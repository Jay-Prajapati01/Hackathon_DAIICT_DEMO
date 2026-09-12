"""
REC Guard — Cryptography Module
Handles SHA-256 hashing and RSA-2048 signing/verification.

Every REC certificate goes through this module during issuance.
Every uploaded certificate goes through verify_signature() during verification.
"""

import base64
import hashlib
import json
import os
from typing import Optional, Tuple

import structlog
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

from config import private_key_path, public_key_path, resolve_path

log = structlog.get_logger()

# ─────────────────────────────────────────────
# Key Generation / Loading
# ─────────────────────────────────────────────


def generate_key_pair(
    private_path: Optional[str] = None, public_path: Optional[str] = None, overwrite: bool = False
) -> Tuple[str, str]:
    """
    Generate an RSA-2048 key pair and write PEM files.
    Returns (private_path, public_path). Existing keys are kept unless overwrite=True.
    """
    priv = private_path or private_key_path()
    pub = public_path or public_key_path()
    if os.path.exists(priv) and os.path.exists(pub) and not overwrite:
        log.info("keys_already_exist", private=priv, public=pub)
        return priv, pub

    os.makedirs(os.path.dirname(priv) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(pub) or ".", exist_ok=True)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    with open(priv, "wb") as f:
        f.write(private_pem)
    with open(pub, "wb") as f:
        f.write(public_pem)
    try:
        os.chmod(priv, 0o600)
    except OSError:
        pass
    log.info("rsa_key_pair_generated", private=priv, public=pub)
    return priv, pub


def load_private_key(path: Optional[str] = None) -> RSAPrivateKey:
    """Load RSA private key from PEM file."""
    key_path = resolve_path(path) if path else private_key_path()
    with open(key_path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_public_key(path: Optional[str] = None) -> RSAPublicKey:
    """Load RSA public key from PEM file."""
    key_path = resolve_path(path) if path else public_key_path()
    with open(key_path, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def load_public_key_from_pem(pem_string: str) -> RSAPublicKey:
    """Load RSA public key from a PEM string (for multi-issuer support)."""
    return serialization.load_pem_public_key(pem_string.encode())


def public_key_to_pem(public_key: RSAPublicKey) -> str:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


def public_key_fingerprint(public_key: RSAPublicKey) -> str:
    """SHA-256 fingerprint of the DER-encoded public key (for display / audit)."""
    der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der).hexdigest()


# ─────────────────────────────────────────────
# Certificate Payload Construction
# ─────────────────────────────────────────────


def build_canonical_payload(
    cert_id: str,
    generator_id: str,
    source_type: str,
    energy_kwh: float,
    generation_date: str,
    issuer_id: str,
    issued_at: str,
) -> dict:
    """
    Build the canonical (deterministic) dict that gets hashed.
    Field order is fixed — changing order changes the hash.
    """
    return {
        "cert_id": cert_id,
        "generator_id": generator_id,
        "source_type": source_type,
        "energy_kwh": round(float(energy_kwh), 6),
        "generation_date": generation_date,
        "issuer_id": issuer_id,
        "issued_at": issued_at,
    }


# ─────────────────────────────────────────────
# Hashing
# ─────────────────────────────────────────────


def compute_sha256(data: dict) -> str:
    """
    Compute SHA-256 hash of a canonical dict.
    JSON is serialized with sorted keys and no spaces for determinism.
    Returns hex-encoded hash string.
    """
    canonical_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_sha256_string(s: str) -> str:
    """Compute SHA-256 of a raw string."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def compute_file_sha256(path: str) -> str:
    """SHA-256 of a file on disk (used for audit of uploaded files)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ─────────────────────────────────────────────
# Signing
# ─────────────────────────────────────────────

_PSS = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH)


def sign_hash(data_hash: str, private_key: RSAPrivateKey) -> str:
    """
    Sign a SHA-256 hash string with the issuer's RSA-2048 private key.
    Uses PSS padding with SHA-256 for maximum security.
    Returns base64-encoded signature string.
    """
    signature_bytes = private_key.sign(data_hash.encode("utf-8"), _PSS, hashes.SHA256())
    return base64.b64encode(signature_bytes).decode("utf-8")


# ─────────────────────────────────────────────
# Verification
# ─────────────────────────────────────────────


def verify_signature(data_hash: str, signature_b64: str, public_key: RSAPublicKey) -> bool:
    """
    Verify a signature against the data hash using the issuer's public key.
    Returns True if valid, False if forged/tampered.
    """
    try:
        signature_bytes = base64.b64decode(signature_b64)
        public_key.verify(signature_bytes, data_hash.encode("utf-8"), _PSS, hashes.SHA256())
        log.info("signature_valid")
        return True
    except InvalidSignature:
        log.warning("signature_invalid")
        return False
    except Exception as e:
        log.error("signature_verification_error", error=str(e))
        return False


# ─────────────────────────────────────────────
# Full Certificate Cryptographic Processing
# ─────────────────────────────────────────────


def process_certificate_for_issuance(
    cert_id: str,
    generator_id: str,
    source_type: str,
    energy_kwh: float,
    generation_date: str,
    issuer_id: str,
    issued_at: str,
    private_key: Optional[RSAPrivateKey] = None,
) -> dict:
    """
    Full cryptographic processing pipeline for a new REC certificate.
    Returns dict containing hash, signature, and full steg payload.
    """
    if private_key is None:
        private_key = load_private_key()

    # 1. Build canonical payload
    canonical = build_canonical_payload(
        cert_id, generator_id, source_type, energy_kwh, generation_date, issuer_id, issued_at
    )

    # 2. Compute SHA-256 hash
    data_hash = compute_sha256(canonical)

    # 3. Sign the hash
    signature = sign_hash(data_hash, private_key)

    # 4. Build the full steganographic payload (what gets hidden in the image)
    steg_payload = {**canonical, "data_hash": data_hash, "signature": signature}

    log.info("cert_cryptographic_processing_complete", cert_id=cert_id, hash_prefix=data_hash[:16])
    return steg_payload


def recompute_and_verify(extracted_payload: dict, public_key: Optional[RSAPublicKey] = None) -> Tuple[bool, bool, str]:
    """
    Given a payload extracted from a certificate file:
    1. Rebuild canonical dict from visible fields
    2. Recompute SHA-256 hash
    3. Compare to stored hash (Layer 1 check)
    4. Verify signature (Layer 2 check)

    Returns (layer1_pass, layer2_pass, recomputed_hash)
    """
    if public_key is None:
        public_key = load_public_key()

    # Rebuild canonical from extracted fields
    try:
        canonical = build_canonical_payload(
            cert_id=extracted_payload["cert_id"],
            generator_id=extracted_payload["generator_id"],
            source_type=extracted_payload["source_type"],
            energy_kwh=extracted_payload["energy_kwh"],
            generation_date=extracted_payload["generation_date"],
            issuer_id=extracted_payload["issuer_id"],
            issued_at=extracted_payload["issued_at"],
        )
    except (KeyError, TypeError, ValueError) as e:
        log.error("payload_missing_or_malformed_field", error=str(e))
        return False, False, ""

    # Recompute hash
    recomputed_hash = compute_sha256(canonical)

    # Layer 1: Hash integrity check
    stored_hash = str(extracted_payload.get("data_hash", "") or "")
    layer1_pass = recomputed_hash == stored_hash

    # Layer 2: Signature check — the signature covers the *stored* hash, so a
    # forger who edits data must also forge a signature over the new hash.
    stored_sig = str(extracted_payload.get("signature", "") or "")
    layer2_pass = verify_signature(stored_hash, stored_sig, public_key) if stored_hash and stored_sig else False

    log.info("crypto_verification", layer1=layer1_pass, layer2=layer2_pass, cert_id=extracted_payload.get("cert_id"))

    return layer1_pass, layer2_pass, recomputed_hash
