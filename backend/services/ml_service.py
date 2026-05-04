import os
import joblib
import numpy as np
from backend.models.load_models import anomaly_model, classifier

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend/models"))

try:
    encoders = joblib.load(os.path.join(BASE_DIR, "encoders.pkl"))
    scaler = joblib.load(os.path.join(BASE_DIR, "scaler.pkl"))
    columns = joblib.load(os.path.join(BASE_DIR, "columns.pkl"))
except Exception as e:
    print(f"Warning: Could not load preprocessing objects: {e}")
    encoders, scaler, columns = {}, None, []

def preprocess_input(features):
    processed = []
    
    for i, val in enumerate(features):
        # Prevent out of bounds if features > columns
        if i >= len(columns):
            break
            
        col_name = columns[i]
        
        if col_name in encoders:
            encoder = encoders[col_name]
            try:
                # Encode known category
                encoded_val = encoder.transform([str(val)])[0]
            except ValueError:
                # Handle unseen category gracefully
                encoded_val = 0
            processed.append(float(encoded_val))
        else:
            try:
                processed.append(float(val))
            except ValueError:
                processed.append(0.0)

    # Scale the row
    if scaler is not None:
        data = np.array(processed).reshape(1, -1)
        data = scaler.transform(data)
        return data
    else:
        return np.array(processed).reshape(1, -1)

def predict(features):
    data = preprocess_input(features)

    anomaly = int(anomaly_model.predict(data)[0])
    attack_type = int(classifier.predict(data)[0])
    confidence = float(round(max(classifier.predict_proba(data)[0]), 4))

    return {
        "anomaly": anomaly,
        "attack_type": attack_type,
        "confidence": confidence
    }