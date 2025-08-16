from dagster import asset, Output, Config
import io
import os
import pandas as pd

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

@asset(
    deps=["crypto_ecosystems_projects_asset"],
    description="Uploads the crypto ecosystems DataFrame to Walrus as a Parquet file.",
    required_resource_keys={"walrus"}
)
def crypto_ecosystems_walrus_asset(context, crypto_ecosystems_projects_asset: pd.DataFrame):
    """
    Takes the upstream DataFrame, converts it to a Parquet file in memory,
    and uploads it to Walrus.
    """
    parquet_buffer = io.BytesIO()
    crypto_ecosystems_projects_asset.to_parquet(parquet_buffer, index=False)
    parquet_buffer.seek(0)

    blob_id = context.resources.walrus.upload(data=parquet_buffer.getvalue())

    yield Output(
        value=blob_id,
        metadata={
            "blob_id": blob_id,
            "filename": "crypto_ecosystems.parquet",
            "num_records": len(crypto_ecosystems_projects_asset)
        }
    )