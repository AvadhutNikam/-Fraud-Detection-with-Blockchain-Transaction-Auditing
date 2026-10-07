import sqlite3
import json
import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "fraud_audit.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_ref TEXT UNIQUE NOT NULL,
        amount REAL NOT NULL,
        transaction_type TEXT NOT NULL,
        orig_balance REAL NOT NULL,
        dest_balance REAL NOT NULL,
        hour_of_day INTEGER NOT NULL,
        risk_flag_unusual_location INTEGER DEFAULT 0,
        risk_flag_high_velocity INTEGER DEFAULT 0,
        raw_features_json TEXT NOT NULL,
        prediction TEXT NOT NULL,
        risk_score REAL NOT NULL,
        risk_category TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        audit_hash TEXT NOT NULL,
        blockchain_tx_hash TEXT,
        blockchain_status TEXT DEFAULT 'CONFIRMED',
        is_tampered INTEGER DEFAULT 0,
        tampered_at TEXT,
        original_data_backup TEXT
    )
    """)
    conn.commit()
    conn.close()

def insert_transaction(data: dict) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (
            transaction_ref, amount, transaction_type, orig_balance, dest_balance,
            hour_of_day, risk_flag_unusual_location, risk_flag_high_velocity,
            raw_features_json, prediction, risk_score, risk_category,
            timestamp, audit_hash, blockchain_tx_hash, blockchain_status
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?
        )
    """, (
        data['transaction_ref'],
        float(data['amount']),
        data['transaction_type'],
        float(data.get('orig_balance', 0.0)),
        float(data.get('dest_balance', 0.0)),
        int(data.get('hour_of_day', 12)),
        int(data.get('risk_flag_unusual_location', 0)),
        int(data.get('risk_flag_high_velocity', 0)),
        json.dumps(data.get('raw_features', {})),
        data['prediction'],
        float(data['risk_score']),
        data['risk_category'],
        data['timestamp'],
        data['audit_hash'],
        data.get('blockchain_tx_hash', ''),
        data.get('blockchain_status', 'CONFIRMED')
    ))
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id

def get_transaction_by_ref(ref: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE transaction_ref = ?", (ref,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_transactions(limit: int = 100):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def tamper_transaction(ref: str, new_amount: float = None, new_prediction: str = None, new_category: str = None):
    """
    Deliberately alters local database record values without touching the blockchain.
    Used for live demonstration of cryptographic audit mismatch.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE transaction_ref = ?", (ref,))
    record = cursor.fetchone()
    if not record:
        conn.close()
        return False, "Transaction not found"

    # Backup original data if not already tampered
    backup = record['original_data_backup']
    if not backup:
        backup = json.dumps({
            'amount': record['amount'],
            'prediction': record['prediction'],
            'risk_category': record['risk_category'],
            'risk_score': record['risk_score']
        })

    amount = new_amount if new_amount is not None else (record['amount'] / 10.0 if record['amount'] > 100 else 50000.0)
    prediction = new_prediction if new_prediction is not None else ("Legitimate" if record['prediction'] == "Fraudulent" else "Fraudulent")
    category = new_category if new_category is not None else ("Low Risk" if prediction == "Legitimate" else "High Risk")
    score = 0.05 if prediction == "Legitimate" else 0.95

    cursor.execute("""
        UPDATE transactions
        SET amount = ?, prediction = ?, risk_category = ?, risk_score = ?,
            is_tampered = 1, tampered_at = ?, original_data_backup = ?
        WHERE transaction_ref = ?
    """, (amount, prediction, category, score, datetime.datetime.now().isoformat(), backup, ref))
    conn.commit()
    conn.close()
    return True, f"Tampered record {ref}: amount -> {amount}, prediction -> {prediction}"

def restore_transaction(ref: str):
    """
    Restores original database values from backup.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT original_data_backup FROM transactions WHERE transaction_ref = ?", (ref,))
    row = cursor.fetchone()
    if not row or not row['original_data_backup']:
        conn.close()
        return False, "No backup found or transaction does not exist"

    backup = json.loads(row['original_data_backup'])
    cursor.execute("""
        UPDATE transactions
        SET amount = ?, prediction = ?, risk_category = ?, risk_score = ?,
            is_tampered = 0, tampered_at = NULL, original_data_backup = NULL
        WHERE transaction_ref = ?
    """, (backup['amount'], backup['prediction'], backup['risk_category'], backup['risk_score'], ref))
    conn.commit()
    conn.close()
    return True, f"Restored {ref} to original values"

def get_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM transactions")
    total = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as fraudulent FROM transactions WHERE prediction = 'Fraudulent'")
    fraudulent = cursor.fetchone()['fraudulent']
    cursor.execute("SELECT COUNT(*) as tampered FROM transactions WHERE is_tampered = 1")
    tampered = cursor.fetchone()['tampered']
    conn.close()
    return {
        'total_transactions': total,
        'fraudulent_count': fraudulent,
        'legitimate_count': total - fraudulent,
        'tampered_count': tampered
    }
