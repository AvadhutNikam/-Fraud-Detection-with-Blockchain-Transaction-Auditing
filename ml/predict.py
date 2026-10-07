import os
import json
import joblib
import pandas as pd
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fraud_model.joblib")

class FraudPredictor:
    _instance = None

    def __init__(self):
        self.model_data = None
        self.model = None
        self.feature_cols = None
        self.load_model()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = FraudPredictor()
        return cls._instance

    def load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                self.model_data = joblib.load(MODEL_PATH)
                self.model = self.model_data['model']
                self.feature_cols = self.model_data['feature_cols']
                print("[FraudPredictor] Successfully loaded trained Random Forest model.")
            except Exception as e:
                print(f"[FraudPredictor] Error loading model: {e}")
                self.model = None
        else:
            print("[FraudPredictor] Model file not found. Please run train_model.py first.")

    def predict(self, txn: dict) -> dict:
        """
        Analyzes a transaction dictionary and returns prediction, risk score, category, and explanation factors.
        """
        amount = float(txn.get('amount', 0.0))
        txn_type = str(txn.get('transaction_type', 'PAYMENT')).upper()
        orig_balance = float(txn.get('orig_balance', 0.0))
        dest_balance = float(txn.get('dest_balance', 0.0))
        hour = int(txn.get('hour_of_day', 12))
        unusual_location = int(txn.get('risk_flag_unusual_location', 0))
        high_velocity = int(txn.get('risk_flag_high_velocity', 0))

        balance_orig_ratio = amount / (orig_balance + 1.0)

        # Build feature DataFrame matching trained columns
        row = {
            'amount': amount,
            'orig_balance': orig_balance,
            'dest_balance': dest_balance,
            'hour_of_day': hour,
            'risk_flag_unusual_location': unusual_location,
            'risk_flag_high_velocity': high_velocity,
            'balance_orig_ratio': balance_orig_ratio,
            'type_CASH_IN': 1 if txn_type == 'CASH_IN' else 0,
            'type_CASH_OUT': 1 if txn_type == 'CASH_OUT' else 0,
            'type_DEBIT': 1 if txn_type == 'DEBIT' else 0,
            'type_PAYMENT': 1 if txn_type == 'PAYMENT' else 0,
            'type_TRANSFER': 1 if txn_type == 'TRANSFER' else 0
        }

        # If model is loaded, use Random Forest probability
        if self.model is not None and self.feature_cols is not None:
            # Reindex to exact feature columns
            df_input = pd.DataFrame([row]).reindex(columns=self.feature_cols, fill_value=0)
            prob_fraud = float(self.model.predict_proba(df_input)[0][1])
        else:
            # Fallback heuristic calculation if model file is generating
            base_score = 0.05
            if txn_type in ['TRANSFER', 'CASH_OUT']:
                base_score += 0.25
            if amount > 50000:
                base_score += 0.35
            elif amount > 15000:
                base_score += 0.15
            if unusual_location:
                base_score += 0.20
            if high_velocity:
                base_score += 0.20
            if hour in [1, 2, 3, 4]:
                base_score += 0.10
            prob_fraud = min(0.99, base_score)

        # Assign category and prediction label
        if prob_fraud >= 0.65:
            risk_category = "High Risk"
            prediction = "Fraudulent"
        elif prob_fraud >= 0.35:
            risk_category = "Medium Risk"
            prediction = "Suspicious"
        else:
            risk_category = "Low Risk"
            prediction = "Legitimate"

        # Risk Factors explanation
        factors = []
        if txn_type in ['TRANSFER', 'CASH_OUT']:
            factors.append(f"High-risk transaction mechanism ({txn_type})")
        if balance_orig_ratio > 0.8:
            factors.append(f"High depletion ratio ({balance_orig_ratio*100:.1f}% of source balance)")
        if amount > 25000:
            factors.append(f"Substantial transaction value (INR {amount:,.2f})")
        if unusual_location:
            factors.append("Geo-location anomaly / unrecognized IP address detected")
        if high_velocity:
            factors.append("Multiple rapid consecutive transfers within short window")
        if hour in [1, 2, 3, 4]:
            factors.append(f"Off-peak nocturnal transaction time ({hour:02d}:00 HRS)")

        if not factors:
            factors.append("Transaction characteristics align with standard verified user activity patterns.")

        return {
            'prediction': prediction,
            'risk_score': round(prob_fraud, 4),
            'risk_percentage': round(prob_fraud * 100, 1),
            'risk_category': risk_category,
            'contributing_factors': factors,
            'features_evaluated': row
        }
