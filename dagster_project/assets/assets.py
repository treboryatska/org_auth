from dagster import asset, Output, Config, op, Failure
import subprocess
import time
import os

# Define a configuration class for the asset
class CryptoEcosystemsConfig(Config):
    """
    Configuration for the crypto_ecosystems_projects_asset.
    
    Attributes:
        ecosystem (str): The name of the ecosystem to export (e.g., "Ethereum").
                         This is a required field and can be set via the
                         DAGSTER_CRYPTO_ECOSYSTEM environment variable.
    """
    # EnvVar tells Dagster to read from the specified environment variable
    # if the value isn't provided directly in the run config.
    ecosystem: str = os.getenv("DAGSTER_CRYPTO_ECOSYSTEM")

@asset(
    description="A table of crypto ecosystem projects from the Electric Capital repo.",
    required_resource_keys={"crypto_ecosystems"}
)
def crypto_ecosystems_projects_asset(context, config: CryptoEcosystemsConfig):
    """
    Uses the CryptoEcosystemsResource to fetch the latest data for a
    user-specified ecosystem and materializes it as an asset.
    """
    # The asset now uses the `ecosystem` from its config to call the resource.
    context.log.info(f"Fetching data for ecosystem: {config.ecosystem}")
    
    df = context.resources.crypto_ecosystems.get_data_as_dataframe(
        ecosystem_name=config.ecosystem
    )

    # Yield metadata for the Dagster UI
    yield Output(
        value=df,
        metadata={
            "num_records": len(df),
            "preview": df.head().to_markdown(),
            "ecosystem": config.ecosystem,
        }
    )

# Clones the repo, exports data, and uploads to Walrus
@asset(required_resource_keys={"crypto_ecosystems"})
def export_and_upload_ecosystem_asset(context, config: CryptoEcosystemsConfig) -> str:
    """
    An asset that uses the CryptoEcosystemsResource to clone, export, compress,
    and upload a dataset to Walrus.
    
    Returns:
        str: The blob_id of the uploaded file.
    """
    context.log.info(f"Starting export for {config.ecosystem} ecosystem...")
    
    crypto_ecosystems_resource = context.resources.crypto_ecosystems
    
    blob_id = crypto_ecosystems_resource._update_repo_and_upload_export(
        ecosystem_name=config.ecosystem
    )
    
    return blob_id

# asset to create the GRC-20 index entry
@asset(required_resource_keys={"crypto_ecosystems"})
def create_grc20_index_entry_asset(context, config: CryptoEcosystemsConfig):
    """
    Triggers the TypeScript script to create an on-chain index entry for a new blob.
    The output of the upstream `export_and_upload_ecosystem_asset` asset is passed in as the `ecosystem_blob` argument.
    """
    context.log.info(f"Starting export for {config.ecosystem} ecosystem...")
    
    crypto_ecosystems_resource = context.resources.crypto_ecosystems
    
    blob_id = crypto_ecosystems_resource._update_repo_and_upload_export(
        ecosystem_name=config.ecosystem
    )
    context.log.info(f"Creating GRC-20 index for blob_id: {blob_id}")
    
    upload_timestamp = str(int(time.time()))
    
    # Get the absolute path to the directory where this Python script is located
    # In a Dagster context, __file__ points to the location of assets.py
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the absolute path to the Node.js script
    # Go up one level from 'assets' to the 'dagster_project' directory
    # then down into 'hypergraph/dist/addIndexEntry.js'
    node_script_path = os.path.join(
        script_dir, # e.g., /opt/dagster/app/dagster_project/assets
        "..",       # Go up to /opt/dagster/app/dagster_project
        "hypergraph",
        "dist",
        "addIndexEntry.js"
    )
    
    node_script_path = os.path.normpath(node_script_path)
    # run the command
    command = ["node", node_script_path, blob_id, upload_timestamp]

    # The working directory can be the root of the project
    working_dir = os.path.join(script_dir, "..") # /opt/dagster/app/dagster_project

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            cwd=working_dir # Use the calculated working directory
        )
        context.log.info("Node.js script executed successfully:")
        context.log.info(result.stdout)
    except subprocess.CalledProcessError as e:
        context.log.error(f"Node.js script failed:\n{e.stderr}")
        raise Failure(description=f"Node.js script execution failed. Stderr: {e.stderr}") from e
    except FileNotFoundError:
        context.log.error(f"Could not find the script at the specified path: {node_script_path}")
        raise

# setup the hypergraph schema
@op
def setup_hypergraph_schema_op(context):
    """
    Runs the one-time setup script to create the GRC-20 Space and Schema.
    
    This op should only be run once to initialize the hypergraph environment.
    The script's output will contain the new space ID, which should be manually
    added to the .env file as 'existing_space_id'.
    """
    context.log.info("Starting one-time Hypergraph schema setup...")
    
    command = ["node", "hypergraph/dist/createIndexEntry.js"]

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            cwd="/opt/dagster/app/"
        )
        context.log.info("Schema setup script executed successfully:")
        context.log.info(result.stdout)
        context.log.warning(
            "ACTION REQUIRED: Copy the 'New space created with ID' from the logs above "
            "and set it as the 'existing_space_id' in your .env file."
        )
    except subprocess.CalledProcessError as e:
        context.log.error(f"Schema setup script failed:\n{e.stderr}")
        raise Failure(description=f"Node.js setup script failed. Stderr: {e.stderr}") from e