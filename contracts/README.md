# Smart Contract Deployment Guide: Sepolia Testnet

This project features the `TransactionAuditor.sol` smart contract, which records cryptographic audit hashes of AI-screened financial transactions.

## 1. Quick Deployment via Remix IDE (Recommended & Free)

1. Open [Remix Ethereum IDE](https://remix.ethereum.org/).
2. Create a new file in the contracts folder: `TransactionAuditor.sol`.
3. Copy and paste the contents of `contracts/TransactionAuditor.sol`.
4. Go to the **Solidity Compiler** tab on the left navigation:
   - Select compiler version `0.8.20` or higher.
   - Click **Compile TransactionAuditor.sol**.
5. Go to the **Deploy & Run Transactions** tab:
   - In the **Environment** dropdown, select **Injected Provider - MetaMask**.
   - Make sure your MetaMask network is switched to **Sepolia Test Network** (get free test ETH from Google Cloud Web3 faucet or Sepolia PoW faucet).
   - Click the orange **Deploy** button.
   - Confirm the transaction in MetaMask.
6. Once deployed:
   - Copy the deployed contract address (starts with `0x...`).
   - Open `.env` in this project directory and set:
     ```env
     CONTRACT_ADDRESS=0xYourDeployedContractAddressHere
     SEPOLIA_RPC_URL=https://rpc.sepolia.org
     PRIVATE_KEY=your_metamask_account_private_key
     USE_MOCK_BLOCKCHAIN=false
     ```

## 2. Instant Local/Simulated Mode (Zero Setup Required)

If you don't have Sepolia test ETH or an RPC key right now, no problem!
By default, the application runs in **Simulated Blockchain Mode**:
- `USE_MOCK_BLOCKCHAIN=true`
- Generates realistic cryptographic transactions and maintains an on-chain ledger in memory/DB.
- Fully simulates hash matching, verification, and tamper detection instantly.
- Toggle between live Sepolia and Simulated Mode at any time in `.env`.
