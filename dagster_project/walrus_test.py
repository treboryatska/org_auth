import io
import os
import pandas as pd

from walrus import WalrusClient

publisher_url = "https://publisher.walrus-testnet.walrus.space"
aggregator_url = "https://aggregator.walrus-testnet.walrus.space"

client = WalrusClient(publisher_base_url=publisher_url, aggregator_base_url=aggregator_url)

blob_id = "0x5dea4bc9e6db3b718b27dc00e680867cdb0d34c9c8a77c5ee75d0fe9b9d1403d"
blob_content = client.get_blob(blob_id)
print(blob_content)