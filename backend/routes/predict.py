from flask import Blueprint, request, jsonify
from backend.services import ml_service, alert_service, db_service

predict_bp = Blueprint("predict", __name__)

@predict_bp.route("/predict", methods=["POST"])
def predict():
    try:
        features = request.json.get("features")
        if not features:
            return jsonify({"error": "Missing 'features' in request body"}), 400

        # 1. ML prediction
        result = ml_service.predict(features)

        # 2. Store log
        db_service.insert_log({**result, "features": features})

        # 3. Generate alert
        alert = alert_service.generate_alert(result["anomaly"], result["confidence"])

        # 4. Store alert if triggered
        if alert:
            db_service.insert_alert(alert)
            result["alert"] = {"severity": alert["severity"], "message": alert["message"]}

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@predict_bp.route("/logs", methods=["GET"])
def logs():
    try:
        return jsonify(db_service.get_logs(limit=50)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
