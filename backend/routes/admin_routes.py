"""Regulator / admin dashboard endpoints."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from modules.ledger import (
    get_all_certificates,
    get_anomalies,
    get_daily_activity,
    get_fraud_breakdown,
    get_ledger_stats,
    get_recent_verifications,
    get_source_breakdown,
    resolve_anomaly,
)
from utils.auth import roles_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard", methods=["GET"])
@jwt_required(optional=True)
def dashboard():
    """GET /api/admin/dashboard — everything the regulator dashboard needs in one call."""
    try:
        days = max(1, min(int(request.args.get("days", 14)), 90))
    except ValueError:
        days = 14
    return jsonify(
        {
            "success": True,
            "stats": get_ledger_stats(),
            "by_source": get_source_breakdown(),
            "fraud_by_layer": get_fraud_breakdown(),
            "daily_activity": get_daily_activity(days),
            "recent_verifications": get_recent_verifications(limit=15),
            "recent_certificates": get_all_certificates(limit=10),
            "open_anomalies": get_anomalies(resolved=False, limit=20),
        }
    )


@admin_bp.route("/verifications", methods=["GET"])
@jwt_required(optional=True)
def verifications():
    """GET /api/admin/verifications?limit=50 — verification audit log."""
    try:
        limit = max(1, min(int(request.args.get("limit", 50)), 500))
    except ValueError:
        limit = 50
    return jsonify({"success": True, "verifications": get_recent_verifications(limit=limit)})


@admin_bp.route("/anomalies", methods=["GET"])
@jwt_required(optional=True)
def anomalies():
    """GET /api/admin/anomalies?resolved=false — anomaly flags raised at issuance."""
    resolved_arg = request.args.get("resolved")
    resolved = None if resolved_arg is None else resolved_arg.lower() in ("1", "true", "yes")
    return jsonify({"success": True, "anomalies": get_anomalies(resolved=resolved, limit=200)})


@admin_bp.route("/anomalies/<int:anomaly_id>/resolve", methods=["POST"])
@roles_required("regulator")
def resolve(anomaly_id):
    """POST /api/admin/anomalies/{id}/resolve — regulator closes an anomaly."""
    if not resolve_anomaly(anomaly_id, get_jwt_identity()):
        return jsonify({"success": False, "error": "Anomaly not found or already resolved."}), 404
    return jsonify({"success": True, "anomaly_id": anomaly_id})
