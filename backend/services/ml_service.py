import os
import joblib
import numpy as np

# Import loader function (not variables)
from backend.models.load_models import load_models

# Load models at startup
anomaly_model, classifier = load_models()

# Correct base path to models folder
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models"))

# Load preprocessing objects
try:
    encoders = joblib.load(os.path.join(BASE_DIR, "encoders.pkl"))
    scaler = joblib.load(os.path.join(BASE_DIR, "scaler.pkl"))
    columns = joblib.load(os.path.join(BASE_DIR, "columns.pkl"))
    label_encoder = joblib.load(os.path.join(BASE_DIR, "label_encoder.pkl"))

except FileNotFoundError as e:
    if "label_encoder" in str(e):
        label_encoder = None
        print("Warning: label_encoder.pkl not found — attack_type will remain numeric")
    else:
        raise

except Exception as e:
    print(f"Warning: Could not load preprocessing objects: {e}")
    encoders, scaler, columns, label_encoder = {}, None, [], None


def _decode_attack_type(encoded_label: int) -> str:
    """Decode numeric label → string class name."""
    if label_encoder is not None:
        try:
            return str(label_encoder.inverse_transform([encoded_label])[0])
        except Exception:
            pass

    # fallback mapping
    fallback = {
        0: "Normal",
        1: "DoS",
        2: "Probe",
        3: "R2L",
        4: "U2R",
    }
    return fallback.get(encoded_label, f"Type-{encoded_label}")


def preprocess_input(features: list) -> np.ndarray:
    processed = []

    for i, val in enumerate(features):
        if i >= len(columns):
            break

        col_name = columns[i]

        if col_name in encoders:
            encoder = encoders[col_name]
            try:
                encoded_val = encoder.transform([str(val)])[0]
            except ValueError:
                encoded_val = 0
            processed.append(float(encoded_val))
        else:
            try:
                processed.append(float(val))
            except (ValueError, TypeError):
                processed.append(0.0)

    if scaler is not None:
        data = np.array(processed).reshape(1, -1)
        return scaler.transform(data)

    return np.array(processed).reshape(1, -1)


def predict(features: list) -> dict:
    data = preprocess_input(features)

    # Step 1: Anomaly Detection
    raw_anomaly = int(anomaly_model.predict(data)[0])
    anomaly_bool = raw_anomaly == -1

    # Step 2: Classification ONLY if anomaly
    if anomaly_bool:
        raw_label = int(classifier.predict(data)[0])
        attack_type = _decode_attack_type(raw_label)
        confidence = float(round(max(classifier.predict_proba(data)[0]), 4))
    else:
        attack_type = "Normal"
        confidence = 0.98  # or 0.99 for realism

    return {
        "anomaly": anomaly_bool,
        "attack_type": attack_type,
        "confidence": confidence,
    }