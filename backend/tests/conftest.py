"""
Shared pytest fixtures.

* A session-scoped RSA key pair is generated in a temp directory so tests never
  depend on (or touch) the repo's keys/.
* Every test gets a fresh SQLite ledger + certificate/temp storage directories.
* HISTORICAL_DATA_PATH points at a non-existent file so the anomaly layer only
  sees what the test itself put in the ledger.
"""

import os

import pytest

from modules.crypto import generate_key_pair
from modules.ledger import init_db


@pytest.fixture(scope="session", autouse=True)
def session_keys(tmp_path_factory):
    key_dir = tmp_path_factory.mktemp("keys")
    priv, pub = generate_key_pair(str(key_dir / "private.pem"), str(key_dir / "public.pem"), overwrite=True)
    mp = pytest.MonkeyPatch()
    mp.setenv("RSA_PRIVATE_KEY_PATH", priv)
    mp.setenv("RSA_PUBLIC_KEY_PATH", pub)
    mp.setenv("LOG_LEVEL", "WARNING")
    mp.setenv("LOG_FORMAT", "console")
    yield {"private": priv, "public": pub}
    mp.undo()


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Fresh ledger + storage for every test."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/ledger.db")
    monkeypatch.setenv("CERT_STORAGE_PATH", str(tmp_path / "certs"))
    monkeypatch.setenv("TEMP_STORAGE_PATH", str(tmp_path / "temp"))
    monkeypatch.setenv("HISTORICAL_DATA_PATH", str(tmp_path / "no_history.csv"))
    monkeypatch.setenv("ANOMALY_THRESHOLD", "-0.1")
    os.makedirs(tmp_path / "certs", exist_ok=True)
    os.makedirs(tmp_path / "temp", exist_ok=True)
    init_db()
    yield tmp_path


@pytest.fixture
def issue_kwargs():
    """Baseline valid issuance arguments."""
    return {
        "generator_id": "TEST-GEN-01",
        "source_type": "Wind",
        "energy_kwh": 100.0,
        "generation_date": "2026-03-01",
        "issuer_id": "ISSUER-TEST-01",
        "output_format": "png",
    }
