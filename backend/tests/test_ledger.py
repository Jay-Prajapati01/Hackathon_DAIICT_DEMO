"""Tests for the SQLite ledger operations."""

import sqlite3

import pytest

from modules import ledger


def _entry(cert_id="REC-WND-2026-0001", **over):
    base = {
        "cert_id": cert_id,
        "generator_id": "WF-A-01",
        "source_type": "Wind",
        "energy_kwh": 100.0,
        "generation_date": "2026-03-01",
        "issuer_id": "ISSUER-TEST",
        "data_hash": "ab" * 32,
        "signature": "sig",
        "issued_at": "2026-03-02T10:00:00+00:00",
        "cert_file_path": "/tmp/x.png",
    }
    base.update(over)
    return base


def test_init_db_is_idempotent():
    ledger.init_db()
    ledger.init_db()
    with ledger.get_db() as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"rec_ledger", "verification_log", "anomaly_log", "issuers", "users"} <= tables


def test_register_and_lookup():
    assert ledger.register_certificate(_entry()) is True
    rec = ledger.lookup_certificate("REC-WND-2026-0001")
    assert rec["status"] == "issued"
    assert rec["energy_kwh"] == 100.0
    assert rec["claimed_by"] is None
    assert ledger.lookup_certificate("MISSING") is None


def test_duplicate_register_rejected():
    assert ledger.register_certificate(_entry()) is True
    assert ledger.register_certificate(_entry()) is False


def test_status_check_constraint():
    ledger.register_certificate(_entry())
    with pytest.raises(sqlite3.IntegrityError):
        with ledger.get_db() as conn:
            conn.execute("UPDATE rec_ledger SET status='bogus' WHERE cert_id='REC-WND-2026-0001'")


def test_mark_claimed_lifecycle():
    ledger.register_certificate(_entry())
    assert ledger.mark_claimed("REC-WND-2026-0001", "BUYER-X") is True
    rec = ledger.lookup_certificate("REC-WND-2026-0001")
    assert rec["status"] == "claimed"
    assert rec["claimed_by"] == "BUYER-X"
    assert rec["claimed_at"]
    assert ledger.mark_claimed("REC-WND-2026-0001", "BUYER-Y") is False  # duplicate claim
    assert ledger.lookup_certificate("REC-WND-2026-0001")["claimed_by"] == "BUYER-X"
    assert ledger.mark_claimed("NOPE", "BUYER-Y") is False


def test_revoke():
    ledger.register_certificate(_entry())
    assert ledger.revoke_certificate("REC-WND-2026-0001", "regulator@x") is True
    assert ledger.lookup_certificate("REC-WND-2026-0001")["status"] == "revoked"
    assert ledger.revoke_certificate("REC-WND-2026-0001", "regulator@x") is False
    assert ledger.mark_claimed("REC-WND-2026-0001", "BUYER") is False


def test_delete_certificate():
    ledger.register_certificate(_entry())
    assert ledger.delete_certificate("REC-WND-2026-0001") is True
    assert ledger.lookup_certificate("REC-WND-2026-0001") is None
    assert ledger.delete_certificate("REC-WND-2026-0001") is False


def test_list_filters_pagination_and_count():
    for i in range(5):
        ledger.register_certificate(_entry(f"REC-WND-2026-{i:04d}", issued_at=f"2026-03-0{i + 1}T00:00:00+00:00"))
    for i in range(3):
        ledger.register_certificate(_entry(f"REC-SLR-2026-{i:04d}", source_type="Solar", generator_id="SP-C-01"))
    ledger.mark_claimed("REC-SLR-2026-0000", "BUYER-Q")

    assert ledger.count_certificates() == 8
    assert len(ledger.get_all_certificates(limit=3)) == 3
    assert len(ledger.get_all_certificates(limit=3, offset=6)) == 2
    assert ledger.count_certificates(source_type="Solar") == 3
    assert ledger.count_certificates(status="claimed") == 1
    assert ledger.count_certificates(generator_id="SP-C-01") == 3
    assert ledger.count_certificates(search="BUYER-Q") == 1
    assert [c["cert_id"] for c in ledger.get_all_certificates(search="WND", limit=2)] == [
        "REC-WND-2026-0004",
        "REC-WND-2026-0003",
    ]  # newest first


def test_stats_and_breakdowns():
    ledger.register_certificate(_entry("A", energy_kwh=100))
    ledger.register_certificate(_entry("B", energy_kwh=250, source_type="Solar"))
    ledger.mark_claimed("B", "X")
    ledger.log_verification(_verif("A", "VALID", 1, 1, 1))
    ledger.log_verification(_verif("A", "FRAUD", 0, 0, 0, "LAYER_1_FAIL"))
    ledger.log_verification(_verif("B", "FRAUD", 1, 1, 0, "LAYER_3_FAIL"))
    ledger.log_anomaly("B", -0.5, "weird")

    s = ledger.get_ledger_stats()
    assert s["total_certificates"] == 2
    assert s["issued"] == 1 and s["claimed"] == 1
    assert s["total_kwh_registered"] == 350.0
    assert s["fraud_attempts_detected"] == 2
    assert s["valid_verifications"] == 1
    assert s["open_anomalies"] == 1

    src = {r["source_type"]: r for r in ledger.get_source_breakdown()}
    assert src["Solar"]["total_kwh"] == 250.0
    fraud = {r["layer"]: r["count"] for r in ledger.get_fraud_breakdown()}
    assert fraud["Layer 1 — Steg Integrity"] == 1
    assert fraud["Layer 3 — Ledger"] == 1
    daily = ledger.get_daily_activity()
    assert daily and daily[-1]["fraud"] == 2 and daily[-1]["valid"] == 1


def _verif(cert_id, result, l1, l2, l3, reason=None):
    return {
        "cert_id": cert_id,
        "verified_at": "2026-03-03T00:00:00+00:00",
        "verifier_ip": "127.0.0.1",
        "verifier_id": None,
        "layer1_pass": l1,
        "layer2_pass": l2,
        "layer3_pass": l3,
        "final_result": result,
        "fraud_reason": reason,
        "uploaded_hash": "",
    }


def test_verification_log_accepts_unknown_cert_ids():
    """Forged files with no payload must still be recorded for the audit trail."""
    ledger.log_verification(_verif("UNKNOWN", "FRAUD", 0, 0, 0, "no payload"))
    recent = ledger.get_recent_verifications()
    assert recent[0]["cert_id"] == "UNKNOWN"
    assert ledger.get_recent_verifications(cert_id="UNKNOWN")[0]["fraud_reason"] == "no payload"
    assert ledger.get_recent_verifications(cert_id="OTHER") == []


def test_anomaly_log_and_resolve():
    aid = ledger.log_anomaly("REC-X", -0.42, "too big")
    assert ledger.get_anomalies(resolved=False)[0]["anomaly_id"] == aid
    assert ledger.resolve_anomaly(aid, "reg@x") is True
    assert ledger.resolve_anomaly(aid, "reg@x") is False
    assert ledger.get_anomalies(resolved=False) == []
    assert ledger.get_anomalies(resolved=True)[0]["resolved_by"] == "reg@x"


def test_issuer_registry():
    assert ledger.register_issuer("ISS-1", "Green Cert", "-----BEGIN PUBLIC KEY-----\nabc") is True
    assert ledger.register_issuer("ISS-1", "Green Cert", "x") is False
    assert ledger.get_issuer_public_key("ISS-1").startswith("-----BEGIN")
    assert ledger.get_issuer_public_key("NOPE") is None
    assert [i["issuer_id"] for i in ledger.get_all_issuers()] == ["ISS-1"]


def test_users():
    u = ledger.create_user("Admin@Example.com", "hash", role="admin", organisation="Org")
    assert u["email"] == "admin@example.com"
    assert ledger.create_user("admin@example.com", "hash") is None
    assert ledger.get_user_by_email("ADMIN@example.com")["role"] == "admin"
    assert ledger.get_user_by_id(u["user_id"])["organisation"] == "Org"
    assert ledger.get_user_by_email("nobody@x") is None


def test_generator_history_helpers():
    for i in range(3):
        ledger.register_certificate(_entry(f"C{i}", generation_date="2026-03-01", energy_kwh=10 * (i + 1)))
    assert len(ledger.get_generator_history("WF-A-01")) == 3
    same_day = ledger.get_certificates_for_generation("WF-A-01", "2026-03-01")
    assert sum(r["energy_kwh"] for r in same_day) == 60
    assert ledger.count_recent_issuances("WF-A-01", "2000-01-01T00:00:00+00:00") == 3
