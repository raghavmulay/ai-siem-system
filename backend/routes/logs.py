from flask import Blueprint, jsonify
from backend.config.db_config import get_db

logs_bp = Blueprint("logs", __name__)

@logs_bp.route("/logs", methods=["GET"])
def get_logs():
    db = get_db()
    logs_collection = db["logs"]

    logs = list(logs_collection.find().sort("timestamp", -1).limit(20))

    for log in logs:
        log["_id"] = str(log["_id"])

    return jsonify(logs)