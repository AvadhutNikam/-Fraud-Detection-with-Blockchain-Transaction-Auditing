# AI-Based Fraud Detection with Blockchain Transaction Auditing

A medium-level project combining **Machine Learning** for intelligent transaction fraud scoring and **Ethereum Blockchain Smart Contracts** with **SHA-256 Cryptographic Fingerprinting** for tamper-evident transaction record auditing.

---

## 📌 Project Overview

Traditional financial systems face two distinct challenges:
1. **Detecting Fraud in Real-Time:** Identifying complex, anomalous patterns in financial transactions.
2. **Audit Trail Integrity:** Ensuring that once a transaction has been reviewed, logged, or flagged, neither an insider, administrator, nor attacker can quietly modify the record in the database.

This project integrates both:
- **AI Fraud Prediction:** A Scikit-learn **Random Forest Classifier** evaluates transaction characteristics (e.g., transaction amount, mechanism, origin/destination balances, hour of day, geo-anomaly, and velocity flags) to compute an estimated risk score and category (Low, Medium, or High Risk).
- **Blockchain Auditing:** Generates a deterministic **SHA-256 hash** of the canonical audit record and commits it to a Solidity smart contract (`TransactionAuditor.sol`).
- **Privacy Preservation:** Sensitive transaction figures, customer PII, and bank account numbers are **never stored on the public blockchain**; only the immutable 256-bit cryptographic fingerprint is recorded.
- **Tamper Detection Demonstration:** An interactive verification lab allows altering local database records to immediately demonstrate how the blockchain detects unauthorized modifications.

---

## 🏗️ Architecture

```
[User / Financial Core]
         │
         ▼
[Flask Web Application (Port 5000)]
   ├── Input Validation & Feature Engineering
   │
   ├── [Scikit-learn Random Forest Model] 
   │        └── Predicts Risk Score & Risk Category (Low, Medium, High)
   │
   ├── [SHA-256 Canonical Serializer]
   │        └── Computes Fixed 256-bit Audit Hash
   │
   ├── [SQLite Database: fraud_audit.db]
   │        └── Stores Full Audit Record & Local State
   │
   └── [Ethereum Web3 / Sepolia Smart Contract]
            └── Logs Audit Hash & Tx Reference on Immutable Ledger
```

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3, Flask | RESTful APIs, request handling, verification pipeline |
| **Machine Learning** | Scikit-learn, Random Forest | Multi-feature financial fraud classification & probability estimation |
| **Data Processing** | Pandas, NumPy | Feature engineering, balance ratios, dummy encoding |
| **Model Persistence** | Joblib | Serialized model loading without retraining overhead |
| **Local Database** | SQLite (`fraud_audit.db`) | Local audit record storage and tamper simulation |
| **Cryptographic Hashing**| SHA-256 (`hashlib`) | Deterministic audit packet fingerprinting |
| **Smart Contract** | Solidity `^0.8.20` | Immutable on-chain audit ledger |
| **Blockchain Client** | Web3.py | Interacting with Ethereum RPC and smart contract calls |
| **Frontend UI** | HTML5, Modern CSS, Bootstrap 5 | Cyber-fintech glassmorphism dashboard, dynamic verification lab |

---

## 🚀 Quick Start Guide

### 1. Prerequisites & Dependencies
Ensure Python is installed, then install required libraries:
```bash
pip install -r requirements.txt
```

### 2. Train the Machine Learning Model
Generate the realistic transaction dataset and train the Random Forest Classifier:
```bash
python ml/train_model.py
```
This generates `ml/fraud_model.joblib` and `ml/metrics.json`.

### 3. Launch the Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://localhost:5000
```

---

## 🧪 Demonstration & Presentation Walkthrough

### Step 1: Submit a Genuine Transaction
1. Click the preset button: **"☕ Normal Coffee / Grocery Payment (Legitimate)"**.
2. Click **"Analyze with AI & Submit Audit to Blockchain"**.
3. Observe:
   - AI outputs **Low Risk** (~5% risk score).
   - Generates deterministic **SHA-256 hash**.
   - Submits hash to the smart contract ledger.

### Step 2: Submit a Suspicious Account Drain
1. Click the preset button: **"⚡ Midnight Account Drain Transfer (High Fraud)"**.
2. Notice the elevated amount (₹92,000), nocturnal timing (03:00 HRS), high balance depletion ratio, and geo-anomaly flags.
3. Click **"Analyze with AI & Submit Audit to Blockchain"**.
4. Observe:
   - AI immediately flags **High Risk / Fraudulent** with high probability.
   - Highlights contributing risk factors.
   - Registers a unique audit hash on the blockchain.

### Step 3: Demonstrate Tamper Detection (The Core Exam/Interview Demo)
1. Switch to the **Tamper & Verification Lab** tab.
2. Select any recorded transaction from the dropdown.
3. Click **"Execute Cryptographic Verification"**:
   - The system recomputes the SHA-256 hash from the local database and compares it with the blockchain record.
   - Result: **✅ VERIFIED (Record Intact)**.
4. Now click **"Deliberately Tamper Record in DB"**:
   - This simulates an insider attack or unauthorized database manipulation by altering the amount or prediction in the local database.
5. Watch the verification banner update:
   - Result: **🚨 INTEGRITY VIOLATION DETECTED: RECORD MISMATCH!**
   - The local database hash no longer matches the immutable on-chain fingerprint.
6. Click **"Restore Original"** to demonstrate automated state recovery and re-verification.

---

## 🌐 Deploying to Live Ethereum Sepolia Testnet

The system comes pre-configured with **Simulated EVM Mode** enabled (`USE_MOCK_BLOCKCHAIN=true`) so it works out-of-the-box with zero configuration.

To connect to live Ethereum Sepolia:
1. Open Remix IDE (`https://remix.ethereum.org/`).
2. Paste `contracts/TransactionAuditor.sol` and deploy to Sepolia via MetaMask.
3. Update `.env`:
   ```env
   USE_MOCK_BLOCKCHAIN=false
   SEPOLIA_RPC_URL=https://rpc.sepolia.org
   CONTRACT_ADDRESS=0xYourDeployedAddressHere
   PRIVATE_KEY=your_testnet_wallet_private_key
   ```
4. Restart Flask: `python app.py`.

---

## 📂 Project Directory Structure

```
├── app.py                      # Flask REST API and web application server
├── database.py                 # SQLite database models, CRUD, and tamper simulator
├── requirements.txt            # Dependency manifest
├── .env                        # Environment configurations (Sepolia & Mock toggles)
│
├── ml/
│   ├── train_model.py          # Synthetic dataset generator & Random Forest training
│   ├── predict.py              # Inference engine, risk categorizer, factor analyzer
│   ├── fraud_model.joblib      # Trained Random Forest model binary
│   └── metrics.json            # Model evaluation metrics (Precision, Recall, F1)
│
├── blockchain/
│   ├── auditor.py              # SHA-256 generator & Web3 / Simulated EVM auditor
│   └── simulated_ledger.json   # Simulated on-chain immutable ledger storage
│
├── contracts/
│   ├── TransactionAuditor.sol  # Solidity smart contract
│   ├── TransactionAuditor.json # Smart contract ABI
│   └── README.md               # Remix and Sepolia deployment walkthrough
│
├── templates/
│   └── index.html              # Cyber-fintech glassmorphism dashboard
│
└── static/
    ├── css/
    │   └── style.css           # Custom dark theme styles and responsive layout
    └── js/
        └── app.js              # Frontend controller and verification workflows
```
