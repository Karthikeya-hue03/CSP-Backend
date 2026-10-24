import os
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import joblib

from ml.dataset_generator import generate_synthetic_dataset

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / 'training_data.csv'
MODEL_PATH = BASE_DIR / 'model.joblib'

# The 8 input telemetry features used for machine learning inference
FEATURE_COLS = [
    'age_years',
    'previous_failures',
    'health_score',
    'inspection_frequency',
    'complaint_count',
    'previous_maintenance_count',
    'condition_code',
    'days_since_last_maintenance'
]

def train_and_export_model():
    """
    Trains the Scikit-learn Machine Learning pipeline and exports the serialized model bundle.
    
    How it works:
    1. Checks if `ml/training_data.csv` exists; if not, triggers `generate_synthetic_dataset()`.
    2. Loads features `X` and targets:
       - `y_class`: Classification target ('Low Risk', 'Medium Risk', 'High Risk').
       - `y_days`: Regression target (predicted days until failure/servicing).
    3. Splits data into 80% training and 20% test sets with stratification on the target class.
    4. Fits a `StandardScaler` on the training features to normalize scales across age, counts, and health.
    5. Trains a `RandomForestClassifier` (120 trees, max_depth 9) for risk categorization.
    6. Trains a `RandomForestRegressor` (80 trees, max_depth 8) for failure window prediction.
    7. Evaluates the classifier on the held-out test set, printing accuracy, precision, recall,
       F1-score, and feature importances.
    8. Packages classifier, regressor, scaler, feature list, and metadata into a joblib bundle
       saved at `ml/model.joblib`.
       
    Returns:
        dict: The trained model bundle dictionary containing all estimators and metadata.
    """
    if not DATA_PATH.exists():
        print("[*] Training data not found. Generating synthetic dataset...")
        df = generate_synthetic_dataset()
    else:
        df = pd.read_csv(DATA_PATH)
        
    X = df[FEATURE_COLS]
    y_class = df['risk_level']
    y_days = df['days_to_failure']
    
    # 80/20 Stratified Train / Test split
    X_train, X_test, y_train, y_test, y_days_train, y_days_test = train_test_split(
        X, y_class, y_days, test_size=0.2, random_state=42, stratify=y_class
    )
    
    # Feature standardization
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Classification Model: Predicts Low / Medium / High Risk
    clf = RandomForestClassifier(
        n_estimators=120,
        max_depth=9,
        min_samples_split=4,
        random_state=42
    )
    clf.fit(X_train_scaled, y_train)
    
    # Regression Model: Predicts estimated days until failure/maintenance
    reg = RandomForestRegressor(
        n_estimators=80,
        max_depth=8,
        random_state=42
    )
    reg.fit(X_train_scaled, y_days_train)
    
    # Evaluate performance on test set
    y_pred = clf.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n==========================================")
    print(f"Scikit-learn Model Training Complete")
    print(f"Classifier Accuracy: {acc * 100:.2f}%")
    print(f"==========================================\n")
    print(classification_report(y_test, y_pred))
    
    # Calculate and display feature importances
    importances = dict(zip(FEATURE_COLS, clf.feature_importances_))
    sorted_importances = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    print("Feature Importances:")
    for feat, imp in sorted_importances:
        print(f"  - {feat:28s}: {imp:.4f}")
        
    # Export bundle with all required deployment artifacts
    bundle = {
        'classifier': clf,
        'regressor': reg,
        'scaler': scaler,
        'features': FEATURE_COLS,
        'classes': list(clf.classes_),
        'accuracy': float(acc),
        'disclaimer': (
            "Prototype demonstration model trained on synthetic college campus infrastructure data. "
            "Actual deployment requires calibrated campus sensor logs and historic telemetry."
        )
    }
    
    joblib.dump(bundle, MODEL_PATH)
    print(f"\n[+] Trained model bundle successfully saved to: {MODEL_PATH}")
    return bundle

if __name__ == '__main__':
    train_and_export_model()
