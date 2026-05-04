from datetime import datetime, timedelta
from collections import defaultdict


# ── Severity Priority Map (used for sorting) ──────────────────────────────────
SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

# ── Known multi-step attack patterns ─────────────────────────────────────────
# Each pattern: (ordered list of attack types, label, severity)
ATTACK_PATTERNS = [
    (["portsweep", "neptune"],          "Recon → DoS",           "CRITICAL"),
    (["portsweep", "smurf"],            "Recon → Flood",         "CRITICAL"),
    (["portsweep", "back"],             "Recon → Exploit",       "CRITICAL"),
    (["portsweep", "teardrop"],         "Recon → Fragmentation", "HIGH"),
    (["satan",     "neptune"],          "Probe → DoS",           "CRITICAL"),
    (["satan",     "smurf"],            "Probe → Flood",         "CRITICAL"),
    (["satan",     "back"],             "Probe → Exploit",       "HIGH"),
    (["nmap",      "neptune"],          "Scan → DoS",            "HIGH"),
    (["nmap",      "smurf"],            "Scan → Flood",          "HIGH"),
    (["neptune",   "smurf"],            "DoS Escalation",        "CRITICAL"),
    (["ipsweep",   "portsweep", "neptune"], "Full Recon → DoS", "CRITICAL"),
]


def detect_attack_chains(db, window_minutes: int = 10) -> list:
    """
    Scan the last `window_minutes` of anomalous logs and detect
    coordinated multi-step attack patterns.
    Returns a list of chain dicts.
    """
    since = datetime.utcnow() - timedelta(minutes=window_minutes)
    logs = list(db["logs"].find(
        {"anomaly": True, "timestamp": {"$gte": since}},
        {"attack_type": 1, "timestamp": 1, "confidence": 1, "_id": 0}
    ).sort("timestamp", 1))

    # Collect ordered unique attack types seen in the window
    seen_types = list(dict.fromkeys(
        l["attack_type"].lower() for l in logs if l.get("attack_type")
    ))

    chains = []
    for pattern, label, severity in ATTACK_PATTERNS:
        # Check if every step in the pattern appears in order
        idx = 0
        matched_steps = []
        for step in pattern:
            try:
                pos = seen_types.index(step, idx)
                matched_steps.append(seen_types[pos])
                idx = pos + 1
            except ValueError:
                break
        else:
            # All steps matched
            # Collect timestamps for matched attack types
            step_set = set(pattern)
            involved = [
                {"attack_type": l["attack_type"],
                 "timestamp":   l["timestamp"].isoformat() + "Z",
                 "confidence":  round(l.get("confidence", 0.0), 3)}
                for l in logs if l.get("attack_type", "").lower() in step_set
            ]
            chains.append({
                "pattern":    label,
                "steps":      pattern,
                "severity":   severity,
                "log_count":  len(involved),
                "first_seen": involved[0]["timestamp"] if involved else None,
                "last_seen":  involved[-1]["timestamp"] if involved else None,
                "logs":       involved[:20],   # cap at 20 for response size
            })

    return chains


def detect_frequency(db, attack_type: str) -> int:
    """
    Count anomalous logs for this attack_type in the last 5 minutes.
    Uses case-insensitive regex to handle label casing differences.
    """
    import re
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    count = db["logs"].count_documents({
        "anomaly": True,
        "attack_type": {"$regex": f"^{re.escape(attack_type)}$", "$options": "i"},
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
    if frequency >= 2:
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
