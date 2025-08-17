// org_auth/dagster_project/hypergraph/createIndexEntry.ts
import { Graph, Ipfs, getSmartAccountWalletClient } from '@graphprotocol/grc-20';
import type { Op } from '@graphprotocol/grc-20';
import { GraphQLClient, gql } from 'graphql-request';
import { privateKeyToAccount } from 'viem/accounts';
import * as dotenv from 'dotenv';
dotenv.config();

const addressPrivateKey = process.env.grc_20_private_key;
if (!addressPrivateKey) {
  throw new Error('grc_20_private_key environment variable is required');
}

// Ensure private key is properly formatted (should start with 0x and be 64 hex characters)
if (!addressPrivateKey.startsWith('0x') || addressPrivateKey.length !== 66) {
  throw new Error('grc_20_private_key must be a 32-byte hex string starting with 0x (66 characters total)');
}

const { address } = privateKeyToAccount(addressPrivateKey as `0x${string}`);

// Space configuration
const editorAddress = address;
const spaceName = process.env.grc_20_space_name as string;

// Helper function to find a space by id
async function getSpaceAddressById(spaceId: string): Promise<string | null> {
  // Return early if no ID is provided.
  if (!spaceId) {
    console.log("No SPACE_ID provided.");
    return null;
  }

  const GEO_TESTNET_ENDPOINT = 'https://api-testnet.geobrowser.io/graphql';
  const client = new GraphQLClient(GEO_TESTNET_ENDPOINT, {
    headers: {
      'Content-Type': 'application/json'
    },
  });

  console.log('getSpaceAddressById', spaceId)

  const query = gql`
    query GetSpaceById($spaceId: UUID!) {
      space(id: $spaceId) {
        spaceAddress
      }
    }
  `;

      try {
      const variables = { spaceId };
      console.log(`Querying for Space ID: ${spaceId}...`);
      const result = await client.request(query, variables) as { space: { spaceAddress: string } | null };

    if (result.space && result.space.spaceAddress) {
      console.log(`   - Found Space Address: ${result.space.spaceAddress}`);
      return result.space.spaceAddress;
    } else {
      console.error(`   - Space with ID '${spaceId}' not found.`);
      return null;
    }
  } catch (error) {
    console.error(`Error querying for space ID '${spaceId}':`, error);
    return null;
  }
}

// This function defines our schema and returns the operations needed to create it.
function defineSchema(): Op[] {
  const allOps: Op[] = [];

  // 1. Create the 'blob_id' property, capturing both its id and ops
  const { id: blobId, ops: blobIdOps } = Graph.createProperty({
    name: 'blob_id',
    dataType: 'STRING',
  });
  console.log(`Generated 'blob_id' property ID: ${blobId}`);
  allOps.push(...blobIdOps);

  // 2. Create the 'upload_timestamp' property, capturing both its id and ops
  const { id: timestampId, ops: timestampOps } = Graph.createProperty({
    name: 'upload_timestamp',
    dataType: 'NUMBER',
  });
  console.log(`Generated 'upload_timestamp' property ID: ${timestampId}`);
  allOps.push(...timestampOps);

  // 3. Create the 'JsonlFileIndex' type using the captured IDs directly
  const { id: indexTypeId,ops: indexTypeOps } = Graph.createType({
    name: 'JsonlFileIndex',
    properties: [
      blobId,     // Use the captured ID
      timestampId,  // Use the captured ID
    ],
  });
  console.log(`Generated 'JsonlFileIndex' type ID: ${indexTypeId}`);
  allOps.push(...indexTypeOps);

  return allOps;
}

// Main execution function
async function main() {
  try {
    console.log('1. Creating wallet client using geo testnet...');
    const smartAccountWalletClient = await getSmartAccountWalletClient({
      privateKey: addressPrivateKey as `0x${string}`,
    });

    console.log(`2. Checking for an existing space named '${spaceName}'...`);

    // Read the Space ID from environment variables
    let spaceId = process.env.existing_space_id;

    // Fetch the space address using the provided ID
    const spaceAddress = await getSpaceAddressById(spaceId as string);
    
    if (spaceAddress) {
      console.log(`   - Found existing space with address: ${spaceAddress}`);
    } else {
      console.log(`   - Space ${spaceId} not found. Creating a new one...`);
      const spaceResponse = await Graph.createSpace({
        editorAddress: address,
        name: spaceName,
        network: 'TESTNET',
      });
      spaceId = (spaceResponse as any).id || (spaceResponse as any).spaceId || spaceResponse;
      console.log(`   - New space created with ID: ${spaceId}`);
    }

    console.log('3. Defining schema for JsonlFileIndex...');
    const schemaOps = defineSchema();
    console.log(`   - Generated ${schemaOps.length} operations.`);

    console.log('\n3. Publishing schema definition as an Edit to IPFS...');

    // 3. Publish the collected operations as a single "Edit" to IPFS.
    const { cid } = await Ipfs.publishEdit({
      name: 'Define JsonlFileIndex Schema',
      ops: schemaOps,
      // Using a placeholder author since this is an off-chain action for now
      author: address,
      network: 'TESTNET', // Use TESTNET for development
    });

    console.log('\n✅ Success!');
    console.log(`IPFS Content ID (CID): ${cid}`);

    // --- On-Chain: Fetch Calldata and Send Transaction ---
    console.log('\n4. Fetching on-chain calldata for the Edit...');

    const calldataResponse = await fetch(`${Graph.TESTNET_API_ORIGIN}/space/${spaceId}/edit/calldata`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cid }),
    });

    if (!calldataResponse.ok) {
        throw new Error(`Failed to fetch calldata: ${await calldataResponse.text()}`);
    }

    const { to, data } = await calldataResponse.json() as { to: string; data: string };
    console.log(`   - Calldata received for contract: ${to}`);

    console.log('\n5. Sending transaction to the blockchain...');
    const txHash = await smartAccountWalletClient.sendTransaction({
      account: smartAccountWalletClient.account,
      // @ts-expect-error
      to: to,
      // @ts-expect-error
      data: data,
      value: 0n,
    });
    console.log(`   - Transaction sent! ${txHash}`);

    console.log('\n Schema published on-chain successfully!');

  } catch (error) {
    console.error('An error occurred:', error);
    process.exit(1);
  }
}

// Run the main function
main();