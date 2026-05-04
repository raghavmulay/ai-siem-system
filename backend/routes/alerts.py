from flask import Blueprint, jsonify
from backend.services.db_service import get_alerts

alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/alerts", methods=["GET"])
def fetch_alerts():
    """
    Returns alerts pre-sorted:
      1. severity  CRITICAL > HIGH > MEDIUM > LOW
      2. confidence descending
    """
    try:
        return jsonify(get_alerts(limit=20)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500