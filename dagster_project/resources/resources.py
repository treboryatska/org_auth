import os
import io
import subprocess
import tempfile
import gzip
import pandas as pd
from dagster import ConfigurableResource, get_dagster_logger, Failure, resource
from walrus import WalrusClient

class WalrusResource(ConfigurableResource):
    """
    A Dagster resource for interacting with the Walrus object store.
    """
    publisher_url: str
    aggregator_url: str
    
    def get_client(self) -> WalrusClient:
        """Initializes and returns a Walrus client."""
        return WalrusClient(
            publisher_base_url=self.publisher_url, 
            aggregator_base_url=self.aggregator_url
        )

    def upload(self, data: bytes, filename: str) -> str:
        """
        Uploads a bytes object to Walrus and returns the blob ID.
        """
        log = get_dagster_logger()
        client = self.get_client()
        log.info(f"Uploading '{filename}' to Walrus...")
        try:
            response = client.put_blob(data=data, epochs=10)
            blob_id = response['newlyCreated']['blobObject']['blobId']
            log.info(f"Successfully uploaded to Walrus. Blob ID: {blob_id}")
            return blob_id
        except Exception as e:
            log.error(f"Failed to upload '{filename}' to Walrus: {e}")
            raise Failure(f"Failed to upload to Walrus: {e}") from e

    def download(self, blob_id: str) -> bytes:
        """
        Downloads a blob from Walrus using its blobid.
        """
        log = get_dagster_logger()
        client = self.get_client()
        log.info(f"Downloading blob '{blob_id}' from Walrus...")
        try:
            blob_data = client.get_blob(blob_id)
            log.info(f"Successfully downloaded blob '{blob_id}'.")
            return blob_data
        except Exception as e:
            log.error(f"Failed to download blob '{blob_id}': {e}")
            raise Failure(f"Failed to download blob '{blob_id}': {e}") from e

class CryptoEcosystemsResource(ConfigurableResource):
    """
    A resource that clones the crypto-ecosystems repo, runs an export,
    compresses the result, and uploads it to Walrus.
    """
    walrus: WalrusResource

    git_repo_url: str = "https://github.com/electric-capital/crypto-ecosystems.git"
    repo_name: str = "crypto-ecosystems"
    primary_branch: str = "master"

    def _update_repo_and_upload_export(self, ecosystem_name: str) -> str:
        """
        Clones the repo, runs the export script, compresses the output,
        and uploads it to Walrus.

        Args:
            ecosystem_name (str): The name of the ecosystem to export (e.g., "Ethereum").

        Returns:
            str: The blob_id of the uploaded file in Walrus.
        """
        log = get_dagster_logger()
        
        output_filename = f"{ecosystem_name.lower()}.jsonl"
        compressed_filename = f"{output_filename}.gz"

        with tempfile.TemporaryDirectory() as tmpdir:
            clone_dir = os.path.join(tmpdir, self.repo_name)
            output_filepath = os.path.join(clone_dir, output_filename)

            try:
                log.info(f"Cloning repository to temporary directory {clone_dir}...")
                subprocess.run(
                    ["git", "clone", "--depth", "1", "--branch", self.primary_branch, self.git_repo_url, clone_dir],
                    check=True, capture_output=True, text=True
                )

                export_command = [os.path.join(clone_dir, "run.sh"), "export", "-e", ecosystem_name, output_filename]
                
                log.info(f"Running export script: {' '.join(export_command)}")
                subprocess.run(
                    export_command,
                    cwd=clone_dir, check=True, capture_output=True, text=True
                )

                if not os.path.exists(output_filepath):
                    raise Failure(f"Export script ran but output file not found at: {output_filepath}")

                log.info(f"Reading and compressing '{output_filename}'...")
                with open(output_filepath, 'rb') as f:
                    file_bytes = f.read()
                
                compressed_bytes = gzip.compress(file_bytes)

                # Log original and compressed sizes
                original_size_mb = len(file_bytes) / (1024 * 1024)
                compressed_size_mb = len(compressed_bytes) / (1024 * 1024)
                log.info(
                    f"Compression complete. Original: {original_size_mb:.2f} MB, "
                    f"Compressed: {compressed_size_mb:.2f} MB"
                )

                # Upload the compressed data
                blob_id = self.walrus.upload(data=compressed_bytes, filename=compressed_filename)
                return blob_id

            except subprocess.CalledProcessError as e:
                log.error(f"Command failed: {' '.join(e.cmd)}\nStderr: {e.stderr}")
                raise Failure("Git or script command failed.") from e
            finally:
                log.info("Temporary directory cleaned up.")


    def get_data_as_dataframe(self, ecosystem_name: str) -> pd.DataFrame:
        """
        Triggers the repo update/upload and then downloads and decompresses
        the resulting data from Walrus to create a DataFrame.

        Args:
            ecosystem_name (str): The name of the ecosystem to fetch.
        """
        log = get_dagster_logger()
        
        # Step 1: Generate and upload the compressed data
        blob_id = self._update_repo_and_upload_export(ecosystem_name=ecosystem_name)

        # Step 2: Download the compressed file from Walrus
        compressed_bytes = self.walrus.download(blob_id)

        # Step 3: Decompress the data and load into a DataFrame
        log.info(f"Decompressing and processing data from blob '{blob_id}'")
        try:
            decompressed_bytes = gzip.decompress(compressed_bytes)
            df = pd.read_json(io.BytesIO(decompressed_bytes), lines=True)

            if df.empty:
                raise ValueError("DataFrame is empty after processing the file from Walrus.")

            df.rename(columns={
                "eco_name": "project_title",
                "branch": "sub_ecosystems",
                "repo_url": "repo",
                "tags": "tags"
            }, inplace=True)
            
            expected_cols = ['project_title', 'sub_ecosystems', 'repo', 'tags']
            df = df[expected_cols]

            return df

        except Exception as e:
            raise Failure(f"Error processing data from Walrus blob '{blob_id}': {e}") from e