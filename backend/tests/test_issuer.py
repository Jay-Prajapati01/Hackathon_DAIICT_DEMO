"""Integration tests for the full issuance pipeline."""

import os
import re

import pytest

from modules.crypto import recompute_and_verify
from modules.issuer import SOURCE_CODES, generate_cert_id, issue_certificate
from modules.ledger import get_anomalies, init_db, lookup_certificate
from modules.steg import extract_payload_from_file


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_ledger.db")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("CERT_STORAGE_PATH", str(tmp_path / "certs/"))
    os.makedirs(str(tmp_path / "certs/"), exist_ok=True)
    init_db()


def test_issue_certificate_success():
    result = issue_certificate(
        generator_id="WF-TEST-01",
        source_type="Wind",
        energy_kwh=100.0,
        generation_date="2026-03-01",
        issuer_id="ISSUER-TEST-01",
        output_format="png",
    )
    assert result["success"] is True
    assert result["cert_id"].startswith("REC-WND-")
    assert os.path.exists(result["file_path"])
    assert result["file_name"] == os.path.basename(result["file_path"])
    assert len(result["data_hash"]) == 64  # SHA-256 hex
    assert result["anomaly_flag"] is False
    # raw (non-steg) artwork must not be left behind
    assert not os.path.exists(result["file_path"].replace(".png", "_raw.png"))


def test_issued_certificate_registered_in_ledger():
    result = issue_certificate(
        generator_id="SP-TEST-01",
        source_type="Solar",
        energy_kwh=500.0,
        generation_date="2026-02-01",
        issuer_id="ISSUER-TEST-01",
    )
    record = lookup_certificate(result["cert_id"])
    assert record is not None
    assert record["status"] == "issued"
    assert record["energy_kwh"] == 500.0
    assert record["data_hash"] == result["data_hash"]
    assert record["cert_file_path"] == result["file_path"]


def test_steg_payload_extractable_from_issued_cert():
    result = issue_certificate(
        generator_id="WF-TEST-02",
        source_type="Wind",
        energy_kwh=250.0,
        generation_date="2026-01-15",
        issuer_id="ISSUER-TEST-01",
    )
    payload = extract_payload_from_file(result["file_path"])
    assert payload is not None
    assert payload["energy_kwh"] == 250.0
    assert payload["cert_id"] == result["cert_id"]
    assert payload == result["payload"]


def test_hash_in_payload_matches_data():
    result = issue_certificate(
        generator_id="HYD-TEST-01",
        source_type="Hydro",
        energy_kwh=1000.0,
        generation_date="2026-03-10",
        issuer_id="ISSUER-TEST-01",
    )
    payload = extract_payload_from_file(result["file_path"])
    layer1_pass, layer2_pass, recomputed = recompute_and_verify(payload)
    assert layer1_pass is True  # Hash matches
    assert layer2_pass is True  # Signature valid
    assert recomputed == result["data_hash"]


def test_pdf_format_issuance():
    result = issue_certificate(
        generator_id="WF-TEST-PDF",
        source_type="Wind",
        energy_kwh=42.0,
        generation_date="2026-03-01",
        issuer_id="ISSUER-TEST-01",
        output_format="pdf",
    )
    assert result["success"] is True
    assert result["file_path"].endswith(".pdf")
    payload = extract_payload_from_file(result["file_path"])
    assert payload["cert_id"] == result["cert_id"]
    assert recompute_and_verify(payload)[:2] == (True, True)


def test_duplicate_cert_id_rejected():
    result1 = issue_certificate(
        cert_id="REC-WND-2026-9999",
        generator_id="WF-TEST-03",
        source_type="Wind",
        energy_kwh=100.0,
        generation_date="2026-03-01",
        issuer_id="ISSUER-TEST-01",
    )
    assert result1["success"] is True

    result2 = issue_certificate(
        cert_id="REC-WND-2026-9999",  # Same ID
        generator_id="WF-TEST-03",
        source_type="Wind",
        energy_kwh=100.0,
        generation_date="2026-03-01",
        issuer_id="ISSUER-TEST-01",
    )
    assert result2["success"] is False
    assert "already exists" in result2["error"]


@pytest.mark.parametrize(
    "override, msg",
    [
        ({"energy_kwh": 0.0}, "positive"),
        ({"energy_kwh": -5}, "positive"),
        ({"energy_kwh": "abc"}, "numeric"),
        ({"generator_id": ""}, "generator_id"),
        ({"generation_date": ""}, "generation_date"),
        ({"generation_date": "01/03/2026"}, "YYYY-MM-DD"),
        ({"issuer_id": ""}, "issuer_id"),
        ({"output_format": "docx"}, "output_format"),
    ],
)
def test_invalid_inputs_rejected(override, msg):
    kwargs = dict(
        generator_id="WF-BAD-01",
        source_type="Wind",
        energy_kwh=100.0,
        generation_date="2026-03-01",
        issuer_id="ISSUER-TEST-01",
    )
    kwargs.update(override)
    result = issue_certificate(**kwargs)
    assert result["success"] is False
    assert msg in result["error"]


def test_zero_energy_rejected():
    result = issue_certificate(
        generator_id="WF-BAD-01",
        source_type="Wind",
        energy_kwh=0.0,
        generation_date="2026-03-01",
        issuer_id="ISSUER-TEST-01",
    )
    assert result["success"] is False


def test_anomalous_issuance_is_flagged_but_not_blocked():
    result = issue_certificate(
        generator_id="WF-HUGE",
        source_type="Wind",
        energy_kwh=50_000_000.0,
        generation_date="2026-03-01",
        issuer_id="ISSUER-TEST-01",
    )
    assert result["success"] is True
    assert result["anomaly_flag"] is True
    assert "ceiling" in result["anomaly_reason"]
    assert get_anomalies(resolved=False)[0]["cert_id"] == result["cert_id"]


def test_generate_cert_id_format_and_uniqueness():
    cid = generate_cert_id("Solar", year=2026)
    assert re.fullmatch(r"REC-SLR-2026-\d{4}", cid)
    assert generate_cert_id("Unknown").split("-")[1] == "OTH"
    for src, code in SOURCE_CODES.items():
        assert generate_cert_id(src, ensure_unique=False).split("-")[1] == code
    ids = {generate_cert_id("Wind") for _ in range(20)}
    assert len(ids) > 1
