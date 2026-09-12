"""
REC Guard — Module 1: REC Issuer
Orchestrates the full certificate issuance pipeline.

Pipeline:
  Input data → anomaly screen → SHA-256 hash + RSA sign → render artwork
  → LSB steganographic embed → register in ledger → return issued certificate file
"""

import os
import secrets
from datetime import datetime, timezone
from typing import Optional

import structlog

from config import cert_storage_path
from modules.anomaly import check_issuance_anomaly
from modules.certificate_gen import generate_certificate_png
from modules.crypto import load_private_key, process_certificate_for_issuance
from modules.ledger import lookup_certificate, register_certificate
from modules.steg import embed_payload_in_pdf, embed_payload_in_png

log = structlog.get_logger()

# ─────────────────────────────────────────────
# Certificate ID Generation
# ─────────────────────────────────────────────

SOURCE_CODES = {
    "Wind": "WND",
    "Solar": "SLR",
    "Hydro": "HYD",
    "Biomass": "BIO",
    "Geothermal": "GEO",
    "Tidal": "TDL",
    "Other": "OTH",
}


def generate_cert_id(source_type: str, year: Optional[int] = None, ensure_unique: bool = True) -> str:
    """
    Generate a unique, human-readable certificate ID.
    Format: REC-{SOURCE}-{YEAR}-{NNNN}
    Example: REC-WND-2026-0091
    """
    code = SOURCE_CODES.get(source_type, "OTH")
    yr = year or datetime.now(timezone.utc).year
    for _ in range(50):
        cert_id = f"REC-{code}-{yr}-{secrets.randbelow(10000):04d}"
        if not ensure_unique or lookup_certificate(cert_id) is None:
            return cert_id
    # 4-digit space nearly exhausted for this source/year — widen the suffix
    return f"REC-{code}-{yr}-{secrets.randbelow(10**8):08d}"


# ─────────────────────────────────────────────
# Main Issuance Function
# ─────────────────────────────────────────────


def issue_certificate(
    cert_id: Optional[str] = None,
    generator_id: str = "",
    source_type: str = "Solar",
    energy_kwh: float = 0.0,
    generation_date: str = "",
    issuer_id: str = "",
    output_format: str = "png",  # "png" or "pdf"
) -> dict:
    """
    Full REC certificate issuance pipeline.

    Returns:
        dict with keys:
          success (bool), cert_id, file_path, file_name, data_hash, issued_at,
          payload (full steg payload), anomaly_flag, anomaly_reason, anomaly (full),
          error (if failed)
    """
    try:
        # ── 0. Input Validation ───────────────────────────────
        if not generator_id:
            raise ValueError("generator_id is required.")
        try:
            energy_kwh = float(energy_kwh)
        except (TypeError, ValueError):
            raise ValueError("energy_kwh must be numeric.")
        if energy_kwh <= 0:
            raise ValueError("energy_kwh must be positive.")
        if not generation_date:
            raise ValueError("generation_date is required (YYYY-MM-DD).")
        try:
            datetime.strptime(generation_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("generation_date must be in YYYY-MM-DD format.")
        if not issuer_id:
            raise ValueError("issuer_id is required.")
        output_format = (output_format or "png").lower()
        if output_format not in ("png", "pdf"):
            raise ValueError("output_format must be 'png' or 'pdf'.")

        # ── 1. Generate Certificate ID ────────────────────────
        if not cert_id:
            cert_id = generate_cert_id(source_type)
        elif lookup_certificate(cert_id):
            raise ValueError(f"Certificate ID already exists: {cert_id}")

        issued_at = datetime.now(timezone.utc).isoformat()

        # ── 2. Anomaly Detection (pre-issuance) ───────────────
        anomaly_result = check_issuance_anomaly(
            generator_id=generator_id,
            source_type=source_type,
            energy_kwh=energy_kwh,
            generation_date=generation_date,
            cert_id=cert_id,
        )
        if anomaly_result["is_anomaly"]:
            log.warning(
                "issuance_anomaly_detected",
                cert_id=cert_id,
                reason=anomaly_result["reason"],
                score=anomaly_result["score"],
            )
            # In production: flag for manual review, don't auto-block.
            # For MVP: log (anomaly_log table) and continue.

        # ── 3. Cryptographic Processing ───────────────────────
        private_key = load_private_key()
        steg_payload = process_certificate_for_issuance(
            cert_id=cert_id,
            generator_id=generator_id,
            source_type=source_type,
            energy_kwh=energy_kwh,
            generation_date=generation_date,
            issuer_id=issuer_id,
            issued_at=issued_at,
            private_key=private_key,
        )

        # ── 4. Generate Certificate Visual ───────────────────
        storage = cert_storage_path()
        os.makedirs(storage, exist_ok=True)
        raw_cert_path = os.path.join(storage, f"{cert_id}_raw.png")
        generate_certificate_png(
            cert_id=cert_id,
            generator_id=generator_id,
            source_type=source_type,
            energy_kwh=energy_kwh,
            generation_date=generation_date,
            issuer_id=issuer_id,
            output_path=raw_cert_path,
            issued_at=issued_at,
        )

        # ── 5. Steganographic Embedding ───────────────────────
        final_cert_path = os.path.join(storage, f"{cert_id}.{output_format}")
        if output_format == "pdf":
            embed_payload_in_pdf(raw_cert_path, steg_payload, final_cert_path)
        else:
            embed_payload_in_png(raw_cert_path, steg_payload, final_cert_path)

        # Clean up raw (non-steg) file
        if os.path.exists(raw_cert_path) and raw_cert_path != final_cert_path:
            os.remove(raw_cert_path)

        # ── 6. Register in Ledger ─────────────────────────────
        ledger_entry = {
            "cert_id": cert_id,
            "generator_id": generator_id,
            "source_type": source_type,
            "energy_kwh": energy_kwh,
            "generation_date": generation_date,
            "issuer_id": issuer_id,
            "data_hash": steg_payload["data_hash"],
            "signature": steg_payload["signature"],
            "issued_at": issued_at,
            "cert_file_path": final_cert_path,
        }
        registered = register_certificate(ledger_entry)
        if not registered:
            # Race: someone registered the same ID between lookup and insert.
            if os.path.exists(final_cert_path):
                os.remove(final_cert_path)
            raise RuntimeError("Failed to register certificate in ledger — ID conflict.")

        log.info(
            "certificate_issued_successfully",
            cert_id=cert_id,
            source=source_type,
            kwh=energy_kwh,
            format=output_format,
        )

        return {
            "success": True,
            "cert_id": cert_id,
            "file_path": final_cert_path,
            "file_name": os.path.basename(final_cert_path),
            "format": output_format,
            "data_hash": steg_payload["data_hash"],
            "issued_at": issued_at,
            "payload": steg_payload,
            "anomaly_flag": anomaly_result["is_anomaly"],
            "anomaly_reason": anomaly_result.get("reason"),
            "anomaly": anomaly_result,
        }

    except Exception as e:
        log.error("issuance_failed", error=str(e))
        return {"success": False, "error": str(e)}
