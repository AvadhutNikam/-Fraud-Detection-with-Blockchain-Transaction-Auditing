import os
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
import joblib

def generate_synthetic_fraud_dataset(n_samples: int = 15000, random_state: int = 42) -> pd.DataFrame:
    """
    Generates a realistic financial transactions dataset inspired by PaySim and Credit Card fraud benchmarks.
    Simulates genuine transaction behavior alongside complex fraud indicators.
    """
    np.random.seed(random_state)
    
    # Types: PAYMENT, CASH_IN, TRANSFER, CASH_OUT, DEBIT
    types = ['PAYMENT', 'CASH_IN', 'TRANSFER', 'CASH_OUT', 'DEBIT']
    type_probs = [0.40, 0.25, 0.15, 0.15, 0.05]
    
    txn_types = np.random.choice(types, size=n_samples, p=type_probs)
    
    # Baseline amounts
    amounts = np.zeros(n_samples)
    orig_balances = np.zeros(n_samples)
    dest_balances = np.zeros(n_samples)
    hours = np.random.randint(0, 24, size=n_samples)
    unusual_location = np.random.binomial(1, 0.04, size=n_samples)
    high_velocity = np.random.binomial(1, 0.03, size=n_samples)
    
    is_fraud = np.zeros(n_samples, dtype=int)
    
    for i in range(n_samples):
        ttype = txn_types[i]
        
        # Fraud probability logic
        fraud_chance = 0.015  # baseline 1.5% fraud rate
        
        if ttype in ['TRANSFER', 'CASH_OUT']:
            fraud_chance += 0.08
            
        if unusual_location[i] == 1:
            fraud_chance += 0.25
            
        if high_velocity[i] == 1:
            fraud_chance += 0.30
            
        if hours[i] in [1, 2, 3, 4]:
            fraud_chance += 0.10
            
        # Draw fraud label
        if np.random.rand() < fraud_chance:
            is_fraud[i] = 1
            # Fraudulent characteristics: typically larger amount, draining account
            if ttype in ['TRANSFER', 'CASH_OUT']:
                amounts[i] = np.random.exponential(scale=65000) + 15000
                orig_balances[i] = amounts[i] + np.random.uniform(0, 2000)
                dest_balances[i] = np.random.uniform(0, 5000)
            else:
                amounts[i] = np.random.exponential(scale=20000) + 5000
                orig_balances[i] = amounts[i] + 500
                dest_balances[i] = np.random.uniform(0, 1000)
        else:
            # Legitimate characteristics
            if ttype == 'PAYMENT':
                amounts[i] = np.random.exponential(scale=800) + 10
                orig_balances[i] = np.random.exponential(scale=5000) + amounts[i]
                dest_balances[i] = 0.0
            elif ttype == 'CASH_IN':
                amounts[i] = np.random.exponential(scale=3500) + 100
                orig_balances[i] = np.random.exponential(scale=10000)
                dest_balances[i] = orig_balances[i] + amounts[i]
            elif ttype in ['TRANSFER', 'CASH_OUT']:
                amounts[i] = np.random.exponential(scale=5000) + 200
                orig_balances[i] = amounts[i] * np.random.uniform(2.0, 10.0)
                dest_balances[i] = np.random.exponential(scale=8000)
            else: # DEBIT
                amounts[i] = np.random.exponential(scale=1200) + 50
                orig_balances[i] = amounts[i] * np.random.uniform(3.0, 12.0)
                dest_balances[i] = 0.0

    df = pd.DataFrame({
        'amount': np.round(amounts, 2),
        'transaction_type': txn_types,
        'orig_balance': np.round(orig_balances, 2),
        'dest_balance': np.round(dest_balances, 2),
        'hour_of_day': hours,
        'risk_flag_unusual_location': unusual_location,
        'risk_flag_high_velocity': high_velocity,
        'is_fraud': is_fraud
    })
    
    return df

def train_and_export():
    print("[+] Generating synthetic financial dataset (15,000 samples)...")
    df = generate_synthetic_fraud_dataset(n_samples=15000)
    
    fraud_pct = (df['is_fraud'].sum() / len(df)) * 100
    print(f"[+] Total samples: {len(df)}, Fraud samples: {df['is_fraud'].sum()} ({fraud_pct:.2f}%)")
    
    # Feature Engineering
    # One-hot encode transaction type
    type_dummies = pd.get_dummies(df['transaction_type'], prefix='type', drop_first=False)
    
    # Balance ratio features
    df['balance_orig_ratio'] = df['amount'] / (df['orig_balance'] + 1.0)
    
    X = pd.concat([
        df[['amount', 'orig_balance', 'dest_balance', 'hour_of_day', 
            'risk_flag_unusual_location', 'risk_flag_high_velocity', 'balance_orig_ratio']],
        type_dummies
    ], axis=1)
    
    y = df['is_fraud']
    feature_cols = list(X.columns)
    
    # Train / Test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    
    print("[+] Training Random Forest Classifier with class weighting...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_split=5,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    
    rf_model.fit(X_train, y_train)
    
    # Evaluation
    y_pred = rf_model.predict(X_test)
    y_prob = rf_model.predict_proba(X_test)[:, 1]
    
    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_prob))
    cm = confusion_matrix(y_test, y_pred).tolist()
    
    print("\n--- Model Evaluation Results ---")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print(f"ROC-AUC:   {roc_auc:.4f}")
    print(f"Confusion Matrix: {cm}")
    
    # Export artifacts
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fraud_model.joblib")
    metrics_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metrics.json")
    
    payload = {
        'model': rf_model,
        'feature_cols': feature_cols,
        'type_categories': ['PAYMENT', 'CASH_IN', 'TRANSFER', 'CASH_OUT', 'DEBIT']
    }
    
    joblib.dump(payload, model_path)
    print(f"[+] Model and feature bundle saved to: {model_path}")
    
    metrics = {
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1_score': round(f1, 4),
        'roc_auc': round(roc_auc, 4),
        'confusion_matrix': cm,
        'total_training_samples': len(X_train),
        'total_testing_samples': len(X_test),
        'feature_importance': {
            col: round(float(imp), 4)
            for col, imp in zip(feature_cols, rf_model.feature_importances_)
        }
    }
    
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"[+] Metrics exported to: {metrics_path}")

if __name__ == '__main__':
    train_and_export()
