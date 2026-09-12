"""POST /api/verify — run the three-layer verification on an uploaded file."""

import os

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from config import ALLOWED_UPLOAD_EXTENSIONS
from modules.verifier import verify_certificate
from utils.file_utils import cleanup_temp_file, save_uploaded_file, sniff_extension

verify_bp = Blueprint("verify", __name__)

ALLOWED_EXTENSIONS = ALLOWED_UPLOAD_EXTENSIONS


@verify_bp.route("/verify", methods=["POST"])
@jwt_required(optional=True)
def verify():
    """
    POST /api/verify
    Verify an uploaded REC certificate file.

    Multipart form-data:
      file:        The certificate file (PNG, JPG, or PDF)
      claim:       "true" to mark as claimed on successful verification
      claimed_by:  Buyer entity ID (defaults to the logged-in identity if claim=true)

    Response 200: VerificationResult JSON (see models/verification_result.py)
    """
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded. Use multipart/form-data with field 'file'."}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file.filename:
        return jsonify({"success": False, "error": "No filename provided."}), 400

    ext = os.path.splitext(uploaded_file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"success": False, "error": f"Unsupported file type '{ext}'. Use PNG or PDF."}), 415

    # Save to temp location for processing
    temp_path = save_uploaded_file(uploaded_file, ext)

    try:
        # Trust magic bytes over the extension the client sent
        real_ext = sniff_extension(temp_path)
        if real_ext and real_ext != ext and not (real_ext == ".jpg" and ext == ".jpeg"):
            new_path = os.path.splitext(temp_path)[0] + real_ext
            os.replace(temp_path, new_path)
            temp_path = new_path
        elif real_ext is None:
            return jsonify({"success": False, "error": "File is not a valid PNG, JPEG or PDF."}), 415

        verifier_id = get_jwt_identity()
        verifier_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        claim = str(request.form.get("claim", "false")).lower() in ("true", "1", "yes")
        claimed_by = request.form.get("claimed_by") or (verifier_id if claim else None)
        if claim and not claimed_by:
            return jsonify({"success": False, "error": "claimed_by is required when claim=true."}), 400

        result = verify_certificate(
            file_path=temp_path,
            verifier_id=verifier_id,
            verifier_ip=verifier_ip,
            claim_cert=claim,
            claimed_by=claimed_by,
        )
        result["success"] = True
        return jsonify(result), 200

    finally:
        cleanup_temp_file(temp_path)
