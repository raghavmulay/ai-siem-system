"""
backend/services/ml_service.py
-------------------------------
Inference service.  Loads artifacts produced by ml/train_model.py and
exposes a single predict() function whose response contract is unchanged:

    {
        "anomaly":     bool,
        "attack_type": str,
        "confidence":  float   # max class probability from RandomForest
    }

Artifact compatibility
----------------------
ml/train_model.py now saves:
  encoders.pkl      — sklearn OrdinalEncoder (fitted on CAT_COLS only)
  scaler.pkl        — sklearn StandardScaler (fitted on numeric cols only)
  columns.pkl       — ordered list of 41 feature column names
  classifier.pkl    — RandomForestClassifier
  anomaly.pkl       — IsolationForest
  label_encoder.pkl — LabelEncoder for target classes

Unknown categorical values at inference time are handled by
OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
so unseen service/flag/protocol values produce -1 instead of crashing.

Confidence note
---------------
predict_proba() returns uncalibrated probabilities.  The max value is
used as a proxy confidence score, consistent with the previous behaviour.
It is NOT a calibrated probability.
"""

import os
import joblib
import numpy as np
import pandas as pd

try:
    from backend.services.autoencoder_service import predict_autoencoder
except Exception as exc:
    predict_autoencoder = None
    print(f"Warning: autoencoder unavailable: {exc}")


from backend.models.load_models import load_models

# ---------------------------------------------------------------------------
# Load models at startup
# ---------------------------------------------------------------------------
anomaly_model, classifier = load_models()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models"))

# Categorical columns — must match the order used during training
CAT_COLS = ["protocol_type", "service", "flag"]

try:
    ord_enc      = joblib.load(os.path.join(BASE_DIR, "encoders.pkl"))
    scaler       = joblib.load(os.path.join(BASE_DIR, "scaler.pkl"))
    columns      = joblib.load(os.path.join(BASE_DIR, "columns.pkl"))
    label_encoder = joblib.load(os.path.join(BASE_DIR, "label_encoder.pkl"))
    print("ml_service: all preprocessing artifacts loaded.")
except FileNotFoundError as e:
    if "label_encoder" in str(e):
        label_encoder = None
        print("Warning: label_encoder.pkl not found — attack_type will be numeric")
    else:
        raise
except Exception as e:
    print(f"Warning: could not load preprocessing artifacts: {e}")
    ord_enc, scaler, columns, label_encoder = None, None, [], None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _decode_attack_type(encoded_label: int) -> str:
    if label_encoder is not None:
        try:
            return str(label_encoder.inverse_transform([encoded_label])[0])
        except Exception:
            pass
    fallback = {0: "Normal", 1: "DoS", 2: "Probe", 3: "R2L", 4: "U2R"}
    return fallback.get(encoded_label, f"Type-{encoded_label}")


def preprocess_input(features: list) -> np.ndarray:
    """
    Transform a raw feature list (41 values, positional) into the scaled
    numpy array expected by the models.

    Categorical columns (protocol_type, service, flag) are encoded with the
    fitted OrdinalEncoder.  Unknown values produce -1 (handle_unknown setting).
    Numeric columns are scaled with the fitted StandardScaler.

    Both transformers receive named DataFrames so sklearn does not emit
    feature-name warnings.  Prediction output is unchanged.
    """
    if not columns:
        return np.array(features, dtype=float).reshape(1, -1)

    # Align to expected column count
    n = len(columns)
    padded = list(features[:n]) + [0] * max(0, n - len(features))

    num_cols = [c for c in columns if c not in CAT_COLS]

    # Build a single-row DataFrame with correct column names
    row = dict(zip(columns, padded))

    # Encode categoricals — pass a named DataFrame to suppress feature-name warning
    if ord_enc is not None:
        cat_df = pd.DataFrame([{c: row[c] for c in CAT_COLS}], columns=CAT_COLS)
        try:
            encoded_cats = ord_enc.transform(cat_df)[0]
        except Exception:
            encoded_cats = np.full(len(CAT_COLS), -1.0)
        for c, val in zip(CAT_COLS, encoded_cats):
            row[c] = val

    # Coerce all values to float
    for c in columns:
        try:
            row[c] = float(row[c])
        except (ValueError, TypeError):
            row[c] = 0.0

    # Scale numerics — pass a named DataFrame to suppress feature-name warning
    if scaler is not None:
        num_df = pd.DataFrame([{c: row[c] for c in num_cols}], columns=num_cols)
        scaled = scaler.transform(num_df)[0]
        for c, val in zip(num_cols, scaled):
            row[c] = val

    return np.array([row[c] for c in columns], dtype=float).reshape(1, -1)


# ---------------------------------------------------------------------------
# Public API — response contract unchanged
# ---------------------------------------------------------------------------
def predict(features: list) -> dict:
    """Combine RF classification with IF and autoencoder anomaly signals."""
    data = preprocess_input(features)

    # Random Forest remains the primary attack classifier.
    raw_label = int(classifier.predict(data)[0])
    attack_type = _decode_attack_type(raw_label)
    confidence = float(round(max(classifier.predict_proba(data)[0]), 4))

    # Isolation Forest supplementary signal.
    raw_anomaly = int(anomaly_model.predict(data)[0])
    if_anomaly = raw_anomaly == -1

    rf_is_attack = attack_type.lower() != "normal"

    # Autoencoder supplementary signal; never changes attack_type.
    ae_anomaly = False
    if predict_autoencoder is not None:
        try:
            ae_result = predict_autoencoder(features)
            ae_anomaly = bool(ae_result.get("anomaly", False))
        except Exception as exc:
            print(f"Warning: autoencoder prediction failed: {exc}")

    anomaly_bool = rf_is_attack or if_anomaly or ae_anomaly

    if not rf_is_attack:
        attack_type = "Normal"

    return {
        "anomaly": anomaly_bool,
        "attack_type": attack_type,
        "confidence": confidence,
    }
