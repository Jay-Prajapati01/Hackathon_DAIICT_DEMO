"""Tests for the statistical / rule-based anomaly layer."""

from datetime import datetime, timedelta, timezone

from modules import ledger
from modules.anomaly import BURST_LIMIT_24H, MAX_KWH_PER_CERT, check_issuance_anomaly


def _seed(generator_id, values, source="Wind", date="2026-01-01"):
    for i, kwh in enumerate(values):
        ledger.register_certificate(
            {
                "cert_id": f"{generator_id}-{i:04d}",
                "generator_id": generator_id,
                "source_type": source,
                "energy_kwh": kwh,
                "generation_date": (datetime(2026, 1, 1) + timedelta(days=i)).strftime("%Y-%m-%d"),
                "issuer_id": "ISS",
                "data_hash": "00" * 32,
                "signature": "s",
                "issued_at": (datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=i)).isoformat(),
                "cert_file_path": None,
            }
        )


def test_normal_first_issuance_is_not_anomalous():
    r = check_issuance_anomaly("NEW-GEN", "Solar", 500.0, "2026-03-01")
    assert r["is_anomaly"] is False
    assert r["reason"] is None
    assert r["method"] == "rules"


def test_future_generation_date_flagged():
    future = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
    r = check_issuance_anomaly("G", "Wind", 100.0, future)
    assert r["is_anomaly"] and "future" in r["reason"]
    assert r["score"] == -1.0


def test_stale_generation_date_flagged():
    r = check_issuance_anomaly("G", "Wind", 100.0, "2015-01-01")
    assert r["is_anomaly"] and "years old" in r["reason"]


def test_invalid_date_flagged():
    r = check_issuance_anomaly("G", "Wind", 100.0, "not-a-date")
    assert r["is_anomaly"] and "Invalid generation_date" in r["reason"]


def test_physical_ceiling_flagged():
    r = check_issuance_anomaly("G", "Solar", MAX_KWH_PER_CERT["Solar"] + 1, "2026-03-01")
    assert r["is_anomaly"] and "ceiling" in r["reason"]


def test_duplicate_issuance_pattern_flagged():
    _seed("WF-A-01", [100.0], date="2026-01-01")
    r = check_issuance_anomaly("WF-A-01", "Wind", 100.0, "2026-01-01")
    assert r["is_anomaly"]
    assert "already has 1 certificate(s) for 2026-01-01" in r["reason"]


def test_cumulative_ceiling_flagged():
    _seed("WF-A-01", [MAX_KWH_PER_CERT["Wind"] * 0.9], date="2026-01-01")
    r = check_issuance_anomaly("WF-A-01", "Wind", MAX_KWH_PER_CERT["Wind"] * 0.5, "2026-01-01")
    assert any("Cumulative" in x for x in r["reasons"])


def test_issuance_burst_flagged():
    now = datetime.now(timezone.utc)
    for i in range(BURST_LIMIT_24H):
        ledger.register_certificate(
            {
                "cert_id": f"BURST-{i}",
                "generator_id": "BURSTY",
                "source_type": "Wind",
                "energy_kwh": 10.0,
                "generation_date": "2026-02-01",
                "issuer_id": "ISS",
                "data_hash": "00" * 32,
                "signature": "s",
                "issued_at": (now - timedelta(minutes=i)).isoformat(),
                "cert_file_path": None,
            }
        )
    r = check_issuance_anomaly("BURSTY", "Wind", 10.0, "2026-03-01")
    assert any("burst" in x for x in r["reasons"])


def test_zscore_used_with_small_history():
    _seed("Z", [100, 101, 99, 100, 102])
    ok = check_issuance_anomaly("Z", "Wind", 100.0, "2026-03-01")
    assert ok["method"] == "zscore" and ok["is_anomaly"] is False
    bad = check_issuance_anomaly("Z", "Wind", 5000.0, "2026-03-01")
    assert bad["method"] == "zscore" and bad["is_anomaly"] is True
    assert "standard deviations" in bad["reason"]


def test_isolation_forest_used_with_enough_history():
    _seed("IF", [100 + (i % 5) for i in range(15)])
    ok = check_issuance_anomaly("IF", "Wind", 102.0, "2026-03-01")
    assert ok["method"] == "isolation_forest"
    assert ok["history_size"] == 15
    assert ok["is_anomaly"] is False
    bad = check_issuance_anomaly("IF", "Wind", 100000.0, "2026-03-01")
    assert bad["method"] == "isolation_forest"
    assert bad["is_anomaly"] is True
    assert bad["score"] < ok["score"]


def test_csv_history_is_used(tmp_path, monkeypatch):
    csv = tmp_path / "hist.csv"
    rows = ["generator_id,source_type,energy_kwh,generation_date"]
    rows += [f"CSV-GEN,Solar,{1000 + i},2026-01-{i + 1:02d}" for i in range(12)]
    csv.write_text("\n".join(rows))
    monkeypatch.setenv("HISTORICAL_DATA_PATH", str(csv))
    r = check_issuance_anomaly("CSV-GEN", "Solar", 1005.0, "2026-03-01")
    assert r["history_size"] == 12 and r["method"] == "isolation_forest"


def test_anomaly_persisted_when_cert_id_given():
    r = check_issuance_anomaly("G", "Solar", MAX_KWH_PER_CERT["Solar"] * 2, "2026-03-01", cert_id="REC-X")
    assert r["is_anomaly"]
    logged = ledger.get_anomalies(resolved=False)
    assert logged and logged[0]["cert_id"] == "REC-X"
    assert "ceiling" in logged[0]["anomaly_reason"]


def test_not_persisted_without_cert_id_or_when_disabled():
    check_issuance_anomaly("G", "Solar", MAX_KWH_PER_CERT["Solar"] * 2, "2026-03-01")
    check_issuance_anomaly("G", "Solar", MAX_KWH_PER_CERT["Solar"] * 2, "2026-03-01", cert_id="X", persist=False)
    assert ledger.get_anomalies() == []


def test_never_raises(monkeypatch):
    monkeypatch.setattr(ledger, "get_certificates_for_generation", lambda *a, **k: 1 / 0)
    r = check_issuance_anomaly("G", "Wind", 1.0, "2026-03-01")
    assert r["is_anomaly"] is False and r["method"] == "error"
