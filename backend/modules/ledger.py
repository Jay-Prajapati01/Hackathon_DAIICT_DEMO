"""
REC Guard — Shared Ledger Module
Handles all database operations for certificate issuance and verification.
SQLite for MVP; swap DATABASE_URL to PostgreSQL/Hyperledger for production.

The ledger is the single source of truth. It records:
  * rec_ledger        — every issued certificate (append-only in spirit; status changes only)
  * verification_log  — every verification attempt, valid or fraudulent
  * anomaly_log       — statistical anomaly flags raised at issuance time
  * issuers           — registered issuing bodies and their RSA public keys
  * users             — API users (regulator / issuer / buyer / auditor)
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

from config import db_path

log = structlog.get_logger()


def get_db_path() -> str:
    """Resolved at call-time so tests can point DATABASE_URL at a temp file."""
    return db_path()


# ─────────────────────────────────────────────
# Schema SQL
# ─────────────────────────────────────────────
SCHEMA_SQL = """
-- ============================================================
-- REC Certificates Ledger
-- This is the single source of truth for all issued RECs.
-- Every verification check references this table.
-- ============================================================
CREATE TABLE IF NOT EXISTS rec_ledger (
    cert_id         TEXT PRIMARY KEY,       -- Unique certificate ID (e.g. REC-WND-2026-0091)
    generator_id    TEXT NOT NULL,           -- Generator plant/facility ID
    source_type     TEXT NOT NULL,           -- Energy source: Wind, Solar, Hydro, Biomass, etc.
    energy_kwh      REAL NOT NULL,           -- Energy generated in kWh
    generation_date TEXT NOT NULL,           -- ISO date of generation (YYYY-MM-DD)
    issuer_id       TEXT NOT NULL,           -- Issuing body identifier
    data_hash       TEXT NOT NULL,           -- SHA-256 hash of certificate data
    signature       TEXT NOT NULL,           -- RSA-2048 signature (base64-encoded)
    status          TEXT NOT NULL            -- 'issued', 'claimed' or 'revoked'
                    CHECK(status IN ('issued', 'claimed', 'revoked'))
                    DEFAULT 'issued',
    issued_at       TEXT NOT NULL,           -- ISO-8601 timestamp of issuance
    claimed_by      TEXT,                    -- Entity that claimed this REC (buyer ID)
    claimed_at      TEXT,                    -- ISO-8601 timestamp of claim
    cert_file_path  TEXT,                    -- Path to the stored certificate file
    CONSTRAINT chk_claimed CHECK (
        (status = 'issued' AND claimed_by IS NULL AND claimed_at IS NULL) OR
        (status IN ('claimed', 'revoked'))
    )
);

-- ============================================================
-- Verification Audit Log
-- Every single verification attempt is logged here, including
-- attempts with forged / unregistered certificate IDs, so that
-- regulators get a complete audit trail of fraud attempts.
-- ============================================================
CREATE TABLE IF NOT EXISTS verification_log (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cert_id         TEXT NOT NULL,           -- May be 'UNKNOWN' for payload-less forgeries
    verified_at     TEXT NOT NULL,           -- ISO-8601 timestamp
    verifier_ip     TEXT,                    -- IP of verifier (for audit)
    verifier_id     TEXT,                    -- Logged-in user (if any)
    layer1_pass     INTEGER NOT NULL,        -- 0 or 1 (steg integrity)
    layer2_pass     INTEGER NOT NULL,        -- 0 or 1 (crypto signature)
    layer3_pass     INTEGER NOT NULL,        -- 0 or 1 (ledger lookup)
    final_result    TEXT NOT NULL            -- 'VALID' or 'FRAUD'
                    CHECK(final_result IN ('VALID', 'FRAUD', 'TAMPERED')),
    fraud_reason    TEXT,                    -- Which layer failed + reason
    uploaded_hash   TEXT                     -- Hash recomputed from uploaded file
);

-- ============================================================
-- Anomaly Detection Log
-- Records statistical anomaly flags from the ML layer.
-- ============================================================
CREATE TABLE IF NOT EXISTS anomaly_log (
    anomaly_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    cert_id         TEXT NOT NULL,
    flagged_at      TEXT NOT NULL,
    anomaly_score   REAL NOT NULL,           -- Isolation Forest score (< threshold = anomaly)
    anomaly_reason  TEXT NOT NULL,           -- Human-readable reason
    resolved        INTEGER DEFAULT 0,       -- 0 = open, 1 = resolved by regulator
    resolved_by     TEXT,
    resolved_at     TEXT
);

-- ============================================================
-- Issuers Registry
-- Registered certificate issuing bodies and their public keys.
-- ============================================================
CREATE TABLE IF NOT EXISTS issuers (
    issuer_id       TEXT PRIMARY KEY,
    issuer_name     TEXT NOT NULL,
    public_key_pem  TEXT NOT NULL,           -- RSA public key for verification
    registered_at   TEXT NOT NULL,
    is_active       INTEGER DEFAULT 1
);

-- ============================================================
-- Users (JWT auth)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'auditor'
                    CHECK(role IN ('regulator', 'issuer', 'buyer', 'auditor', 'admin')),
    organisation    TEXT,
    created_at      TEXT NOT NULL
);

-- ============================================================
-- Indexes for performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_ledger_generator ON rec_ledger(generator_id);
CREATE INDEX IF NOT EXISTS idx_ledger_status ON rec_ledger(status);
CREATE INDEX IF NOT EXISTS idx_ledger_issued_at ON rec_ledger(issued_at);
CREATE INDEX IF NOT EXISTS idx_ledger_source ON rec_ledger(source_type);
CREATE INDEX IF NOT EXISTS idx_ledger_gen_date ON rec_ledger(generator_id, generation_date);
CREATE INDEX IF NOT EXISTS idx_verif_cert ON verification_log(cert_id);
CREATE INDEX IF NOT EXISTS idx_verif_result ON verification_log(final_result);
CREATE INDEX IF NOT EXISTS idx_anomaly_cert ON anomaly_log(cert_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────
# Database connection context manager
# ─────────────────────────────────────────────


@contextmanager
def get_db():
    """Database connection context manager: commits on success, rolls back on error."""
    path = get_db_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrency
    conn.execute("PRAGMA foreign_keys=ON")  # Enforce FK constraints
    conn.execute("PRAGMA synchronous=NORMAL")  # Balance durability + speed
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        log.error("db_transaction_failed", error=str(e))
        raise
    finally:
        conn.close()


# ─────────────────────────────────────────────
# Init
# ─────────────────────────────────────────────


def init_db():
    """Initialize all tables. Safe to call multiple times (idempotent)."""
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
    log.info("db_initialized", path=get_db_path())


# ─────────────────────────────────────────────
# Ledger Operations
# ─────────────────────────────────────────────


def register_certificate(cert_data: dict) -> bool:
    """
    Register a newly issued certificate in the ledger.
    Returns True on success, False if cert_id already exists.
    """
    with get_db() as conn:
        try:
            conn.execute(
                """
                INSERT INTO rec_ledger (
                    cert_id, generator_id, source_type, energy_kwh,
                    generation_date, issuer_id, data_hash, signature,
                    status, issued_at, cert_file_path
                ) VALUES (
                    :cert_id, :generator_id, :source_type, :energy_kwh,
                    :generation_date, :issuer_id, :data_hash, :signature,
                    'issued', :issued_at, :cert_file_path
                )
            """,
                cert_data,
            )
            log.info("cert_registered", cert_id=cert_data["cert_id"])
            return True
        except sqlite3.IntegrityError:
            log.warning("cert_already_exists", cert_id=cert_data["cert_id"])
            return False


def lookup_certificate(cert_id: str) -> Optional[dict]:
    """Look up a certificate by ID. Returns dict if found, None if not registered."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM rec_ledger WHERE cert_id = ?", (cert_id,)).fetchone()
        return dict(row) if row else None


def mark_claimed(cert_id: str, claimed_by: str) -> bool:
    """
    Mark a certificate as claimed by a buyer.
    Returns True on success, False if not found or already claimed/revoked.
    """
    with get_db() as conn:
        row = conn.execute("SELECT status FROM rec_ledger WHERE cert_id = ?", (cert_id,)).fetchone()

        if not row:
            return False
        if row["status"] != "issued":
            log.warning("cert_not_claimable", cert_id=cert_id, status=row["status"])
            return False

        conn.execute(
            """
            UPDATE rec_ledger
            SET status = 'claimed',
                claimed_by = ?,
                claimed_at = ?
            WHERE cert_id = ?
        """,
            (claimed_by, _now(), cert_id),
        )
        log.info("cert_claimed", cert_id=cert_id, claimed_by=claimed_by)
        return True


def revoke_certificate(cert_id: str, revoked_by: str) -> bool:
    """Revoke a certificate (regulator action). Revoked certificates fail Layer 3."""
    with get_db() as conn:
        row = conn.execute("SELECT status FROM rec_ledger WHERE cert_id = ?", (cert_id,)).fetchone()
        if not row or row["status"] == "revoked":
            return False
        conn.execute(
            """
            UPDATE rec_ledger
            SET status = 'revoked', claimed_by = COALESCE(claimed_by, ?), claimed_at = COALESCE(claimed_at, ?)
            WHERE cert_id = ?
        """,
            (f"REVOKED:{revoked_by}", _now(), cert_id),
        )
        log.info("cert_revoked", cert_id=cert_id, by=revoked_by)
        return True


def delete_certificate(cert_id: str) -> bool:
    """Hard-delete a ledger row. Only used by tests to simulate an unregistered cert."""
    with get_db() as conn:
        cur = conn.execute("DELETE FROM rec_ledger WHERE cert_id = ?", (cert_id,))
        return cur.rowcount > 0


def get_all_certificates(
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    generator_id: Optional[str] = None,
    issuer_id: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[dict]:
    """Paginated, filtered ledger query."""
    query = "SELECT * FROM rec_ledger WHERE 1=1"
    params: List[Any] = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if source_type:
        query += " AND source_type = ?"
        params.append(source_type)
    if generator_id:
        query += " AND generator_id = ?"
        params.append(generator_id)
    if issuer_id:
        query += " AND issuer_id = ?"
        params.append(issuer_id)
    if search:
        like = f"%{search}%"
        query += " AND (cert_id LIKE ? OR generator_id LIKE ? OR issuer_id LIKE ? OR claimed_by LIKE ?)"
        params.extend([like, like, like, like])
    query += " ORDER BY issued_at DESC LIMIT ? OFFSET ?"
    params.extend([int(limit), int(offset)])

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def count_certificates(
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    generator_id: Optional[str] = None,
    issuer_id: Optional[str] = None,
    search: Optional[str] = None,
) -> int:
    """Total row count for the same filters as get_all_certificates (for pagination)."""
    query = "SELECT COUNT(*) FROM rec_ledger WHERE 1=1"
    params: List[Any] = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if source_type:
        query += " AND source_type = ?"
        params.append(source_type)
    if generator_id:
        query += " AND generator_id = ?"
        params.append(generator_id)
    if issuer_id:
        query += " AND issuer_id = ?"
        params.append(issuer_id)
    if search:
        like = f"%{search}%"
        query += " AND (cert_id LIKE ? OR generator_id LIKE ? OR issuer_id LIKE ? OR claimed_by LIKE ?)"
        params.extend([like, like, like, like])
    with get_db() as conn:
        return conn.execute(query, params).fetchone()[0]


def get_generator_history(generator_id: str, limit: int = 500) -> List[dict]:
    """Historical issuance rows for one generator (used by the anomaly layer)."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT cert_id, generator_id, source_type, energy_kwh, generation_date, issued_at
            FROM rec_ledger WHERE generator_id = ?
            ORDER BY issued_at DESC LIMIT ?
        """,
            (generator_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_certificates_for_generation(generator_id: str, generation_date: str) -> List[dict]:
    """All certificates already issued for a generator on a given generation date."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT cert_id, energy_kwh, issued_at, issuer_id FROM rec_ledger
            WHERE generator_id = ? AND generation_date = ?
        """,
            (generator_id, generation_date),
        ).fetchall()
        return [dict(r) for r in rows]


def count_recent_issuances(generator_id: str, since_iso: str) -> int:
    with get_db() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM rec_ledger WHERE generator_id = ? AND issued_at >= ?",
            (generator_id, since_iso),
        ).fetchone()[0]


# ─────────────────────────────────────────────
# Stats / Dashboard
# ─────────────────────────────────────────────


def get_ledger_stats() -> dict:
    """Aggregate statistics for the dashboard."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM rec_ledger").fetchone()[0]
        issued = conn.execute("SELECT COUNT(*) FROM rec_ledger WHERE status='issued'").fetchone()[0]
        claimed = conn.execute("SELECT COUNT(*) FROM rec_ledger WHERE status='claimed'").fetchone()[0]
        revoked = conn.execute("SELECT COUNT(*) FROM rec_ledger WHERE status='revoked'").fetchone()[0]
        total_verifications = conn.execute("SELECT COUNT(*) FROM verification_log").fetchone()[0]
        valid_count = conn.execute("SELECT COUNT(*) FROM verification_log WHERE final_result='VALID'").fetchone()[0]
        fraud_count = conn.execute("SELECT COUNT(*) FROM verification_log WHERE final_result='FRAUD'").fetchone()[0]
        total_kwh = conn.execute("SELECT COALESCE(SUM(energy_kwh),0) FROM rec_ledger").fetchone()[0]
        open_anomalies = conn.execute("SELECT COUNT(*) FROM anomaly_log WHERE resolved=0").fetchone()[0]
        return {
            "total_certificates": total,
            "issued": issued,
            "claimed": claimed,
            "revoked": revoked,
            "total_kwh_registered": float(total_kwh),
            "total_verifications": total_verifications,
            "valid_verifications": valid_count,
            "fraud_attempts_detected": fraud_count,
            "open_anomalies": open_anomalies,
        }


def get_source_breakdown() -> List[dict]:
    """Certificates + kWh grouped by energy source (dashboard chart)."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT source_type, COUNT(*) AS count, COALESCE(SUM(energy_kwh),0) AS total_kwh
            FROM rec_ledger GROUP BY source_type ORDER BY count DESC
        """
        ).fetchall()
        return [dict(r) for r in rows]


def get_fraud_breakdown() -> List[dict]:
    """Fraud attempts grouped by the layer that caught them (dashboard chart)."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
              CASE
                WHEN layer1_pass = 0 THEN 'Layer 1 — Steg Integrity'
                WHEN layer2_pass = 0 THEN 'Layer 2 — Signature'
                WHEN layer3_pass = 0 THEN 'Layer 3 — Ledger'
                ELSE 'Other'
              END AS layer,
              COUNT(*) AS count
            FROM verification_log WHERE final_result = 'FRAUD'
            GROUP BY layer ORDER BY count DESC
        """
        ).fetchall()
        return [dict(r) for r in rows]


def get_daily_activity(days: int = 14) -> List[dict]:
    """Per-day issuance / verification / fraud counts for the trend chart."""
    with get_db() as conn:
        issued = conn.execute(
            """
            SELECT substr(issued_at, 1, 10) AS day, COUNT(*) AS n
            FROM rec_ledger GROUP BY day ORDER BY day DESC LIMIT ?
        """,
            (days,),
        ).fetchall()
        verified = conn.execute(
            """
            SELECT substr(verified_at, 1, 10) AS day,
                   SUM(CASE WHEN final_result='VALID' THEN 1 ELSE 0 END) AS valid,
                   SUM(CASE WHEN final_result='FRAUD' THEN 1 ELSE 0 END) AS fraud
            FROM verification_log GROUP BY day ORDER BY day DESC LIMIT ?
        """,
            (days,),
        ).fetchall()
    merged: Dict[str, dict] = {}
    for r in issued:
        merged.setdefault(r["day"], {"day": r["day"], "issued": 0, "valid": 0, "fraud": 0})["issued"] = r["n"]
    for r in verified:
        entry = merged.setdefault(r["day"], {"day": r["day"], "issued": 0, "valid": 0, "fraud": 0})
        entry["valid"] = r["valid"] or 0
        entry["fraud"] = r["fraud"] or 0
    return sorted(merged.values(), key=lambda x: x["day"])


# ─────────────────────────────────────────────
# Verification audit log
# ─────────────────────────────────────────────


def log_verification(log_data: dict):
    """Append a verification attempt to the audit log."""
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO verification_log (
                cert_id, verified_at, verifier_ip, verifier_id,
                layer1_pass, layer2_pass, layer3_pass,
                final_result, fraud_reason, uploaded_hash
            ) VALUES (
                :cert_id, :verified_at, :verifier_ip, :verifier_id,
                :layer1_pass, :layer2_pass, :layer3_pass,
                :final_result, :fraud_reason, :uploaded_hash
            )
        """,
            log_data,
        )


def get_recent_verifications(limit: int = 20, cert_id: Optional[str] = None) -> List[dict]:
    query = "SELECT * FROM verification_log"
    params: List[Any] = []
    if cert_id:
        query += " WHERE cert_id = ?"
        params.append(cert_id)
    query += " ORDER BY log_id DESC LIMIT ?"
    params.append(int(limit))
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# Anomaly log
# ─────────────────────────────────────────────


def log_anomaly(cert_id: str, score: float, reason: str) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO anomaly_log (cert_id, flagged_at, anomaly_score, anomaly_reason)
            VALUES (?, ?, ?, ?)
        """,
            (cert_id, _now(), float(score), reason),
        )
        return cur.lastrowid


def get_anomalies(resolved: Optional[bool] = None, limit: int = 50) -> List[dict]:
    query = "SELECT * FROM anomaly_log"
    params: List[Any] = []
    if resolved is not None:
        query += " WHERE resolved = ?"
        params.append(1 if resolved else 0)
    query += " ORDER BY anomaly_id DESC LIMIT ?"
    params.append(int(limit))
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def resolve_anomaly(anomaly_id: int, resolved_by: str) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            """
            UPDATE anomaly_log SET resolved = 1, resolved_by = ?, resolved_at = ?
            WHERE anomaly_id = ? AND resolved = 0
        """,
            (resolved_by, _now(), int(anomaly_id)),
        )
        return cur.rowcount > 0


# ─────────────────────────────────────────────
# Issuers registry
# ─────────────────────────────────────────────


def register_issuer(issuer_id: str, name: str, public_key_pem: str) -> bool:
    """Register a new certificate issuing body."""
    with get_db() as conn:
        try:
            conn.execute(
                """
                INSERT INTO issuers (issuer_id, issuer_name, public_key_pem, registered_at)
                VALUES (?, ?, ?, ?)
            """,
                (issuer_id, name, public_key_pem, _now()),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def get_issuer_public_key(issuer_id: str) -> Optional[str]:
    """Retrieve an issuer's public key PEM string for signature verification."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT public_key_pem FROM issuers WHERE issuer_id = ? AND is_active = 1", (issuer_id,)
        ).fetchone()
        return row["public_key_pem"] if row else None


def get_all_issuers() -> List[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT issuer_id, issuer_name, registered_at, is_active FROM issuers ORDER BY registered_at"
        ).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────


def create_user(
    email: str, password_hash: str, role: str = "auditor", organisation: Optional[str] = None
) -> Optional[dict]:
    with get_db() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO users (email, password_hash, role, organisation, created_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (email.lower().strip(), password_hash, role, organisation, _now()),
            )
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (cur.lastrowid,)).fetchone()
            return dict(row)
        except sqlite3.IntegrityError:
            return None


def get_user_by_email(email: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (int(user_id),)).fetchone()
        return dict(row) if row else None
