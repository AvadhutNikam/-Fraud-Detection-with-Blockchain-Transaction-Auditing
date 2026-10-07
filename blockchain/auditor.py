import os
import json
import hashlib
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SIMULATED_LEDGER_FILE = Path(__file__).parent / "simulated_ledger.json"
ABI_FILE = Path(__file__).parent.parent / "contracts" / "TransactionAuditor.json"

def generate_canonical_payload(record: dict) -> str:
    """
    Creates a standardized, deterministic string representation of the audit record.
    The exact serialization guarantees that any modification to fields produces a totally different SHA-256 hash.
    """
    amount = float(record.get('amount', 0.0))
    # Standard format: REF|AMOUNT|TYPE|PREDICTION|RISK_SCORE|TIMESTAMP
    canonical_str = (
        f"TX_REF:{str(record.get('transaction_ref')).strip()}|"
        f"AMOUNT:{amount:.2f}|"
        f"TYPE:{str(record.get('transaction_type')).strip().upper()}|"
        f"PRED:{str(record.get('prediction')).strip()}|"
        f"RISK:{float(record.get('risk_score', 0.0)):.4f}|"
        f"TIME:{str(record.get('timestamp')).strip()}"
    )
    return canonical_str

def compute_audit_hash(record: dict) -> tuple[str, str]:
    """
    Computes SHA-256 hash for a transaction audit record.
    Returns (sha256_hex, canonical_payload_string).
    """
    canonical_payload = generate_canonical_payload(record)
    hash_obj = hashlib.sha256(canonical_payload.encode('utf-8'))
    return hash_obj.hexdigest(), canonical_payload

class BlockchainAuditor:
    def __init__(self):
        self.use_mock = os.getenv("USE_MOCK_BLOCKCHAIN", "true").lower() in ("true", "1", "yes")
        self.contract_address = os.getenv("CONTRACT_ADDRESS", "0x89205A3A3b2A55388eC7311149954C5a0d3f8EB2")
        self.rpc_url = os.getenv("SEPOLIA_RPC_URL", "https://rpc.sepolia.org")
        self.private_key = os.getenv("PRIVATE_KEY", "")
        
        self.w3 = None
        self.contract = None
        self.abi = self._load_abi()
        
        if not self.use_mock and self.private_key and self.contract_address:
            self._init_web3()
        else:
            self.use_mock = True
            self._init_simulated_ledger()

    def _load_abi(self):
        if ABI_FILE.exists():
            with open(ABI_FILE, 'r') as f:
                return json.load(f)
        return []

    def _init_web3(self):
        try:
            from web3 import Web3
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if self.w3.is_connected():
                account = self.w3.eth.account.from_key(self.private_key)
                self.account_address = account.address
                checksum_address = self.w3.to_checksum_address(self.contract_address)
                self.contract = self.w3.eth.contract(address=checksum_address, abi=self.abi)
                print(f"[BlockchainAuditor] Connected to Sepolia RPC. Auditor Address: {self.account_address}")
            else:
                print("[BlockchainAuditor] Unable to connect to Sepolia RPC. Falling back to Simulated Mode.")
                self.use_mock = True
                self._init_simulated_ledger()
        except Exception as e:
            print(f"[BlockchainAuditor] Web3 initialization error: {e}. Defaulting to Simulated Mode.")
            self.use_mock = True
            self._init_simulated_ledger()

    def _init_simulated_ledger(self):
        if not SIMULATED_LEDGER_FILE.exists():
            with open(SIMULATED_LEDGER_FILE, 'w') as f:
                json.dump({}, f, indent=2)

    def _read_simulated_ledger(self) -> dict:
        try:
            if SIMULATED_LEDGER_FILE.exists():
                with open(SIMULATED_LEDGER_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _write_simulated_ledger(self, ledger: dict):
        with open(SIMULATED_LEDGER_FILE, 'w') as f:
            json.dump(ledger, f, indent=2)

    def log_audit_record(self, tx_ref: str, audit_hash: str) -> dict:
        """
        Submits the audit hash to the blockchain smart contract.
        """
        if self.use_mock:
            ledger = self._read_simulated_ledger()
            if tx_ref in ledger:
                # Immutability violation
                return {
                    'success': False,
                    'error': f"Transaction {tx_ref} already recorded on-chain. Blockchain records are immutable!",
                    'tx_hash': ledger[tx_ref]['tx_hash']
                }

            # Generate pseudo-Ethereum transaction hash (0x + 64 hex chars)
            mock_block = int(time.time() * 1000)
            seed = f"{tx_ref}_{audit_hash}_{mock_block}"
            tx_hash = "0x" + hashlib.sha256(seed.encode('utf-8')).hexdigest()

            record = {
                'transaction_ref': tx_ref,
                'audit_hash': audit_hash,
                'timestamp': int(time.time()),
                'recorded_by': "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
                'tx_hash': tx_hash,
                'network': 'Simulated Ethereum Sepolia Ledger',
                'block_number': 6418900 + len(ledger) + 1
            }

            ledger[tx_ref] = record
            self._write_simulated_ledger(ledger)

            return {
                'success': True,
                'tx_hash': tx_hash,
                'block_number': record['block_number'],
                'network': record['network'],
                'contract_address': self.contract_address,
                'explorer_url': f"https://sepolia.etherscan.io/tx/{tx_hash}"
            }
        else:
            try:
                # Live Sepolia testnet execution
                account = self.w3.eth.account.from_key(self.private_key)
                nonce = self.w3.eth.get_transaction_count(account.address)
                gas_price = self.w3.eth.gas_price

                tx = self.contract.functions.logAuditRecord(tx_ref, audit_hash).build_transaction({
                    'from': account.address,
                    'nonce': nonce,
                    'gas': 200000,
                    'gasPrice': gas_price
                })

                signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
                tx_hash_bytes = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                tx_hash = self.w3.to_hex(tx_hash_bytes)

                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=120)

                return {
                    'success': True,
                    'tx_hash': tx_hash,
                    'block_number': receipt.blockNumber,
                    'network': 'Ethereum Sepolia Testnet',
                    'contract_address': self.contract_address,
                    'explorer_url': f"https://sepolia.etherscan.io/tx/{tx_hash}"
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'network': 'Ethereum Sepolia Testnet'
                }

    def verify_record(self, tx_ref: str, current_calculated_hash: str) -> dict:
        """
        Queries the blockchain for the stored audit hash and performs cryptographic comparison.
        """
        if self.use_mock:
            ledger = self._read_simulated_ledger()
            if tx_ref not in ledger:
                return {
                    'verified': False,
                    'error': f"Transaction {tx_ref} not found on the blockchain ledger.",
                    'stored_hash': None,
                    'calculated_hash': current_calculated_hash,
                    'status': 'NOT_FOUND_ON_CHAIN'
                }

            stored_hash = ledger[tx_ref]['audit_hash']
            matches = (stored_hash == current_calculated_hash)

            return {
                'verified': matches,
                'status': 'VERIFIED' if matches else 'MISMATCH_DETECTED',
                'stored_hash': stored_hash,
                'calculated_hash': current_calculated_hash,
                'timestamp': ledger[tx_ref]['timestamp'],
                'tx_hash': ledger[tx_ref]['tx_hash'],
                'network': ledger[tx_ref]['network'],
                'contract_address': self.contract_address
            }
        else:
            try:
                matches, stored_hash, timestamp = self.contract.functions.verifyRecordHash(
                    tx_ref, current_calculated_hash
                ).call()

                return {
                    'verified': matches,
                    'status': 'VERIFIED' if matches else 'MISMATCH_DETECTED',
                    'stored_hash': stored_hash,
                    'calculated_hash': current_calculated_hash,
                    'timestamp': timestamp,
                    'contract_address': self.contract_address,
                    'network': 'Ethereum Sepolia Testnet'
                }
            except Exception as e:
                return {
                    'verified': False,
                    'error': str(e),
                    'status': 'ERROR'
                }

    def get_status(self) -> dict:
        return {
            'mode': 'Simulated Ethereum Ledger' if self.use_mock else 'Ethereum Sepolia Testnet',
            'is_mock': self.use_mock,
            'contract_address': self.contract_address,
            'rpc_url': self.rpc_url if not self.use_mock else 'Local Mock EVM'
        }

auditor_instance = BlockchainAuditor()
