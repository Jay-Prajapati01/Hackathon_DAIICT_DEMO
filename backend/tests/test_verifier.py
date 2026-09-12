"""Tests for all four fraud scenarios + valid baseline (three-layer verifier)."""

import base64
import os

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from PIL import Image

from modules import ledger
from modules.crypto import sign_hash
from modules.issuer import issue_certificate
from modules.ledger import get_recent_verifications, init_db, mark_claimed
from modules.steg import embed_payload_in_png, extract_payload_from_file
from modules.verifier import verify_certificate


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("CERT_STORAGE_PATH", str(tmp_path / "certs/"))
    os.makedirs(str(tmp_path / "certs/"), exist_ok=True)
    init_db()


def issue_test_cert(**kwargs):
    return issue_certificate(
        **{
            "generator_id": "TEST-GEN-01",
            "source_type": "Wind",
            "energy_kwh": 100.0,
            "generation_date": "2026-03-01",
            "issuer_id": "ISSUER-TEST-01",
            "output_format": "png",
            **kwargs,
        }
    )


def _layers(result):
    return [v["passed"] for v in result["layers"].values()]


def _tamper(file_path, out_path, **changes):
    """Simulate a fraudster editing the certificate: change visible data, keep old hash/signature."""
    payload = extract_payload_from_file(file_path)
    payload.update(changes)
    return embed_payload_in_png(file_path, payload, out_path)


# ─────────────────────────────────────────────
# Baseline
# ─────────────────────────────────────────────


def test_valid_certificate_passes_all_layers():
    issued = issue_test_cert()
    result = verify_certificate(issued["file_path"])
    assert result["final_result"] == "VALID"
    assert result["is_valid"] is True
    assert result["layers"]["layer1_steganographic_integrity"]["passed"] is True
    assert result["layers"]["layer2_cryptographic_signature"]["passed"] is True
    assert result["layers"]["layer3_ledger_lookup"]["passed"] is True
    assert result["fraud_reason"] is None
    assert result["cert_id"] == issued["cert_id"]
    assert result["ledger_record"]["status"] == "issued"
    assert result["extracted_data"]["energy_kwh"] == 100.0
    assert len(result["file_sha256"]) == 64
    assert result["claimed"] is False


def test_valid_pdf_certificate():
    issued = issue_test_cert(output_format="pdf")
    result = verify_certificate(issued["file_path"])
    assert result["final_result"] == "VALID"
    assert _layers(result) == [True, True, True]


# ─────────────────────────────────────────────
# Scenario 1 — value tampering (100 → 1000 kWh)
# ─────────────────────────────────────────────


def test_scenario1_value_tampering_caught_by_layer1(tmp_path):
    """Layer 1: Energy edited from 100 kWh to 1000 kWh after issuance."""
    issued = issue_test_cert(energy_kwh=100.0)
    tampered_path = _tamper(issued["file_path"], str(tmp_path / "tampered.png"), energy_kwh=1000.0)

    result = verify_certificate(tampered_path)
    assert result["final_result"] == "FRAUD"
    assert result["layers"]["layer1_steganographic_integrity"]["passed"] is False
    assert "HASH MISMATCH" in result["layers"]["layer1_steganographic_integrity"]["detail"]
    assert result["fraud_reason"].startswith("LAYER_1_FAIL")
    # Signature still verifies over the *old* hash — reported for diagnostics only
    assert result["layers"]["layer2_cryptographic_signature"]["passed"] is True
    assert result["layers"]["layer3_ledger_lookup"]["passed"] is False
    assert "Skipped" in result["layers"]["layer3_ledger_lookup"]["detail"]


def test_scenario1_pixel_level_corruption_caught_by_layer1(tmp_path):
    """Layer 1: attacker edits the image itself, corrupting the LSB payload area."""
    issued = issue_test_cert(energy_kwh=100.0)
    img = Image.open(issued["file_path"])
    pixels = list(img.getdata())
    # Corrupt a pixel inside the steg payload area (pixel 200 = payload byte 75)
    pixels[200] = (pixels[200][0] ^ 0xFF, pixels[200][1], pixels[200][2])
    tampered = Image.new("RGB", img.size)
    tampered.putdata(pixels)
    tampered_path = str(tmp_path / "tampered.png")
    tampered.save(tampered_path)

    result = verify_certificate(tampered_path)
    assert result["final_result"] == "FRAUD"
    assert result["layers"]["layer1_steganographic_integrity"]["passed"] is False


# ─────────────────────────────────────────────
# Scenario 2 — same CertID sold to two buyers
# ─────────────────────────────────────────────


def test_scenario2_duplicate_certid_caught_by_layer3():
    """Layer 3: Same CertID claimed by two buyers."""
    issued = issue_test_cert(cert_id="REC-SLR-TEST-0034", energy_kwh=1000.0, source_type="Solar")
    # First claim succeeds
    result1 = verify_certificate(issued["file_path"], claim_cert=True, claimed_by="BUYER-X")
    assert result1["final_result"] == "VALID"
    assert result1["claimed"] is True
    assert result1["ledger_record"]["claimed_by"] == "BUYER-X"

    # Second claim with a copy of the same file is rejected
    result2 = verify_certificate(issued["file_path"], claim_cert=True, claimed_by="BUYER-Y")
    assert result2["final_result"] == "FRAUD"
    assert result2["layers"]["layer3_ledger_lookup"]["passed"] is False
    assert "already claimed" in result2["fraud_reason"].lower()
    assert "BUYER-X" in result2["fraud_reason"]
    assert ledger.lookup_certificate("REC-SLR-TEST-0034")["claimed_by"] == "BUYER-X"


def test_scenario2b_same_certid_reissued_with_different_data(tmp_path):
    """Layer 3: a second, differently-valued certificate carrying an existing CertID."""
    issued = issue_test_cert(cert_id="REC-DUP-0001", energy_kwh=100.0)
    # Simulate the issuer's registry being overwritten for that ID with different data
    with ledger.get_db() as conn:
        conn.execute("UPDATE rec_ledger SET data_hash = ? WHERE cert_id = ?", ("ff" * 32, "REC-DUP-0001"))
    result = verify_certificate(issued["file_path"])
    assert result["final_result"] == "FRAUD"
    assert _layers(result) == [True, True, False]
    assert "hash mismatch" in result["fraud_reason"].lower()


# ─────────────────────────────────────────────
# Scenario 3 — post-issuance edit (500 → 5000 kWh)
# ─────────────────────────────────────────────


def test_scenario3_post_issuance_edit_caught_by_layer1(tmp_path):
    """Layer 1: 500 kWh edited to 5000 kWh post-issuance."""
    issued = issue_test_cert(energy_kwh=500.0, source_type="Solar")
    corrupt_path = _tamper(issued["file_path"], str(tmp_path / "corrupt.png"), energy_kwh=5000.0)

    result = verify_certificate(corrupt_path)
    assert result["final_result"] == "FRAUD"
    assert result["layers"]["layer1_steganographic_integrity"]["passed"] is False
    assert result["extracted_data"]["energy_kwh"] == 5000.0
    assert result["uploaded_hash"] != result["extracted_data"]["data_hash"]


def test_scenario3b_unit_or_date_edit_caught_by_layer1(tmp_path):
    issued = issue_test_cert()
    p1 = _tamper(issued["file_path"], str(tmp_path / "a.png"), generation_date="2026-03-02")
    p2 = _tamper(issued["file_path"], str(tmp_path / "b.png"), source_type="Solar")
    p3 = _tamper(issued["file_path"], str(tmp_path / "c.png"), generator_id="OTHER-GEN")
    for p in (p1, p2, p3):
        r = verify_certificate(p)
        assert r["final_result"] == "FRAUD" and r["fraud_reason"].startswith("LAYER_1_FAIL")


# ─────────────────────────────────────────────
# Scenario 4 — duplicate claim / re-use
# ─────────────────────────────────────────────


def test_scenario4_duplicate_claim_caught_by_layer3():
    """Layer 3: Certificate claimed once, then resubmitted."""
    issued = issue_test_cert(cert_id="REC-WND-TEST-0102", energy_kwh=750.0)
    # Valid first claim
    r1 = verify_certificate(issued["file_path"], claim_cert=True, claimed_by="BUYER-ECO")
    assert r1["final_result"] == "VALID"
    # Duplicate resubmission (even without asking to claim)
    r2 = verify_certificate(issued["file_path"])
    assert r2["final_result"] == "FRAUD"
    assert r2["layers"]["layer3_ledger_lookup"]["passed"] is False
    assert "BUYER-ECO" in r2["layers"]["layer3_ledger_lookup"]["detail"]


def test_claim_via_ledger_then_verify_is_fraud():
    issued = issue_test_cert()
    mark_claimed(issued["cert_id"], "BUYER-DIRECT")
    r = verify_certificate(issued["file_path"])
    assert r["final_result"] == "FRAUD" and "already claimed" in r["fraud_reason"].lower()


# ─────────────────────────────────────────────
# Forgeries
# ─────────────────────────────────────────────


def test_no_payload_certificate_caught_by_layer1(tmp_path):
    """Layer 1: Plain PNG with no steganographic payload (forged document)."""
    plain_img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    plain_path = str(tmp_path / "no_payload.png")
    plain_img.save(plain_path)

    result = verify_certificate(plain_path)
    assert result["final_result"] == "FRAUD"
    assert result["layers"]["layer1_steganographic_integrity"]["passed"] is False
    assert "no hidden payload" in result["layers"]["layer1_steganographic_integrity"]["detail"].lower()
    assert result["cert_id"] is None
    assert result["extracted_data"] is None


def test_forged_payload_with_attackers_own_key_caught_by_layer2(tmp_path):
    """Layer 2: attacker embeds a well-formed payload signed with their own RSA key."""
    issued = issue_test_cert()
    payload = extract_payload_from_file(issued["file_path"])
    payload["energy_kwh"] = 9999.0
    from modules.crypto import build_canonical_payload, compute_sha256

    canonical = build_canonical_payload(
        **{
            k: payload[k]
            for k in (
                "cert_id",
                "generator_id",
                "source_type",
                "energy_kwh",
                "generation_date",
                "issuer_id",
                "issued_at",
            )
        }
    )
    payload["data_hash"] = compute_sha256(canonical)  # attacker recomputes the hash correctly
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    payload["signature"] = sign_hash(payload["data_hash"], attacker_key)
    forged = embed_payload_in_png(issued["file_path"], payload, str(tmp_path / "forged.png"))

    result = verify_certificate(forged)
    assert result["final_result"] == "FRAUD"
    assert _layers(result) == [True, False, False]
    assert result["fraud_reason"].startswith("LAYER_2_FAIL")


def test_garbage_signature_caught_by_layer2(tmp_path):
    issued = issue_test_cert()
    payload = extract_payload_from_file(issued["file_path"])
    payload["signature"] = base64.b64encode(b"\x01" * 256).decode()
    forged = embed_payload_in_png(issued["file_path"], payload, str(tmp_path / "forged.png"))
    r = verify_certificate(forged)
    assert r["final_result"] == "FRAUD" and _layers(r) == [True, False, False]


def test_unregistered_certid_caught_by_layer3():
    """Layer 3: Signed payload but cert_id not in ledger (offline forgery / deleted record)."""
    issued = issue_test_cert(cert_id="REC-WND-TEST-GHOST")
    assert ledger.delete_certificate("REC-WND-TEST-GHOST")
    result = verify_certificate(issued["file_path"])
    assert result["final_result"] == "FRAUD"
    assert _layers(result) == [True, True, False]
    assert "not found in ledger" in result["fraud_reason"].lower()


def test_revoked_certificate_caught_by_layer3():
    issued = issue_test_cert()
    ledger.revoke_certificate(issued["cert_id"], "regulator@recguard.io")
    r = verify_certificate(issued["file_path"])
    assert r["final_result"] == "FRAUD" and "revoked" in r["fraud_reason"].lower()


def test_unsupported_file_is_fraud_not_exception(tmp_path):
    f = tmp_path / "cert.txt"
    f.write_text("hello")
    r = verify_certificate(str(f))
    assert r["final_result"] == "FRAUD" and r["fraud_reason"].startswith("LAYER_1_FAIL")


# ─────────────────────────────────────────────
# Audit trail / issuer registry
# ─────────────────────────────────────────────


def test_every_verification_is_audit_logged(tmp_path):
    issued = issue_test_cert()
    verify_certificate(issued["file_path"], verifier_id="auditor@x", verifier_ip="10.0.0.1")
    plain = tmp_path / "plain.png"
    Image.new("RGB", (100, 100)).save(plain)
    verify_certificate(str(plain))
    logs = get_recent_verifications(limit=10)
    assert [l["final_result"] for l in logs] == ["FRAUD", "VALID"]
    assert logs[0]["cert_id"] == "UNKNOWN"
    assert logs[1]["verifier_id"] == "auditor@x" and logs[1]["verifier_ip"] == "10.0.0.1"
    assert logs[1]["uploaded_hash"] == issued["data_hash"]


def test_registered_issuer_key_is_used_for_layer2():
    """If the issuer has its own registered public key, Layer 2 must use it."""
    issued = issue_test_cert(issuer_id="ISSUER-OTHER")
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    from modules.crypto import public_key_to_pem

    ledger.register_issuer("ISSUER-OTHER", "Other Body", public_key_to_pem(other.public_key()))
    r = verify_certificate(issued["file_path"])
    assert r["final_result"] == "FRAUD" and r["fraud_reason"].startswith("LAYER_2_FAIL")


def test_claim_requires_claimed_by():
    issued = issue_test_cert()
    r = verify_certificate(issued["file_path"], claim_cert=True, claimed_by=None)
    assert r["final_result"] == "VALID" and r["claimed"] is False
    assert ledger.lookup_certificate(issued["cert_id"])["status"] == "issued"


def test_open_anomalies_surfaced_on_valid_result():
    issued = issue_test_cert(energy_kwh=50_000_000.0)
    r = verify_certificate(issued["file_path"])
    assert r["final_result"] == "VALID"
    assert r["anomalies"] and r["anomalies"][0]["cert_id"] == issued["cert_id"]
