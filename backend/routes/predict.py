from datetime import datetime
from flask import Blueprint, jsonify, request
from backend.services import ml_service, db_service
from backend.services.intelligence import generate_alert, sort_alerts
from backend.config.db_config import get_db

predict_bp = Blueprint("predict", __name__)


@predict_bp.route("/predict", methods=["POST"])
def predict():
    """
    Pipeline:
        input → preprocess → ML prediction → decode label
              → detect frequency → assign severity
              → store log → generate & store alert → return response
    """
    try:
        body = request.get_json(silent=True) or {}
        features = body.get("features")
        force_anomaly = body.get("force_anomaly")  # optional: {"attack_type": "neptune"}

        if not features or not isinstance(features, list):
            return jsonify({"error": "Missing or invalid 'features' list in request body"}), 400

        now = datetime.utcnow()

        # ── 1. ML prediction (anomaly bool + decoded attack_type + confidence) ──
        result = ml_service.predict(features)

        # Override with forced anomaly when caller knows the true label
        if force_anomaly and isinstance(force_anomaly, dict):
            result["anomaly"]     = True
            result["attack_type"] = force_anomaly.get("attack_type", result["attack_type"])
            result["confidence"]  = force_anomaly.get("confidence", max(result["confidence"], 0.85))

        result["timestamp"] = now.isoformat() + "Z"

        # ── 2. Store log ──────────────────────────────────────────────────────
        db = get_db()
        db_service.insert_log({
            **result,
            "features":  features,
            "timestamp": now,
            "severity":  "LOW",      # placeholder; updated below if alert fires
        })

        # ── 3. Intelligence: severity + alert ────────────────────────────────
        alert = generate_alert({**result, "timestamp": now}, db)

        if alert:
            db_service.insert_alert(alert)
            result["severity"] = alert["severity"]
            result["alert"] = {
                "severity":  alert["severity"],
                "reason":    alert["reason"],
                "frequency": alert["frequency"],
            }
        else:
            result["severity"] = "LOW"

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# /logs is handled by logs_bp — removed duplicate route
