"""
REC Guard — Module 2: REC Verifier
Three-layer fraud detection pipeline.

Layer 1 — Steganographic Integrity:
  Extract hidden LSB payload from uploaded file.
  Recompute SHA-256 hash of visible data.
  Compare to stored hash in payload.
  → Catches: value/unit tampering, no-payload fakes.

Layer 2 — Cryptographic Signature:
  Validate the RSA signature in the payload against the issuer's public key.
  → Catches: forged certificates (payload exists but was not signed by a real issuer).

Layer 3 — Ledger / Registry Lookup:
  Query the shared ledger for the Certificate ID.
  Check: is it registered? Does the ledger hash match? Is it already claimed / revoked?
  → Catches: duplicate issuance (one CertID to two buyers),
             duplicate usage (re-submission of already-claimed cert),
             revoked certificates.

A certificate is VALID only if ALL THREE layers pass.
"""

from datetime import datetime, timezone
from typing import Optional

import structlog

from models.verification_result import VerificationResult
from modules.crypto import compute_file_sha256, load_public_key, load_public_key_from_pem, recompute_and_verify
from modules.ledger import get_anomalies, get_issuer_public_key, log_verification, lookup_certificate, mark_claimed
from modules.steg import extract_payload_from_file

log = structlog.get_logger()

__all__ = ["VerificationResult", "verify_certificate"]


# ─────────────────────────────────────────────
# Main Verification Function
# ─────────────────────────────────────────────


def verify_certificate(
    file_path: str,
    verifier_id: Optional[str] = None,
    verifier_ip: Optional[str] = None,
    claim_cert: bool = False,
    claimed_by: Optional[str] = None,
) -> dict:
    """
    Run the three-layer verification pipeline on an uploaded certificate file.

    Args:
        file_path:    Path to the uploaded certificate (PNG or PDF)
        verifier_id:  Logged-in verifier's user ID (for audit log)
        verifier_ip:  Requester IP address (for audit log)
        claim_cert:   If True and verification passes, mark certificate as claimed
        claimed_by:   Entity claiming the certificate (buyer ID)

    Returns:
        VerificationResult.to_dict() with all layer results and final verdict.
    """
    result = VerificationResult()
    result.verified_at = datetime.now(timezone.utc).isoformat()
    try:
        result.file_sha256 = compute_file_sha256(file_path)
    except OSError:
        result.file_sha256 = ""

    # ── LAYER 1: Steganographic Integrity ────────────────────────
    log.info("verification_layer1_start", file=file_path)

    try:
        extracted = extract_payload_from_file(file_path)
    except ValueError as e:  # unsupported extension
        extracted = None
        log.warning("verification_unsupported_file", error=str(e))

    if extracted is None:
        result.layer1_pass = False
        result.layer1_detail = (
            "No hidden payload found in this certificate file. "
            "This is either a forged document or was not issued by REC Guard."
        )
        result.layer2_detail = "Skipped — Layer 1 failed (no payload to verify signature against)."
        result.layer3_detail = "Skipped — Layer 1 failed."
        result.fraud_reason = "LAYER_1_FAIL: No steganographic payload detected."
        result.final_result = "FRAUD"
        return _finish(result, verifier_id, verifier_ip)

    result.extracted_payload = extracted
    result.cert_id = str(extracted.get("cert_id")) if extracted.get("cert_id") else None

    # Re-verify the hash integrity
    public_key = _resolve_public_key(extracted.get("issuer_id"))
    layer1_pass, layer2_pass, recomputed_hash = recompute_and_verify(extracted, public_key)
    result.uploaded_hash = recomputed_hash

    if layer1_pass:
        result.layer1_pass = True
        result.layer1_detail = (
            f"Hash integrity confirmed. Recomputed SHA-256 matches stored hash: {recomputed_hash[:24]}..."
        )
    else:
        stored = str(extracted.get("data_hash") or "N/A")
        result.layer1_pass = False
        if not recomputed_hash:
            result.layer1_detail = (
                "Hidden payload is present but malformed (missing or corrupted fields). "
                "The certificate data has been altered after issuance."
            )
        else:
            result.layer1_detail = (
                f"HASH MISMATCH. Recomputed: {recomputed_hash[:24]}..., Stored: {stored[:24]}... "
                "The visible certificate data has been altered after issuance."
            )
        result.fraud_reason = "LAYER_1_FAIL: Data hash mismatch — certificate was tampered."
        result.final_result = "FRAUD"
        # Still report layer 2 for full diagnostic; layer 3 is skipped.
        result.layer2_pass = layer2_pass
        result.layer2_detail = _run_layer2(layer2_pass)
        result.layer3_detail = "Skipped — Layer 1 failed (hash mismatch)."
        return _finish(result, verifier_id, verifier_ip)

    # ── LAYER 2: Cryptographic Signature ─────────────────────────
    log.info("verification_layer2_start", cert_id=result.cert_id)

    result.layer2_pass = layer2_pass
    result.layer2_detail = _run_layer2(layer2_pass)

    if not layer2_pass:
        result.fraud_reason = (
            "LAYER_2_FAIL: RSA signature invalid — certificate was not signed by "
            "a registered issuing authority, or signature has been tampered."
        )
        result.final_result = "FRAUD"
        result.layer3_detail = "Skipped — Layer 2 failed."
        return _finish(result, verifier_id, verifier_ip)

    # ── LAYER 3: Ledger Lookup ─────────────────────────────────────
    log.info("verification_layer3_start", cert_id=result.cert_id)

    if not result.cert_id:
        result.layer3_pass = False
        result.layer3_detail = "No Certificate ID found in payload."
        result.fraud_reason = "LAYER_3_FAIL: Missing Certificate ID."
        result.final_result = "FRAUD"
        return _finish(result, verifier_id, verifier_ip)

    ledger_record = lookup_certificate(result.cert_id)

    if ledger_record is None:
        result.layer3_pass = False
        result.layer3_detail = (
            f"Certificate ID '{result.cert_id}' is NOT registered in the ledger. "
            "This certificate was never officially issued."
        )
        result.fraud_reason = "LAYER_3_FAIL: Certificate ID not found in ledger."
        result.final_result = "FRAUD"
        return _finish(result, verifier_id, verifier_ip)

    result.ledger_record = ledger_record

    # The registry copy of the hash must match the file's hash. A mismatch means
    # the same Certificate ID was (re)issued with different data — duplicate issuance.
    if ledger_record.get("data_hash") != extracted.get("data_hash"):
        result.layer3_pass = False
        result.layer3_detail = (
            f"Certificate '{result.cert_id}' is registered, but the ledger hash "
            f"({str(ledger_record.get('data_hash'))[:24]}...) does not match this file's hash "
            f"({str(extracted.get('data_hash'))[:24]}...). Same Certificate ID, different data."
        )
        result.fraud_reason = "LAYER_3_FAIL: Ledger hash mismatch — Certificate ID reused for different data."
        result.final_result = "FRAUD"
        return _finish(result, verifier_id, verifier_ip)

    status = ledger_record.get("status")
    if status == "revoked":
        result.layer3_pass = False
        result.layer3_detail = (
            f"Certificate '{result.cert_id}' has been REVOKED by the regulator "
            f"({ledger_record.get('claimed_by', 'unknown')} on {ledger_record.get('claimed_at', 'unknown')})."
        )
        result.fraud_reason = "LAYER_3_FAIL: Certificate has been revoked."
        result.final_result = "FRAUD"
        return _finish(result, verifier_id, verifier_ip)

    if status == "claimed":
        result.layer3_pass = False
        result.layer3_detail = (
            f"Certificate '{result.cert_id}' has ALREADY been claimed by "
            f"'{ledger_record.get('claimed_by', 'unknown')}' "
            f"on {ledger_record.get('claimed_at', 'unknown')}. "
            "This is a duplicate claim attempt."
        )
        result.fraud_reason = (
            f"LAYER_3_FAIL: Certificate already claimed by "
            f"'{ledger_record.get('claimed_by')}' on {ledger_record.get('claimed_at')}."
        )
        result.final_result = "FRAUD"
        return _finish(result, verifier_id, verifier_ip)

    # All 3 layers passed!
    result.layer3_pass = True
    result.layer3_detail = (
        f"Certificate '{result.cert_id}' is registered, valid, and not yet claimed. "
        f"Source: {ledger_record['source_type']}, "
        f"Energy: {ledger_record['energy_kwh']} kWh, "
        f"Issued: {ledger_record['issued_at']}"
    )
    result.final_result = "VALID"
    result.fraud_reason = None

    # Optional: Mark as claimed
    if claim_cert and claimed_by:
        if mark_claimed(result.cert_id, claimed_by):
            result.claimed = True
            result.ledger_record = lookup_certificate(result.cert_id)
            result.layer3_detail += f" | Certificate now claimed by '{claimed_by}'."

    # Surface any open issuance anomalies for the auditor's attention (informational)
    try:
        result.anomalies = [a for a in get_anomalies(resolved=False, limit=200) if a["cert_id"] == result.cert_id]
    except Exception:
        result.anomalies = []

    log.info("certificate_verified_valid", cert_id=result.cert_id)
    return _finish(result, verifier_id, verifier_ip)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def _resolve_public_key(issuer_id: Optional[str]):
    """
    Resolve the correct RSA public key for this issuer.
    Falls back to the default system key if issuer is not in registry.
    """
    if issuer_id:
        try:
            pem_str = get_issuer_public_key(str(issuer_id))
            if pem_str:
                return load_public_key_from_pem(pem_str)
        except Exception as e:
            log.warning("issuer_key_lookup_failed", issuer_id=issuer_id, error=str(e))
    return load_public_key()  # Default system key


def _run_layer2(layer2_pass: bool) -> str:
    if layer2_pass:
        return "RSA-2048 signature is valid. Certificate was signed by a registered issuing authority."
    return (
        "RSA signature INVALID. Payload exists but was not signed by any registered "
        "issuing body. This is a forged certificate."
    )


def _finish(result: VerificationResult, verifier_id, verifier_ip) -> dict:
    _write_audit_log(result, verifier_id, verifier_ip, result.verified_at)
    return result.to_dict()


def _write_audit_log(result: VerificationResult, verifier_id, verifier_ip, verified_at):
    """Write verification result to the audit log table."""
    try:
        log_verification(
            {
                "cert_id": result.cert_id or "UNKNOWN",
                "verified_at": verified_at,
                "verifier_ip": verifier_ip,
                "verifier_id": verifier_id,
                "layer1_pass": int(result.layer1_pass),
                "layer2_pass": int(result.layer2_pass),
                "layer3_pass": int(result.layer3_pass),
                "final_result": result.final_result,
                "fraud_reason": result.fraud_reason,
                "uploaded_hash": result.uploaded_hash,
            }
        )
    except Exception as e:
        log.error("audit_log_write_failed", error=str(e))
