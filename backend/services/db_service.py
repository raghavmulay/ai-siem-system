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


def _parse_dt(s):
    """Parse ISO string to naive datetime, return None on failure."""
    if not s:
        return None
    try:
        # Strip any timezone suffix — MongoDB stores naive UTC, we compare naively
        clean = s[:19].replace("T", " ")  # '2024-01-15T10:30' or '2024-01-15T10:30:00'
        return datetime.strptime(clean, "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")
        except Exception:
            return None


def get_logs(limit: int = 50, search: str = "", start: str = None, end: str = None, severity: str = None) -> list:
    query = {}
    dt_filter = {}
    if _parse_dt(start):
        dt_filter["$gte"] = _parse_dt(start)
    if _parse_dt(end):
        dt_filter["$lte"] = _parse_dt(end)
    if dt_filter:
        query["timestamp"] = dt_filter
    if search:
        query["attack_type"] = {"$regex": search, "$options": "i"}
    if severity:
        sevs = [s.strip().upper() for s in severity.split(",") if s.strip()]
        query["severity"] = {"$in": sevs}

    logs = db["logs"].find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
    result = []
    for log in logs:
        if "timestamp" in log and hasattr(log["timestamp"], "isoformat"):
            log["timestamp"] = log["timestamp"].isoformat() + "Z"
        result.append(log)
    return result


def clear_all():
    db["logs"].delete_many({})
    db["alerts"].delete_many({})


def get_alerts(limit: int = 20, severity: str = None, search: str = "", start: str = None, end: str = None) -> list:
    """Fetch alerts with optional filtering by severity, search, and date range."""
    query = {}
    if severity:
        sevs = [s.strip().upper() for s in severity.split(",") if s.strip()]
        query["severity"] = {"$in": sevs}
    if search:
        query["$or"] = [
            {"attack_type": {"$regex": search, "$options": "i"}},
            {"reason":      {"$regex": search, "$options": "i"}},
            {"message":     {"$regex": search, "$options": "i"}},
        ]
    dt_filter = {}
    if _parse_dt(start):
        dt_filter["$gte"] = _parse_dt(start)
    if _parse_dt(end):
        dt_filter["$lte"] = _parse_dt(end)
    if dt_filter:
        query["timestamp"] = dt_filter

    raw = list(db["alerts"].find(query, {"_id": 0}).sort("timestamp", -1).limit(limit))
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
