from flask import Blueprint, jsonify, request
from backend.services.intelligence import detect_attack_chains
from backend.config.db_config import get_db

attack_chains_bp = Blueprint("attack_chains", __name__)


@attack_chains_bp.route("/attack-chains", methods=["GET"])
def get_attack_chains():
    """
    Returns detected multi-step attack chains from the last N minutes.
    Query param: ?window=10  (default 10 minutes)
    """
    try:
        window = int(request.args.get("window", 10))
        db = get_db()
        chains = detect_attack_chains(db, window_minutes=window)
        return jsonify({"chains": chains, "count": len(chains)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
