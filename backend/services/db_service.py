from datetime import datetime
from backend.config.db_config import get_db

db = get_db()

def insert_log(data):
    db["logs"].insert_one({
        "timestamp": datetime.utcnow(),
        "features": data["features"],
        "anomaly": data["anomaly"],
        "attack_type": data["attack_type"],
        "confidence": data["confidence"]
    })

def insert_alert(alert):
    db["alerts"].insert_one(alert)

def get_logs(limit=50):
    logs = db["logs"].find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return list(logs)
