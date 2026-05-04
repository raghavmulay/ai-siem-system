from flask import Blueprint, jsonify
from backend.services.db_service import get_logs

logs_bp = Blueprint("logs", __name__)


@logs_bp.route("/logs", methods=["GET"])
def fetch_logs():
    """Returns latest 50 logs (newest first). Timestamps are ISO strings."""
    try:
        return jsonify(get_logs(limit=50)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500