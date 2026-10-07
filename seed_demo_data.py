import datetime
from database import init_db, insert_transaction, get_transaction_by_ref
from ml.predict import FraudPredictor
from blockchain.auditor import compute_audit_hash, auditor_instance

def seed():
    init_db()
    predictor = FraudPredictor.get_instance()

    demo_txns = [
        {
            'transaction_ref': 'TXN-1001',
            'amount': 25000.0,
            'transaction_type': 'TRANSFER',
            'orig_balance': 25200.0,
            'dest_balance': 150.0,
            'hour_of_day': 3,
            'risk_flag_unusual_location': 1,
            'risk_flag_high_velocity': 1
        },
        {
            'transaction_ref': 'TXN-1002',
            'amount': 650.0,
            'transaction_type': 'PAYMENT',
            'orig_balance': 14200.0,
            'dest_balance': 0.0,
            'hour_of_day': 14,
            'risk_flag_unusual_location': 0,
            'risk_flag_high_velocity': 0
        },
        {
            'transaction_ref': 'TXN-1003',
            'amount': 18500.0,
            'transaction_type': 'CASH_OUT',
            'orig_balance': 20000.0,
            'dest_balance': 500.0,
            'hour_of_day': 22,
            'risk_flag_unusual_location': 1,
            'risk_flag_high_velocity': 0
        }
    ]

    for data in demo_txns:
        ref = data['transaction_ref']
        if get_transaction_by_ref(ref):
            continue

        pred = predictor.predict(data)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        audit_payload = {
            'transaction_ref': ref,
            'amount': data['amount'],
            'transaction_type': data['transaction_type'],
            'prediction': pred['prediction'],
            'risk_score': pred['risk_score'],
            'timestamp': timestamp
        }

        audit_hash, canonical_payload = compute_audit_hash(audit_payload)
        b_res = auditor_instance.log_audit_record(ref, audit_hash)

        rec = {
            'transaction_ref': ref,
            'amount': data['amount'],
            'transaction_type': data['transaction_type'],
            'orig_balance': data['orig_balance'],
            'dest_balance': data['dest_balance'],
            'hour_of_day': data['hour_of_day'],
            'risk_flag_unusual_location': data['risk_flag_unusual_location'],
            'risk_flag_high_velocity': data['risk_flag_high_velocity'],
            'raw_features': data,
            'prediction': pred['prediction'],
            'risk_score': pred['risk_score'],
            'risk_category': pred['risk_category'],
            'timestamp': timestamp,
            'audit_hash': audit_hash,
            'blockchain_tx_hash': b_res.get('tx_hash', ''),
            'blockchain_status': 'CONFIRMED'
        }

        insert_transaction(rec)
        print(f"[Seed] Added {ref} - {pred['risk_category']} (Hash: {audit_hash[:16]}...)")

if __name__ == '__main__':
    seed()
