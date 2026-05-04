import csv
import io
from flask import Blueprint, jsonify, request, Response
from backend.services.db_service import get_alerts, get_logs

alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/alerts", methods=["GET"])
def fetch_alerts():
    severity = request.args.get("severity")       # e.g. CRITICAL,HIGH
    search   = request.args.get("search", "").strip().lower()
    start    = request.args.get("start")           # ISO string
    end      = request.args.get("end")
    limit    = int(request.args.get("limit", 100))
    try:
        alerts = get_alerts(limit=limit, severity=severity, search=search, start=start, end=end)
        return jsonify(alerts), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alerts_bp.route("/alerts/export", methods=["GET"])
def export_alerts():
    """Export filtered alerts as CSV."""
    severity = request.args.get("severity")
    search   = request.args.get("search", "").strip().lower()
    start    = request.args.get("start")
    end      = request.args.get("end")
    try:
        alerts = get_alerts(limit=10000, severity=severity, search=search, start=start, end=end)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["timestamp", "severity", "attack_type", "confidence", "reason"])
        writer.writeheader()
        for a in alerts:
            writer.writerow({
                "timestamp":   a.get("timestamp", ""),
                "severity":    a.get("severity", ""),
                "attack_type": a.get("attack_type", ""),
                "confidence":  a.get("confidence", ""),
                "reason":      a.get("reason") or a.get("message", ""),
            })
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=alerts_export.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alerts_bp.route("/logs/export", methods=["GET"])
def export_logs():
    """Export logs as CSV."""
    search = request.args.get("search", "").strip().lower()
    start  = request.args.get("start")
    end    = request.args.get("end")
    try:
        logs = get_logs(limit=10000, search=search, start=start, end=end)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["timestamp", "attack_type", "anomaly", "severity", "confidence"])
        writer.writeheader()
        for l in logs:
            writer.writerow({
                "timestamp":   l.get("timestamp", ""),
                "attack_type": l.get("attack_type", ""),
                "anomaly":     l.get("anomaly", ""),
                "severity":    l.get("severity", ""),
                "confidence":  l.get("confidence", ""),
            })
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=logs_export.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500