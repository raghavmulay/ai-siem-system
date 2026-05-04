from flask import Blueprint, jsonify
from backend.config.db_config import get_db

alerts_bp = Blueprint("alerts", __name__)

@alerts_bp.route("/alerts", methods=["GET"])
def get_alerts():
    db = get_db()
    alerts_collection = db["alerts"]

    alerts = list(alerts_collection.find().sort("timestamp", -1).limit(10))

    for alert in alerts:
        alert["_id"] = str(alert["_id"])

    return jsonify(alerts)