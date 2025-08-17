# Compose - A Modern, Crypto-Native Data Pipeline

This project provides a containerized data pipeline built with Dagster that orchestrates the process of fetching crypto ecosystem data, storing it on a decentralized network, and indexing it on-chain using The Graph's GRC-20 protocol.

The pipeline uses Python for data orchestration and interaction with the Walrus storage protocol, and it leverages a Node.js/TypeScript script to interact with the GRC-20 HyperGraph index.

## Core Technologies

- Orchestrator: Dagster
- Containerization: Docker
- Languages: Python & TypeScript/Node.js
- Decentralized Storage: Walrus
- Decentralized Indexing: The Graph (HyperGraph GRC-20)

## How It Works

The pipeline automates a simple but powerful workflow for creating a public, verifiable dataset.

1) Fetch Data: The Dagster pipeline is triggered, fetching the latest developer report data from the Electric Capital public repository.

2) Store on Walrus: The dataset (in JSONL format) is uploaded to the Walrus decentralized storage network, which returns a unique and permanent blob ID.

3) Index on HyperGraph: The pipeline calls a TypeScript script that uses the GRC-20 library to write the returned blob ID and a timestamp to a HyperGraph index running on the testnet.geobrowser.io network.

This creates an immutable, on-chain record that points to a specific version of the dataset stored on decentralized infrastructure.

## Getting Started

### Prerequisites
- **Docker:** The entire environment is containerized, so you will need Docker installed and running.

- **Ethereum Wallet:** You need a private key from an Ethereum-style wallet. This will be used to generate a smart account on the GRC-20 testnet. As of August 2025, transaction fees for this network are subsidized.

### Configuration

Before running the project, create a `.env` file in the root directory.

```
# .env file

# The private key of your wallet (must start with 0x)
GRC_20_PRIVATE_KEY=0x...

# The public address of your wallet
GRC_20_ADDRESS=0x...

# A name for your HyperGraph space (e.g., "my-crypto-index")
GRC_20_SPACE_NAME=your-space-name

# The ecosystem to fetch data for (e.g., "Ethereum", "Polkadot")
DAGSTER_CRYPTO_ECOSYSTEM=Ethereum

# Set this value in your .env. Only overwrite this value if you want to create a seperate space with crypto project data.
EXISTING_SPACE_ID=45c68ac0-f3a1-4617-87ba-9f31c90d03f3
```
If you want to create a seperate space:
1) Start the pipeline (see steps below)
2) In the Dagster UI, find and run the op named setup_hypergraph_schema_op
3) Copy the new space ID from the Dagster logs and paste it into your .env file for all future runs.

## Running the Pipeline

1) Build the Docker Image:
```
Bash

docker build -t dagster-pipeline .
```

2) Run the Container:
```
Bash

docker run --env-file .env -p 3000:3000 dagster-pipeline
```

3) Access the UI:
Open your browser to http://localhost:3000 to access the Dagster UI and materialize your assets.

## Project Roadmap
### ✅ Implemented
- Containerized Dagster pipeline for easy, credential-free setup.
- Asset to fetch the crypto ecosystems JSONL dataset.
- Integration with Walrus to upload the dataset as a blob.
- Asset that writes the returned blob ID and a timestamp to a HyperGraph index.

### 🚀 Upcoming Milestones
- A downstream pipeline asset that fetches the latest blob ID from HyperGraph to kick off a transformation process.
- Logic to process the raw JSONL file into serialized "Edits" for granular data modeling.
- Creation of distinct data entities within HyperGraph:
    - Projects with a unique HyperGraph ID.
    - Repos with a HyperGraph ID and a foreign key to a parent project.
    - Organizations with a unique HyperGraph ID.
- Implementation of access control to allow other users to contribute to and compose the public data graph.