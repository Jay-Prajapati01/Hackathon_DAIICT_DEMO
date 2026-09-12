"""POST /api/issue — issue a certificate; GET /api/certificate/<file> — download it."""

import os

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from config import cert_storage_path
from modules.issuer import issue_certificate
from utils.validators import validate_issue_input

issue_bp = Blueprint("issue", __name__)


@issue_bp.route("/issue", methods=["POST"])
@jwt_required(optional=True)
def issue():
    """
    POST /api/issue
    Issue a new REC certificate.

    Body (JSON):
    {
      "generator_id":    "WF-A-01",
      "source_type":     "Wind",        // Wind|Solar|Hydro|Biomass|Geothermal|Tidal|Other
      "energy_kwh":      100.0,
      "generation_date": "2026-03-01",
      "issuer_id":       "ISSUER-GreenCert-04",
      "cert_id":         null,           // Optional: auto-generated if null
      "format":          "png"           // "png" or "pdf"
    }

    Response 201:
    {
      "success": true,
      "cert_id": "REC-WND-2026-0091",
      "data_hash": "c9f0f895...",
      "issued_at": "2026-03-02T10:15:00Z",
      "download_url": "/api/certificate/REC-WND-2026-0091.png",
      "anomaly_flag": false
    }
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"success": False, "error": "JSON body required."}), 400

    errors = validate_issue_input(data)
    if errors:
        return jsonify({"success": False, "error": "Validation failed", "details": errors}), 422

    issuer_id = data.get("issuer_id") or get_jwt_identity() or "SYSTEM"
    fmt = (data.get("format") or "png").lower()
    result = issue_certificate(
        cert_id=data.get("cert_id") or None,
        generator_id=data["generator_id"].strip(),
        source_type=data.get("source_type", "Solar"),
        energy_kwh=float(data["energy_kwh"]),
        generation_date=data["generation_date"],
        issuer_id=issuer_id,
        output_format=fmt,
    )

    if not result["success"]:
        return jsonify({"success": False, "error": result["error"]}), 400

    cert_id = result["cert_id"]
    file_name = result["file_name"]
    return (
        jsonify(
            {
                "success": True,
                "cert_id": cert_id,
                "data_hash": result["data_hash"],
                "issued_at": result["issued_at"],
                "format": result["format"],
                "file_name": file_name,
                "download_url": f"/api/certificate/{file_name}",
                "preview_url": f"/api/certificate/{file_name}/preview",
                "anomaly_flag": result.get("anomaly_flag", False),
                "anomaly_reason": result.get("anomaly_reason"),
                "anomaly": result.get("anomaly"),
                "payload": result.get("payload"),
            }
        ),
        201,
    )


def _resolve_cert_file(filename: str):
    safe = secure_filename(filename)
    if not safe or safe != filename:
        return None
    path = os.path.join(cert_storage_path(), safe)
    if not os.path.isfile(path):
        return None
    return path


@issue_bp.route("/certificate/<filename>", methods=["GET"])
def download_certificate(filename):
    """GET /api/certificate/{cert_id}.{ext} — download an issued certificate file."""
    path = _resolve_cert_file(filename)
    if not path:
        return jsonify({"success": False, "error": "Certificate file not found."}), 404
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


@issue_bp.route("/certificate/<filename>/preview", methods=["GET"])
def preview_certificate(filename):
    """GET /api/certificate/{file}/preview — serve inline for browser preview."""
    path = _resolve_cert_file(filename)
    if not path:
        return jsonify({"success": False, "error": "Certificate file not found."}), 404
    mimetype = "application/pdf" if path.lower().endswith(".pdf") else "image/png"
    return send_file(path, as_attachment=False, mimetype=mimetype)
