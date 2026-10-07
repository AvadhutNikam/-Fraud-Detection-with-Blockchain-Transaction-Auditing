import os
import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from database import (
    init_db,
    insert_transaction,
    get_transaction_by_ref,
    get_all_transactions,
    tamper_transaction,
    restore_transaction,
    get_stats
)
from ml.predict import FraudPredictor
from blockchain.auditor import compute_audit_hash, auditor_instance

load_dotenv()

app = Flask(__name__)

# Initialize database on startup
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/predict-and-audit', methods=['POST'])
def predict_and_audit():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON payload provided'}), 400

        # Validate mandatory fields
        required_fields = ['transaction_ref', 'amount', 'transaction_type']
        for field in required_fields:
            if field not in data or data[field] is None:
                return jsonify({'error': f"Missing required parameter: {field}"}), 400

        tx_ref = str(data['transaction_ref']).strip()
        amount = float(data['amount'])
        if amount <= 0:
            return jsonify({'error': 'Transaction amount must be strictly positive'}), 400

        # Check for duplication
        existing = get_transaction_by_ref(tx_ref)
        if existing:
            return jsonify({'error': f"Transaction {tx_ref} already exists in audit registry"}), 409

        # 1. AI Fraud Prediction
        predictor = FraudPredictor.get_instance()
        prediction_result = predictor.predict(data)

        # 2. Cryptographic SHA-256 Hashing
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        audit_payload = {
            'transaction_ref': tx_ref,
            'amount': amount,
            'transaction_type': data['transaction_type'],
            'prediction': prediction_result['prediction'],
            'risk_score': prediction_result['risk_score'],
            'timestamp': timestamp
        }

        audit_hash, canonical_payload = compute_audit_hash(audit_payload)

        # 3. Blockchain Audit Registration
        blockchain_result = auditor_instance.log_audit_record(tx_ref, audit_hash)

        if not blockchain_result.get('success'):
            return jsonify({
                'error': f"Blockchain submission failed: {blockchain_result.get('error')}"
            }), 500

        # 4. Save to Database
        db_record = {
            'transaction_ref': tx_ref,
            'amount': amount,
            'transaction_type': data['transaction_type'],
            'orig_balance': data.get('orig_balance', 0.0),
            'dest_balance': data.get('dest_balance', 0.0),
            'hour_of_day': data.get('hour_of_day', 12),
            'risk_flag_unusual_location': data.get('risk_flag_unusual_location', 0),
            'risk_flag_high_velocity': data.get('risk_flag_high_velocity', 0),
            'raw_features': data,
            'prediction': prediction_result['prediction'],
            'risk_score': prediction_result['risk_score'],
            'risk_category': prediction_result['risk_category'],
            'timestamp': timestamp,
            'audit_hash': audit_hash,
            'blockchain_tx_hash': blockchain_result.get('tx_hash', ''),
            'blockchain_status': 'CONFIRMED'
        }

        row_id = insert_transaction(db_record)

        return jsonify({
            'status': 'SUCCESS',
            'record_id': row_id,
            'transaction': db_record,
            'prediction': prediction_result,
            'audit': {
                'audit_hash': audit_hash,
                'canonical_payload': canonical_payload
            },
            'blockchain': blockchain_result
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
def list_transactions():
    transactions = get_all_transactions(limit=100)
    return jsonify(transactions)

@app.route('/api/transactions/<ref>', methods=['GET'])
def get_transaction(ref):
    tx = get_transaction_by_ref(ref)
    if not tx:
        return jsonify({'error': 'Transaction not found'}), 404

    # Calculate what the SHA-256 hash would be right now with current DB values
    current_hash, canonical_payload = compute_audit_hash(tx)

    # Query blockchain
    blockchain_info = auditor_instance.verify_record(ref, current_hash)

    return jsonify({
        'transaction': tx,
        'current_calculated_hash': current_hash,
        'current_canonical_payload': canonical_payload,
        'blockchain_record': blockchain_info
    })

@app.route('/api/verify', methods=['POST'])
def verify_transaction():
    data = request.get_json() or {}
    tx_ref = data.get('transaction_ref')
    if not tx_ref:
        return jsonify({'error': 'Missing transaction_ref'}), 400

    tx = get_transaction_by_ref(tx_ref)
    if not tx:
        return jsonify({'error': f"Transaction {tx_ref} not found in database"}), 404

    # Re-calculate hash from current DB data
    calculated_hash, _ = compute_audit_hash(tx)

    # Perform verification against blockchain
    result = auditor_instance.verify_record(tx_ref, calculated_hash)
    result['transaction_ref'] = tx_ref
    result['is_tampered_in_db'] = bool(tx.get('is_tampered', 0))

    return jsonify(result)

@app.route('/api/tamper', methods=['POST'])
def tamper():
    data = request.get_json() or {}
    tx_ref = data.get('transaction_ref')
    if not tx_ref:
        return jsonify({'error': 'Missing transaction_ref'}), 400

    new_amount = data.get('amount')
    new_pred = data.get('prediction')
    new_cat = data.get('risk_category')

    success, message = tamper_transaction(
        tx_ref,
        new_amount=float(new_amount) if new_amount is not None else None,
        new_prediction=new_pred,
        new_category=new_cat
    )

    if not success:
        return jsonify({'error': message}), 404

    return jsonify({'status': 'TAMPERED', 'message': message})

@app.route('/api/reset-tamper', methods=['POST'])
def reset_tamper():
    data = request.get_json() or {}
    tx_ref = data.get('transaction_ref')
    if not tx_ref:
        return jsonify({'error': 'Missing transaction_ref'}), 400

    success, message = restore_transaction(tx_ref)
    if not success:
        return jsonify({'error': message}), 404

    return jsonify({'status': 'RESTORED', 'message': message})

@app.route('/api/stats', methods=['GET'])
def stats():
    return jsonify(get_stats())

@app.route('/api/system-status', methods=['GET'])
def system_status():
    return jsonify({
        'blockchain': auditor_instance.get_status()
    })

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
