"""
REC Guard — Configuration

All configuration is read from environment variables (loaded from backend/.env)
with safe defaults. Every accessor is a *function* rather than a module-level
constant so that values can be changed at runtime (tests monkeypatch env vars).

Relative paths are resolved against the backend directory so the application
behaves identically regardless of the current working directory.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

APP_NAME = "REC Guard API"
APP_VERSION = "1.0.0"

ALLOWED_SOURCE_TYPES = ["Wind", "Solar", "Hydro", "Biomass", "Geothermal", "Tidal", "Other"]
ALLOWED_OUTPUT_FORMATS = {"png", "pdf"}
ALLOWED_UPLOAD_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
MAX_UPLOAD_BYTES = 16 * 1024 * 1024  # 16 MB


def resolve_path(path_str: str) -> str:
    """Resolve a possibly-relative path against the backend directory."""
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path)


def env(key: str, default=None):
    return os.getenv(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes", "on")


# ── Paths ──────────────────────────────────────────────────────


def db_path() -> str:
    """SQLite file path derived from DATABASE_URL (sqlite:///relative or sqlite:////absolute)."""
    url = os.getenv("DATABASE_URL", "sqlite:///storage/ledger.db")
    if url.startswith("sqlite:///"):
        url = url[len("sqlite:///") :]
    return resolve_path(url)


def cert_storage_path() -> str:
    return resolve_path(os.getenv("CERT_STORAGE_PATH", "storage/certificates/"))


def temp_storage_path() -> str:
    return resolve_path(os.getenv("TEMP_STORAGE_PATH", "storage/temp/"))


def private_key_path() -> str:
    return resolve_path(os.getenv("RSA_PRIVATE_KEY_PATH", "keys/private.pem"))


def public_key_path() -> str:
    return resolve_path(os.getenv("RSA_PUBLIC_KEY_PATH", "keys/public.pem"))


def anomaly_model_path() -> str:
    return resolve_path(os.getenv("ANOMALY_MODEL_PATH", "models/isolation_forest.pkl"))


def historical_data_path() -> str:
    return resolve_path(os.getenv("HISTORICAL_DATA_PATH", "data/historical_gen.csv"))


# ── Tunables ───────────────────────────────────────────────────


def anomaly_threshold() -> float:
    return float(os.getenv("ANOMALY_THRESHOLD", "-0.1"))


def cors_origins() -> list:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


def jwt_expires_seconds() -> int:
    return int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600"))


def flask_port() -> int:
    return int(os.getenv("FLASK_PORT", "5000"))


def flask_debug() -> bool:
    return env_bool("FLASK_DEBUG", False)
