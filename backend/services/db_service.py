from datetime import datetime
from backend.config.db_config import get_db

db = get_db()

SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def insert_log(data: dict):
    db["logs"].insert_one({
        "timestamp":   data.get("timestamp", datetime.utcnow()),
        "features":    data.get("features", []),
        "anomaly":     data.get("anomaly"),       # bool
        "attack_type": data.get("attack_type"),   # decoded string
        "confidence":  data.get("confidence"),
        "severity":    data.get("severity", "LOW"),
    })


def insert_alert(alert: dict):
    db["alerts"].insert_one(alert)


def get_logs(limit: int = 50) -> list:
    logs = db["logs"].find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    result = []
    for log in logs:
        if "timestamp" in log and hasattr(log["timestamp"], "isoformat"):
            log["timestamp"] = log["timestamp"].isoformat() + "Z"
        result.append(log)
    return result


def get_alerts(limit: int = 20) -> list:
    """Fetch alerts sorted by severity (CRITICAL first), then confidence."""
    raw = list(db["alerts"].find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
    for a in raw:
        if "timestamp" in a and hasattr(a["timestamp"], "isoformat"):
            a["timestamp"] = a["timestamp"].isoformat() + "Z"

    return sorted(
        raw,
        key=lambda a: (
            SEVERITY_ORDER.get(a.get("severity", "LOW"), 0),
            a.get("confidence", 0.0),
        ),
        reverse=True,
    )
