from dagster import Definitions
from .assets import crypto_ecosystems_projects_asset, crypto_ecosystems_walrus_asset
from .resources.resources import CryptoEcosystemsResource, WalrusResource
from .io_managers import in_memory_io_manager

# Testnet URLs from the walrus documentation
PUBLISHER_URL = "https://publisher.walrus-testnet.walrus.space"
AGGREGATOR_URL = "https://aggregator.walrus-testnet.walrus.space"

defs = Definitions(
    assets=[
        crypto_ecosystems_projects_asset, 
        crypto_ecosystems_walrus_asset
    ],
    resources={
        "io_manager": in_memory_io_manager,
        "walrus": WalrusResource(
            publisher_url=PUBLISHER_URL,
            aggregator_url=AGGREGATOR_URL
        ),
        "crypto_ecosystems": CryptoEcosystemsResource(
            walrus=WalrusResource(
                publisher_url=PUBLISHER_URL,
                aggregator_url=AGGREGATOR_URL
            )
        ),
    }
)