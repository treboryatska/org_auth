# dagster_project/definitions.py
from dagster import Definitions
from .assets.assets import crypto_ecosystems_projects_asset, export_and_upload_ecosystem_asset, create_grc20_index_entry_asset
from .resources.resources import CryptoEcosystemsResource, WalrusResource
from .io_managers import in_memory_io_manager
from .jobs.jobs import setup_hypergraph_job

# Testnet URLs from the walrus documentation
PUBLISHER_URL = "https://publisher.walrus-testnet.walrus.space"
AGGREGATOR_URL = "https://aggregator.walrus-testnet.walrus.space"

# define the walrus resource 
walrus_resource_instance = WalrusResource(
    publisher_url=PUBLISHER_URL,
    aggregator_url=AGGREGATOR_URL
)

# define the crypto ecosystems resource
crypto_ecosystems_resource_instance = CryptoEcosystemsResource(
    walrus=walrus_resource_instance
)

defs = Definitions(
    assets=[
        crypto_ecosystems_projects_asset,
        export_and_upload_ecosystem_asset,
        create_grc20_index_entry_asset
    ],
    jobs=[setup_hypergraph_job],
    resources={
        "io_manager": in_memory_io_manager,
        "walrus": walrus_resource_instance,
        "crypto_ecosystems": crypto_ecosystems_resource_instance,
    }
)