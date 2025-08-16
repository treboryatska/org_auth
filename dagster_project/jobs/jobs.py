"""
Basic jobs for the Dagster project.
These jobs orchestrate asset execution with different configurations.
"""

from dagster import job, define_asset_job, AssetSelection
from ..assets.assets import crypto_ecosystems_projects_asset


@job
def crypto_ecosystems_job():
    """
    A job that runs the crypto ecosystems asset.
    """
    crypto_ecosystems_projects_asset()


# Define a job that selects specific assets
crypto_data_job = define_asset_job(
    name="crypto_data_job",
    selection=AssetSelection.assets(crypto_ecosystems_projects_asset),
    description="A job that processes crypto ecosystem data"
)

# Create a list of all jobs for easy importing
all_jobs = [crypto_ecosystems_job, crypto_data_job] 