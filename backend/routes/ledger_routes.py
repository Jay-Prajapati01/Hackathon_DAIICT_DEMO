"""Ledger endpoints: listing, lookup, stats, claim, revoke, issuers registry."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from modules.crypto import load_public_key_from_pem
from modules.ledger import (
    count_certificates,
    get_all_certificates,
    get_all_issuers,
    get_ledger_stats,
    get_recent_verifications,
    lookup_certificate,
    mark_claimed,
    register_issuer,
    revoke_certificate,
)
from utils.auth import roles_required

ledger_bp = Blueprint("ledger", __name__)


@ledger_bp.route("/ledger", methods=["GET"])
@jwt_required(optional=True)
def get_ledger():
    """
    GET /api/ledger?status=issued&source_type=Wind&search=WF&limit=50&offset=0
    Paginated ledger listing with optional filters.
    """
    filters = {
        "status": request.args.get("status") or None,
        "source_type": request.args.get("source_type") or None,
        "generator_id": request.args.get("generator_id") or None,
        "issuer_id": request.args.get("issuer_id") or None,
        "search": request.args.get("search") or None,
    }
    try:
        limit = max(1, min(int(request.args.get("limit", 100)), 500))
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        return jsonify({"success": False, "error": "limit/offset must be integers."}), 400

    certs = get_all_certificates(limit=limit, offset=offset, **filters)
    total = count_certificates(**filters)
    return jsonify(
        {"success": True, "certificates": certs, "count": len(certs), "total": total, "limit": limit, "offset": offset}
    )


@ledger_bp.route("/ledger/stats", methods=["GET"])
def get_stats():
    """GET /api/ledger/stats — Aggregate statistics for dashboard."""
    return jsonify(get_ledger_stats())


@ledger_bp.route("/ledger/<cert_id>", methods=["GET"])
def get_certificate(cert_id):
    """GET /api/ledger/{cert_id} — Get single certificate ledger record."""
    record = lookup_certificate(cert_id)
    if not record:
        return jsonify({"success": False, "error": f"Certificate '{cert_id}' not found."}), 404
    return jsonify(record)


@ledger_bp.route("/ledger/<cert_id>/history", methods=["GET"])
def get_certificate_history(cert_id):
    """GET /api/ledger/{cert_id}/history — every verification attempt for this certificate."""
    record = lookup_certificate(cert_id)
    history = get_recent_verifications(limit=100, cert_id=cert_id)
    if not record and not history:
        return jsonify({"success": False, "error": f"Certificate '{cert_id}' not found."}), 404
    return jsonify({"success": True, "cert_id": cert_id, "record": record, "verifications": history})


@ledger_bp.route("/ledger/<cert_id>/claim", methods=["POST"])
@jwt_required()
def claim_certificate(cert_id):
    """POST /api/ledger/{cert_id}/claim — Mark a certificate as claimed."""
    data = request.get_json(silent=True) or {}
    claimed_by = data.get("claimed_by") or get_jwt_identity()
    success = mark_claimed(cert_id, claimed_by)
    if not success:
        return jsonify({"success": False, "error": "Certificate not found or already claimed."}), 400
    return jsonify({"success": True, "cert_id": cert_id, "claimed_by": claimed_by})


@ledger_bp.route("/ledger/<cert_id>/revoke", methods=["POST"])
@roles_required("regulator")
def revoke(cert_id):
    """POST /api/ledger/{cert_id}/revoke — Regulator revokes a certificate."""
    success = revoke_certificate(cert_id, get_jwt_identity())
    if not success:
        return jsonify({"success": False, "error": "Certificate not found or already revoked."}), 400
    return jsonify({"success": True, "cert_id": cert_id, "status": "revoked"})


@ledger_bp.route("/issuers", methods=["GET"])
def list_issuers():
    """GET /api/issuers — registered issuing bodies (public keys omitted)."""
    return jsonify({"success": True, "issuers": get_all_issuers()})


@ledger_bp.route("/issuers", methods=["POST"])
@roles_required("regulator")
def add_issuer():
    """POST /api/issuers — register an issuing body and its RSA public key (PEM)."""
    data = request.get_json(silent=True) or {}
    issuer_id, name, pem = data.get("issuer_id"), data.get("issuer_name"), data.get("public_key_pem")
    if not issuer_id or not name or not pem:
        return jsonify({"success": False, "error": "issuer_id, issuer_name and public_key_pem are required."}), 422
    try:
        load_public_key_from_pem(pem)
    except Exception:
        return jsonify({"success": False, "error": "public_key_pem is not a valid PEM public key."}), 422
    if not register_issuer(issuer_id, name, pem):
        return jsonify({"success": False, "error": "Issuer already registered."}), 409
    return jsonify({"success": True, "issuer_id": issuer_id}), 201
