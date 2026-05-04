from datetime import datetime, timedelta


# ── Severity Priority Map (used for sorting) ──────────────────────────────────
SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def detect_frequency(db, attack_type: str) -> int:
    """
    Count how many times attack_type appeared in the last 5 minutes.
    Returns an integer count.
    """
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    count = db["logs"].count_documents({
        "attack_type": attack_type,
        "timestamp": {"$gte": five_min_ago}
    })
    return count


def calculate_severity(anomaly: bool, confidence: float, frequency: int) -> str:
    """
    Rules (in priority order):
      anomaly == False              → LOW
      anomaly == True, conf < 0.6  → MEDIUM
      anomaly == True, conf >= 0.6 → HIGH
      frequency >= 3 in 5 min      → CRITICAL  (overrides HIGH)
    """
    if not anomaly:
        return "LOW"
    if frequency >= 3:
        return "CRITICAL"
    if confidence >= 0.6:
        return "HIGH"
    return "MEDIUM"


def build_reason(severity: str, confidence: float, frequency: int, attack_type: str) -> str:
    """
    Human-readable reason string attached to every alert.
    """
    base = f"{attack_type} detected"
    conf_pct = round(confidence * 100, 1)

    if severity == "CRITICAL":
        return (
            f"High-confidence anomaly detected {frequency} times in the last 5 minutes "
            f"(confidence: {conf_pct}%) — CRITICAL escalation triggered"
        )
    if severity == "HIGH":
        return (
            f"{base} with {conf_pct}% confidence — elevated threat level"
        )
    if severity == "MEDIUM":
        return (
            f"Suspicious activity flagged for {base} "
            f"(low confidence: {conf_pct}%) — monitoring required"
        )
    # LOW — should not reach here for an alert (we only alert on anomalies)
    return f"Normal traffic classified as {attack_type}"


def generate_alert(data: dict, db) -> dict | None:
    """
    data keys expected:
        anomaly (bool), attack_type (str), confidence (float), timestamp (datetime)
    Returns None when anomaly is False (no alert).
    """
    if not data.get("anomaly"):
        return None

    attack_type = data["attack_type"]
    confidence  = data["confidence"]
    timestamp   = data.get("timestamp", datetime.utcnow())

    frequency = detect_frequency(db, attack_type)
    severity  = calculate_severity(True, confidence, frequency)
    reason    = build_reason(severity, confidence, frequency, attack_type)

    return {
        "attack_type": attack_type,
        "confidence":  confidence,
        "severity":    severity,
        "frequency":   frequency,
        "reason":      reason,
        "timestamp":   timestamp,
    }


def sort_alerts(alerts: list) -> list:
    """
    Sort alerts by:
      1. severity  CRITICAL > HIGH > MEDIUM > LOW
      2. confidence descending
    """
    return sorted(
        alerts,
        key=lambda a: (
            SEVERITY_ORDER.get(a.get("severity", "LOW"), 0),
            a.get("confidence", 0.0)
        ),
        reverse=True
    )
