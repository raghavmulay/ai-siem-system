from datetime import datetime

def generate_alert(anomaly, confidence):
    if anomaly != -1:
        return None

    severity = "HIGH" if confidence > 0.8 else "MEDIUM"
    message = (
        f"🚨 High-confidence anomaly detected (confidence: {confidence})"
        if severity == "HIGH"
        else "⚠️ Suspicious activity detected"
    )

    return {
        "timestamp": datetime.utcnow(),
        "severity": severity,
        "message": message
    }
