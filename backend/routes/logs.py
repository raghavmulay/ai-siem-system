from flask import Blueprint, jsonify, request
from backend.services.db_service import get_logs, clear_all

logs_bp = Blueprint("logs", __name__)


@logs_bp.route("/logs", methods=["GET"])
def fetch_logs():
    search   = request.args.get("search", "").strip()
    start    = request.args.get("start")
    end      = request.args.get("end")
    severity = request.args.get("severity")
    limit    = int(request.args.get("limit", 100))
    try:
        return jsonify(get_logs(limit=limit, search=search, start=start, end=end, severity=severity)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@logs_bp.route("/clear", methods=["DELETE"])
def clear_logs():
    """Wipes all logs and alerts from the database."""
    try:
        clear_all()
        return jsonify({"message": "All logs and alerts cleared"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500