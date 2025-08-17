// org_auth/dagster_project/hypergraph/addIndexEntry.ts
import { Graph, Ipfs, getSmartAccountWalletClient } from '@graphprotocol/grc-20';
import { GraphQLClient, gql } from 'graphql-request';
import { privateKeyToAccount } from 'viem/accounts';
import * as dotenv from 'dotenv';
dotenv.config();

// --- Hardcoded Schema IDs ---
const BLOB_ID_PROPERTY_ID = 'b5c2673b-cb22-4d54-8890-fcacb3cb38a1';
const UPLOAD_TIMESTAMP_PROPERTY_ID = '5cb4d39b-b4a9-43fb-a680-7814b1124df4';
const JSONL_FILE_INDEX_TYPE_ID = 'ba32adab-0085-42de-9b74-b47dbfaf9718';

// --- Environment Variable and Wallet Setup ---
const addressPrivateKey = process.env.grc_20_private_key;
if (!addressPrivateKey) {
  throw new Error('grc_20_private_key environment variable is required');
}
if (!addressPrivateKey.startsWith('0x') || addressPrivateKey.length !== 66) {
  throw new Error('grc_20_private_key must be a 32-byte hex string');
}
const { address } = privateKeyToAccount(addressPrivateKey as `0x${string}`);
const spaceId = process.env.existing_space_id as string;
if (!spaceId) {
    throw new Error('existing_space_id environment variable is required');
}

const GEO_TESTNET_ENDPOINT = 'https://api-testnet.geobrowser.io/graphql';
const client = new GraphQLClient(GEO_TESTNET_ENDPOINT);

// --- Main Execution Function ---
async function main() {
  const args = process.argv.slice(2);
  if (args.length !== 2) {
    console.error("Usage: ts-node addIndexEntry.ts <blob_id> <upload_timestamp>");
    process.exit(1);
  }
  const [blobId, uploadTimestamp] = args;
  console.log(`Received data: Blob ID = ${blobId}, Timestamp = ${uploadTimestamp}`);

  try {
    console.log('1. Creating wallet client...');
    const smartAccountWalletClient = await getSmartAccountWalletClient({
      privateKey: addressPrivateKey as `0x${string}`,
    });

    // Note: We still need the spaceAddress for other operations, so this query remains.
    console.log(`2. Getting Space Address for ID: ${spaceId}...`);
    const spaceAddressResponse = await client.request(gql`
        query GetSpaceById($spaceId: UUID!) { space(id: $spaceId) { spaceAddress } }
    `, { spaceId }) as { space: { spaceAddress: string } };
    const spaceAddress = spaceAddressResponse.space.spaceAddress;
    console.log(`   - Found Space Address: ${spaceAddress}`);


    console.log('3. Generating operations to create a new entity using hardcoded IDs...');
    const { ops: entityOps } = Graph.createEntity({
      types: [JSONL_FILE_INDEX_TYPE_ID], 
      values: [
        {
          property: BLOB_ID_PROPERTY_ID,
          value: blobId,
        },
        {
          property: UPLOAD_TIMESTAMP_PROPERTY_ID,
          value: Graph.serializeNumber(Number(uploadTimestamp)),
        },
      ],
    });
    console.log(`   - Generated ${entityOps.length} operations.`);


    console.log('4. Publishing entity creation as an Edit to IPFS...');
    const { cid } = await Ipfs.publishEdit({
      name: `Add index for ${blobId}`,
      ops: entityOps,
      author: address,
      network: 'TESTNET',
    });
    console.log(`   - IPFS Content ID (CID): ${cid}`);

    console.log('5. Fetching on-chain calldata for the Edit...');
    const calldataResponse = await fetch(`${Graph.TESTNET_API_ORIGIN}/space/${spaceId}/edit/calldata`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cid }),
    });
    if (!calldataResponse.ok) {
        throw new Error(`Failed to fetch calldata: ${await calldataResponse.text()}`);
    }
    const { to, data } = await calldataResponse.json() as { to: string; data: string };

    console.log('6. Sending transaction to the blockchain...');
    const txHash = await smartAccountWalletClient.sendTransaction({
      account: smartAccountWalletClient.account,
      to: to as `0x${string}`,
      data: data as `0x${string}`,
      value: 0n,
    });
    
    console.log('\n Success!');
    console.log(`   - Transaction sent: ${txHash}`);
    console.log('   - New index entry published on-chain successfully!');

  } catch (error) {
    console.error('\nAn error occurred:', error);
    process.exit(1);
  }
}

main();
