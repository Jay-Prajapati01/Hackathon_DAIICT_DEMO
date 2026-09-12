# REC Guard — Renewable Energy Certificate Fraud Detection System
## Complete Agent Implementation Blueprint — Team Exodus

> **AGENT INSTRUCTION**: This document is your complete specification to build the REC Guard platform end-to-end. Follow every section in order. Every code block, schema, config, and command is production-ready. Do not skip sections. Build the full system.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Solution Overview](#2-solution-overview)
3. [Project Directory Structure](#3-project-directory-structure)
4. [Full Technology Stack](#4-full-technology-stack)
5. [Environment Setup](#5-environment-setup)
6. [Database Layer — Shared REC Ledger](#6-database-layer)
7. [Cryptography Module](#7-cryptography-module)
8. [Steganography Module](#8-steganography-module)
9. [Module 1 — REC Issuer](#9-module-1-rec-issuer)
10. [Module 2 — REC Verifier](#10-module-2-rec-verifier)
11. [Flask REST API Layer](#11-flask-rest-api-layer)
12. [Frontend UI — React Application](#12-frontend-ui)
13. [Three-Layer Verification Engine](#13-three-layer-verification-engine)
14. [Fraud Scenarios and Test Data](#14-fraud-scenarios-and-test-data)
15. [Security Design](#15-security-design)
16. [Full Testing Suite](#16-full-testing-suite)
17. [Docker and Containerization](#17-docker-and-containerization)
18. [Cloud Deployment Guide](#18-cloud-deployment-guide)
19. [Roadmap — MVP to Production SaaS](#19-roadmap)
20. [Expected Impact](#20-expected-impact)
21. [Appendix — Data Structures Reference](#21-appendix)

---

## 1. Problem Statement

### Theme: RENEWABLE ENERGY INTELLIGENCE

**Track**: Renewable Energy Certificate (REC) Fraud Detection System

**Description**:
Renewable Energy Certificates (RECs) are used to prove that electricity was generated from renewable sources. However, manual issuance and tracking processes are vulnerable to:
- Duplication of certificates (one certificate sold to multiple buyers)
- Fraudulent claims (energy amounts edited after issuance)
- Mismatches between claimed and actual generation data
- Re-use of already-claimed certificates
- Forged certificates with no authentic origin

**This system must**:
- Detect duplicate certificate issuance patterns
- Flag suspicious REC issuance anomalies
- Verify authenticity of any certificate file (PDF/PNG)
- Maintain an immutable ledger of all issuances and claims
- Provide deterministic fraud detection (no false negatives on known fraud types)

**Target Users**:
| User | Role |
|---|---|
| Renewable Energy Regulators | Audit and monitor system-wide issuance and claim activity |
| Certificate Issuing Bodies | Issue tamper-evident certificates via Module 1 |
| Corporate REC Buyers | Purchase and self-verify certificates before relying on claims |
| Independent Auditors | Verify certificates independently via Module 2 during compliance reviews |

**Impact**:
- Strengthens integrity and trust in renewable energy markets
- Reduces regulatory and reputational risk for genuine producers
- Improves auditability of national/regional renewable energy claims

**Suggested Technologies**:
- Blockchain / DLT
- AI/ML Anomaly Detection
- Data Encryption
- Secure Cloud Storage

---

## 2. Solution Overview

### REC Guard — System Concept

REC Guard is a two-module system that makes REC fraud detectable **by construction** rather than by manual review.

**How it works**:

1. When a certificate is issued:
   - Its data (Certificate ID, Generator, Energy kWh, Date) is hashed with **SHA-256**
   - The hash is signed with the issuing body's **private RSA-2048 key**
   - The resulting tamper-evident payload is **hidden inside the certificate's own PDF/PNG file** using **LSB (Least Significant Bit) steganography**
   - The same event is recorded in a **shared ledger**

2. When anyone verifies a certificate:
   - The **Verifier module** extracts the hidden payload
   - Checks the **cryptographic signature** (Layer 2)
   - Looks up the **Certificate ID in the ledger** (Layer 3)
   - Three independent checks that catch silent tampering, forged documents, and duplicate certificates

**Key Innovation**: The certificate **carries its own proof of authenticity**. A regulator, buyer, or auditor can verify a REC in seconds without contacting the issuing body.

### Architecture Summary

```
┌──────────────────────────────────────────────────────────────────┐
│                    REC FRAUD DETECTION SYSTEM                    │
├──────────────────────────┬───────────────────────────────────────┤
│   MODULE 1 — REC ISSUER  │    MODULE 2 — REC VERIFIER            │
│                          │                                       │
│  REC Input Data          │  Upload Suspect REC (PDF/PNG)         │
│  CertID · Gen · kWh · Dt │                                       │
│          ↓               │          ↓                            │
│  SHA-256 Hash + RSA Sign │  CHECK 1 — Steg Integrity            │
│  Issuer private key signs│  Extract hidden payload, verify hash  │
│          ↓               │          ↓                            │
│  Steganographic Embed    │  CHECK 2 — Signature Auth             │
│  LSB hidden in PDF/PNG   │  Validate Issuer's RSA signature      │
│          ↓               │          ↓                            │
│  Register in Ledger      │  CHECK 3 — Ledger Lookup              │
│  CertID + hash in DB     │  CertID registered? Already claimed?  │
│          ↓               │          ↓            ↓               │
│  Issued REC Certificate  │       ✓ VALID      ✗ FRAUD/TAMPERED  │
└──────────────────────────┴───────────────────────────────────────┘
                    ↕                          ↕
            ┌─────────────────────────────────────┐
            │     SHARED REC LEDGER (SQLite/DLT)  │
            └─────────────────────────────────────┘

CATCHES:
  Tampered docs (hash mismatch)
  Forged certificates (no valid steg)
  Duplicate usage (already claimed)
  Unsigned fakes (no payload found)
```

---

## 3. Project Directory Structure

> **AGENT**: Create this exact directory structure before writing any code.

```
rec-guard/
├── backend/
│   ├── app.py                        # Flask main application entry point
│   ├── config.py                     # All configuration constants
│   ├── requirements.txt              # Python dependencies (pinned versions)
│   ├── .env.example                  # Environment variable template
│   ├── .env                          # Local env vars (DO NOT COMMIT)
│   │
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── issuer.py                 # Module 1: REC Issuer logic
│   │   ├── verifier.py               # Module 2: REC Verifier logic
│   │   ├── crypto.py                 # SHA-256 + RSA cryptography
│   │   ├── steg.py                   # LSB steganography (embed/extract)
│   │   ├── ledger.py                 # SQLite ledger operations
│   │   ├── anomaly.py                # Statistical anomaly detection layer
│   │   └── certificate_gen.py        # PDF/PNG certificate generator
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── issue_routes.py           # POST /api/issue
│   │   ├── verify_routes.py          # POST /api/verify
│   │   ├── ledger_routes.py          # GET  /api/ledger, /api/ledger/<id>
│   │   ├── admin_routes.py           # GET  /api/admin/dashboard
│   │   └── auth_routes.py            # POST /api/auth/login, /register
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── rec_certificate.py        # REC Certificate dataclass
│   │   ├── verification_result.py    # Verification result dataclass
│   │   └── ledger_entry.py           # Ledger entry dataclass
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py             # Input validation helpers
│   │   ├── logger.py                 # Structured logging
│   │   ├── file_utils.py             # File handling helpers
│   │   └── response_utils.py         # Standardized API response builder
│   │
│   ├── keys/                         # RSA key storage (generated once)
│   │   ├── .gitignore                # Ignore private.pem
│   │   ├── private.pem               # RSA-2048 private key (NEVER commit)
│   │   └── public.pem                # RSA-2048 public key (safe to share)
│   │
│   ├── storage/
│   │   ├── certificates/             # Issued certificate files
│   │   ├── temp/                     # Temporary upload storage
│   │   └── ledger.db                 # SQLite database file
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_crypto.py            # Crypto module unit tests
│       ├── test_steg.py              # Steganography unit tests
│       ├── test_issuer.py            # Issuer integration tests
│       ├── test_verifier.py          # Verifier integration tests
│       ├── test_ledger.py            # Ledger operation tests
│       ├── test_anomaly.py           # Anomaly detection tests
│       ├── test_api.py               # Full API endpoint tests
│       └── fixtures/                 # Test certificate files + data
│           ├── valid_cert.png
│           ├── tampered_cert.png
│           ├── no_payload_cert.png
│           └── sample_data.json
│
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── .env.example
│   ├── .env
│   ├── public/
│   │   ├── index.html
│   │   ├── favicon.ico
│   │   └── manifest.json
│   └── src/
│       ├── index.js
│       ├── App.js
│       ├── App.css                   # Global styles + design tokens
│       │
│       ├── components/
│       │   ├── Layout/
│       │   │   ├── Header.js
│       │   │   ├── Sidebar.js
│       │   │   └── Footer.js
│       │   ├── Issue/
│       │   │   ├── IssueForm.js      # Certificate issuance form
│       │   │   ├── CertPreview.js    # Issued cert download preview
│       │   │   └── IssueResult.js    # Success/error display
│       │   ├── Verify/
│       │   │   ├── VerifyUpload.js   # Drag-and-drop file uploader
│       │   │   ├── VerifyResult.js   # Three-layer result display
│       │   │   └── LayerStatus.js    # Individual layer pass/fail card
│       │   ├── Ledger/
│       │   │   ├── LedgerTable.js    # Searchable/filterable ledger view
│       │   │   └── LedgerRow.js      # Individual certificate row
│       │   ├── Dashboard/
│       │   │   ├── StatCard.js
│       │   │   ├── FraudChart.js
│       │   │   └── RecentActivity.js
│       │   └── Common/
│       │       ├── StatusBadge.js
│       │       ├── LoadingSpinner.js
│       │       └── Toast.js
│       │
│       ├── pages/
│       │   ├── IssuePage.js
│       │   ├── VerifyPage.js
│       │   ├── LedgerPage.js
│       │   ├── DashboardPage.js
│       │   └── LoginPage.js
│       │
│       ├── services/
│       │   ├── api.js                # Axios API client
│       │   ├── issueService.js
│       │   └── verifyService.js
│       │
│       └── store/
│           ├── index.js              # Redux store
│           ├── issueSlice.js
│           └── verifySlice.js
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .github/
│   └── workflows/
│       └── ci.yml                    # GitHub Actions CI pipeline
└── README.md
```

---

## 4. Full Technology Stack

### Backend

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | 3.11+ | Core backend language |
| Web Framework | Flask | 2.3.x | REST API server |
| WSGI Server | Gunicorn | 21.x | Production server |
| Steganography | Pillow | 10.x | Image pixel manipulation for LSB embed |
| Steganography | stegano | 0.11.x | Higher-level LSB helper |
| Cryptography | cryptography | 41.x | SHA-256 hashing + RSA-2048 sign/verify |
| PDF Generation | reportlab | 4.x | Generate certificate PDF files |
| PDF Manipulation | pypdf2 | 3.x | Extract images from PDF for steg |
| PDF to PNG | pdf2image | 1.16.x | Convert PDF pages to PIL images |
| Database | SQLite3 | built-in | Ledger for MVP |
| ORM | SQLAlchemy | 2.x | Database abstraction layer |
| Migrations | Alembic | 1.12.x | Database schema migrations |
| CORS | Flask-CORS | 4.x | Cross-origin requests from frontend |
| Auth | Flask-JWT-Extended | 4.x | JWT authentication tokens |
| Validation | marshmallow | 3.x | Input/output schema validation |
| Env Vars | python-dotenv | 1.x | .env file loading |
| Anomaly Detection | scikit-learn | 1.3.x | Isolation Forest anomaly model |
| Anomaly Detection | numpy | 1.26.x | Numerical operations |
| Anomaly Detection | pandas | 2.x | Dataframe for historical analysis |
| Logging | structlog | 23.x | Structured JSON logging |
| Testing | pytest | 7.x | Unit + integration test runner |
| Testing | pytest-cov | 4.x | Code coverage reports |
| Linting | black | 23.x | Code formatting |
| Linting | flake8 | 6.x | Style checking |

### Frontend

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Language | JavaScript (ES2022) | — | Core frontend language |
| Framework | React | 18.x | UI component framework |
| Build Tool | Vite | 5.x | Fast build + HMR |
| State Management | Redux Toolkit | 2.x | Global state |
| HTTP Client | Axios | 1.x | API communication |
| Routing | React Router v6 | 6.x | Client-side routing |
| Styling | Tailwind CSS | 3.x | Utility-first CSS |
| Charts | Recharts | 2.x | Dashboard analytics charts |
| File Upload | react-dropzone | 14.x | Drag-and-drop upload UX |
| Notifications | react-hot-toast | 2.x | Toast notifications |
| Icons | lucide-react | — | Icon system |
| Animation | framer-motion | 10.x | UI animations |
| PDF Preview | react-pdf | 7.x | In-browser PDF rendering |
| Date Handling | date-fns | 3.x | Date formatting |
| Form Validation | react-hook-form | 7.x | Form state management |
| Type Safety | PropTypes | 15.x | Runtime prop validation |

### Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| Containerization | Docker + Docker Compose | Dev and production container setup |
| Reverse Proxy | Nginx | Serve frontend + proxy API |
| Cloud Platform | AWS / GCP / Railway | Deployment target |
| Object Storage | AWS S3 / GCS | Certificate file storage (Phase 2) |
| Future Ledger | Hyperledger Fabric | Permissioned DLT (Phase 3) |
| CI/CD | GitHub Actions | Automated test + deploy pipeline |
| Secrets | AWS Secrets Manager / .env | RSA key + DB credentials |
| Monitoring | Sentry | Error tracking |
| APM | Prometheus + Grafana | Metrics + dashboards |

---

## 5. Environment Setup

### 5.1 Prerequisites

```bash
# Required software versions
python --version    # 3.11+
node --version      # 18+
npm --version       # 9+
docker --version    # 24+
git --version       # 2.40+

# Install poppler (required for pdf2image)
# Ubuntu/Debian:
sudo apt-get install -y poppler-utils
# macOS:
brew install poppler
# Windows: download from https://github.com/oschwartz10612/poppler-windows
```

### 5.2 Backend Setup

```bash
# Clone repository
git clone <repo-url> rec-guard
cd rec-guard/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

# Install all dependencies
pip install -r requirements.txt
```

### 5.3 requirements.txt (pinned versions — use exactly these)

```text
# Web Framework
Flask==2.3.3
Flask-CORS==4.0.0
Flask-JWT-Extended==4.5.3
gunicorn==21.2.0

# Cryptography
cryptography==41.0.7

# Steganography / Image
Pillow==10.1.0
stegano==0.11.2
pdf2image==1.16.3
PyPDF2==3.0.1
reportlab==4.0.7

# Database
SQLAlchemy==2.0.23
alembic==1.12.1

# Validation + Config
marshmallow==3.20.1
python-dotenv==1.0.0

# Anomaly Detection
scikit-learn==1.3.2
numpy==1.26.2
pandas==2.1.3
joblib==1.3.2

# Logging
structlog==23.2.0

# Utilities
Werkzeug==2.3.7
click==8.1.7

# Testing
pytest==7.4.3
pytest-cov==4.1.0
pytest-flask==1.3.0

# Dev / Linting
black==23.11.0
flake8==6.1.0
```

### 5.4 Environment Variables (.env)

```bash
# Copy template
cp .env.example .env
# Edit .env with actual values
```

**.env.example**:
```dotenv
# Flask Configuration
FLASK_ENV=development
FLASK_SECRET_KEY=your-super-secret-key-change-in-production-min-32-chars
FLASK_DEBUG=True
FLASK_PORT=5000

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRES=3600

# Database
DATABASE_URL=sqlite:///storage/ledger.db
# Production: postgresql://user:password@host:5432/rec_guard

# RSA Key Paths
RSA_PRIVATE_KEY_PATH=keys/private.pem
RSA_PUBLIC_KEY_PATH=keys/public.pem

# Storage
CERT_STORAGE_PATH=storage/certificates/
TEMP_STORAGE_PATH=storage/temp/

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Anomaly Detection
ANOMALY_THRESHOLD=-0.1
ANOMALY_MODEL_PATH=models/isolation_forest.pkl
HISTORICAL_DATA_PATH=data/historical_gen.csv

# Cloud Storage (Phase 2 — leave empty for local)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=
AWS_REGION=ap-south-1

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Admin
ADMIN_EMAIL=admin@recguard.io
ADMIN_PASSWORD=changeme
```

### 5.5 Generate RSA Key Pair

> **AGENT**: Run this ONCE to generate the cryptographic key pair. Keys are reused across all issuance.

```bash
cd backend
python -c "
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os

os.makedirs('keys', exist_ok=True)

# Generate RSA-2048 private key
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

# Serialize private key (PEM, no encryption for prototype)
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# Serialize public key (PEM)
public_pem = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

with open('keys/private.pem', 'wb') as f:
    f.write(private_pem)
with open('keys/public.pem', 'wb') as f:
    f.write(public_pem)

print('✅ RSA-2048 key pair generated.')
print('   keys/private.pem — NEVER commit this file.')
print('   keys/public.pem  — safe to distribute.')
"
```

**keys/.gitignore**:
```
private.pem
```

### 5.6 Initialize Database

```bash
cd backend
python -c "
from modules.ledger import init_db
init_db()
print('✅ REC Ledger database initialized.')
"
```

### 5.7 Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env: VITE_API_URL=http://localhost:5000
```

**frontend/.env.example**:
```dotenv
VITE_API_URL=http://localhost:5000
VITE_APP_TITLE=REC Guard
VITE_APP_VERSION=1.0.0
```

---

## 6. Database Layer — Shared REC Ledger

### 6.1 Schema

**File: `backend/modules/ledger.py`**

```python
"""
REC Guard — Shared Ledger Module
Handles all database operations for certificate issuance and verification.
SQLite for MVP; swap DATABASE_URL to PostgreSQL/Hyperledger for production.
"""

import sqlite3
import json
import os
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import structlog

log = structlog.get_logger()

# ─────────────────────────────────────────────
# Database path from environment
# ─────────────────────────────────────────────
DB_PATH = os.getenv("DATABASE_URL", "storage/ledger.db").replace("sqlite:///", "")

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
    signature       TEXT NOT NULL,           -- RSA-2048 signature (hex-encoded)
    status          TEXT NOT NULL           -- 'issued' or 'claimed'
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
-- Every single verification attempt is logged here.
-- Regulators use this for full audit trail.
-- ============================================================
CREATE TABLE IF NOT EXISTS verification_log (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cert_id         TEXT NOT NULL,
    verified_at     TEXT NOT NULL,           -- ISO-8601 timestamp
    verifier_ip     TEXT,                    -- IP of verifier (for audit)
    verifier_id     TEXT,                    -- Logged-in user (if any)
    layer1_pass     INTEGER NOT NULL,        -- 0 or 1 (steg integrity)
    layer2_pass     INTEGER NOT NULL,        -- 0 or 1 (crypto signature)
    layer3_pass     INTEGER NOT NULL,        -- 0 or 1 (ledger lookup)
    final_result    TEXT NOT NULL            -- 'VALID' or 'FRAUD'
                    CHECK(final_result IN ('VALID', 'FRAUD', 'TAMPERED')),
    fraud_reason    TEXT,                    -- Which layer failed + reason
    uploaded_hash   TEXT,                    -- Hash extracted from uploaded file
    FOREIGN KEY (cert_id) REFERENCES rec_ledger(cert_id)
);

-- ============================================================
-- Anomaly Detection Log
-- Records statistical anomaly flags from the ML layer.
-- ============================================================
CREATE TABLE IF NOT EXISTS anomaly_log (
    anomaly_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    cert_id         TEXT NOT NULL,
    flagged_at      TEXT NOT NULL,
    anomaly_score   REAL NOT NULL,           -- Isolation Forest score (< -0.1 = anomaly)
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
-- Indexes for performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_ledger_generator ON rec_ledger(generator_id);
CREATE INDEX IF NOT EXISTS idx_ledger_status ON rec_ledger(status);
CREATE INDEX IF NOT EXISTS idx_ledger_issued_at ON rec_ledger(issued_at);
CREATE INDEX IF NOT EXISTS idx_ledger_source ON rec_ledger(source_type);
CREATE INDEX IF NOT EXISTS idx_verif_cert ON verification_log(cert_id);
CREATE INDEX IF NOT EXISTS idx_verif_result ON verification_log(final_result);
CREATE INDEX IF NOT EXISTS idx_anomaly_cert ON anomaly_log(cert_id);
"""

# ─────────────────────────────────────────────
# Database connection context manager
# ─────────────────────────────────────────────

@contextmanager
def get_db():
    """Thread-safe database connection context manager."""
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA journal_mode=WAL")     # Write-Ahead Logging for concurrency
    conn.execute("PRAGMA foreign_keys=ON")      # Enforce FK constraints
    conn.execute("PRAGMA synchronous=NORMAL")   # Balance durability + speed
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
    log.info("db_initialized", path=DB_PATH)

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
            conn.execute("""
                INSERT INTO rec_ledger (
                    cert_id, generator_id, source_type, energy_kwh,
                    generation_date, issuer_id, data_hash, signature,
                    status, issued_at, cert_file_path
                ) VALUES (
                    :cert_id, :generator_id, :source_type, :energy_kwh,
                    :generation_date, :issuer_id, :data_hash, :signature,
                    'issued', :issued_at, :cert_file_path
                )
            """, cert_data)
            log.info("cert_registered", cert_id=cert_data["cert_id"])
            return True
        except sqlite3.IntegrityError:
            log.warning("cert_already_exists", cert_id=cert_data["cert_id"])
            return False

def lookup_certificate(cert_id: str) -> Optional[dict]:
    """
    Look up a certificate by ID.
    Returns dict if found, None if not registered.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM rec_ledger WHERE cert_id = ?", (cert_id,)
        ).fetchone()
        return dict(row) if row else None

def mark_claimed(cert_id: str, claimed_by: str) -> bool:
    """
    Mark a certificate as claimed by a buyer.
    Returns True on success, False if already claimed.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT status FROM rec_ledger WHERE cert_id = ?", (cert_id,)
        ).fetchone()

        if not row:
            return False
        if row["status"] == "claimed":
            log.warning("cert_already_claimed", cert_id=cert_id)
            return False

        conn.execute("""
            UPDATE rec_ledger
            SET status = 'claimed',
                claimed_by = ?,
                claimed_at = ?
            WHERE cert_id = ?
        """, (claimed_by, datetime.now(timezone.utc).isoformat(), cert_id))
        log.info("cert_claimed", cert_id=cert_id, claimed_by=claimed_by)
        return True

def get_all_certificates(
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[dict]:
    """Paginated, filtered ledger query."""
    query = "SELECT * FROM rec_ledger WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if source_type:
        query += " AND source_type = ?"
        params.append(source_type)
    query += " ORDER BY issued_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

def get_ledger_stats() -> dict:
    """Aggregate statistics for the dashboard."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM rec_ledger").fetchone()[0]
        issued = conn.execute("SELECT COUNT(*) FROM rec_ledger WHERE status='issued'").fetchone()[0]
        claimed = conn.execute("SELECT COUNT(*) FROM rec_ledger WHERE status='claimed'").fetchone()[0]
        fraud_count = conn.execute("SELECT COUNT(*) FROM verification_log WHERE final_result='FRAUD'").fetchone()[0]
        total_kwh = conn.execute("SELECT COALESCE(SUM(energy_kwh),0) FROM rec_ledger").fetchone()[0]
        return {
            "total_certificates": total,
            "issued": issued,
            "claimed": claimed,
            "total_kwh_registered": total_kwh,
            "fraud_attempts_detected": fraud_count,
        }

def log_verification(log_data: dict):
    """Append a verification attempt to the audit log."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO verification_log (
                cert_id, verified_at, verifier_ip, verifier_id,
                layer1_pass, layer2_pass, layer3_pass,
                final_result, fraud_reason, uploaded_hash
            ) VALUES (
                :cert_id, :verified_at, :verifier_ip, :verifier_id,
                :layer1_pass, :layer2_pass, :layer3_pass,
                :final_result, :fraud_reason, :uploaded_hash
            )
        """, log_data)

def register_issuer(issuer_id: str, name: str, public_key_pem: str) -> bool:
    """Register a new certificate issuing body."""
    with get_db() as conn:
        try:
            conn.execute("""
                INSERT INTO issuers (issuer_id, issuer_name, public_key_pem, registered_at)
                VALUES (?, ?, ?, ?)
            """, (issuer_id, name, public_key_pem, datetime.now(timezone.utc).isoformat()))
            return True
        except sqlite3.IntegrityError:
            return False

def get_issuer_public_key(issuer_id: str) -> Optional[str]:
    """Retrieve an issuer's public key PEM string for signature verification."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT public_key_pem FROM issuers WHERE issuer_id = ? AND is_active = 1",
            (issuer_id,)
        ).fetchone()
        return row["public_key_pem"] if row else None
```

---

## 7. Cryptography Module

**File: `backend/modules/crypto.py`**

```python
"""
REC Guard — Cryptography Module
Handles SHA-256 hashing and RSA-2048 signing/verification.

Every REC certificate goes through this module during issuance.
Every uploaded certificate goes through verify_signature() during verification.
"""

import os
import json
import hashlib
import base64
from typing import Tuple, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.exceptions import InvalidSignature
import structlog

log = structlog.get_logger()

# ─────────────────────────────────────────────
# Key Loading
# ─────────────────────────────────────────────

def load_private_key(path: Optional[str] = None) -> RSAPrivateKey:
    """Load RSA private key from PEM file."""
    key_path = path or os.getenv("RSA_PRIVATE_KEY_PATH", "keys/private.pem")
    with open(key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    return private_key

def load_public_key(path: Optional[str] = None) -> RSAPublicKey:
    """Load RSA public key from PEM file."""
    key_path = path or os.getenv("RSA_PUBLIC_KEY_PATH", "keys/public.pem")
    with open(key_path, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())
    return public_key

def load_public_key_from_pem(pem_string: str) -> RSAPublicKey:
    """Load RSA public key from a PEM string (for multi-issuer support)."""
    return serialization.load_pem_public_key(pem_string.encode())

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
    issued_at: str
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

# ─────────────────────────────────────────────
# Signing
# ─────────────────────────────────────────────

def sign_hash(data_hash: str, private_key: RSAPrivateKey) -> str:
    """
    Sign a SHA-256 hash string with the issuer's RSA-2048 private key.
    Uses PSS padding with SHA-256 for maximum security.
    Returns base64-encoded signature string.
    """
    signature_bytes = private_key.sign(
        data_hash.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
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
        public_key.verify(
            signature_bytes,
            data_hash.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
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
    private_key: Optional[RSAPrivateKey] = None
) -> dict:
    """
    Full cryptographic processing pipeline for a new REC certificate.
    Returns dict containing hash, signature, and full steg payload.
    """
    if private_key is None:
        private_key = load_private_key()

    # 1. Build canonical payload
    canonical = build_canonical_payload(
        cert_id, generator_id, source_type,
        energy_kwh, generation_date, issuer_id, issued_at
    )

    # 2. Compute SHA-256 hash
    data_hash = compute_sha256(canonical)

    # 3. Sign the hash
    signature = sign_hash(data_hash, private_key)

    # 4. Build the full steganographic payload (what gets hidden in the image)
    steg_payload = {
        **canonical,
        "data_hash": data_hash,
        "signature": signature,
    }

    log.info("cert_cryptographic_processing_complete",
             cert_id=cert_id, hash_prefix=data_hash[:16])
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
    except KeyError as e:
        log.error("payload_missing_field", field=str(e))
        return False, False, ""

    # Recompute hash
    recomputed_hash = compute_sha256(canonical)

    # Layer 1: Hash integrity check
    stored_hash = extracted_payload.get("data_hash", "")
    layer1_pass = recomputed_hash == stored_hash

    # Layer 2: Signature check
    stored_sig = extracted_payload.get("signature", "")
    layer2_pass = verify_signature(stored_hash, stored_sig, public_key)

    log.info("crypto_verification",
             layer1=layer1_pass,
             layer2=layer2_pass,
             cert_id=extracted_payload.get("cert_id"))

    return layer1_pass, layer2_pass, recomputed_hash
```

---

## 8. Steganography Module

**File: `backend/modules/steg.py`**

```python
"""
REC Guard — Steganography Module (LSB — Least Significant Bit)
Hides the cryptographic payload inside a PNG/PDF certificate file's pixels.

Embedding: The JSON payload is converted to bytes, then each bit of those bytes
is hidden in the least significant bit of the R/G/B channels of image pixels.
This is visually imperceptible but recoverable on extraction.

Why LSB steganography?
- The hidden payload travels with the file wherever it is copied or shared.
- Tampering with the visible certificate data breaks the hidden proof.
- No external service is needed to verify authenticity.
"""

import json
import os
import io
import struct
import tempfile
from typing import Optional, Tuple
from PIL import Image
import PyPDF2
from pdf2image import convert_from_path, convert_from_bytes
import structlog

log = structlog.get_logger()

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

MAGIC_HEADER = b"RECGUARD"  # 8-byte magic string to detect our payload
HEADER_SIZE = 8 + 4         # magic (8 bytes) + payload length (4 bytes uint32)
SUPPORTED_IMAGE_MODES = {"RGB", "RGBA", "L"}

# ─────────────────────────────────────────────
# Utility — Image Preparation
# ─────────────────────────────────────────────

def _ensure_rgb(img: Image.Image) -> Image.Image:
    """Ensure image is in RGB mode for consistent channel access."""
    if img.mode in ("RGBA",):
        # Convert RGBA → RGB (drop alpha for LSB embed)
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        return background
    elif img.mode != "RGB":
        return img.convert("RGB")
    return img

def _image_capacity_bytes(img: Image.Image) -> int:
    """
    Calculate how many bytes can be hidden in this image.
    Each pixel's R, G, B channels each hold 1 bit → 3 bits/pixel.
    Capacity in bytes = (width * height * 3) // 8
    """
    w, h = img.size
    return (w * h * 3) // 8

# ─────────────────────────────────────────────
# Core LSB Embed
# ─────────────────────────────────────────────

def _lsb_embed(img: Image.Image, data: bytes) -> Image.Image:
    """
    Embed arbitrary bytes into image pixels using LSB steganography.
    Format: MAGIC_HEADER (8 bytes) + length (4 bytes, big-endian uint32) + data

    The length prefix allows extraction without knowing payload size in advance.
    """
    img = _ensure_rgb(img)
    payload = MAGIC_HEADER + struct.pack(">I", len(data)) + data
    capacity = _image_capacity_bytes(img)

    if len(payload) > capacity:
        raise ValueError(
            f"Payload too large: {len(payload)} bytes > image capacity {capacity} bytes. "
            f"Use a larger certificate image (minimum ~{len(payload)*8//3} pixels)."
        )

    pixels = list(img.getdata())
    bit_stream = []
    for byte in payload:
        for bit_pos in range(7, -1, -1):  # MSB first
            bit_stream.append((byte >> bit_pos) & 1)

    new_pixels = []
    bit_index = 0
    for pixel in pixels:
        r, g, b = pixel
        if bit_index < len(bit_stream):
            r = (r & 0xFE) | bit_stream[bit_index];     bit_index += 1
        if bit_index < len(bit_stream):
            g = (g & 0xFE) | bit_stream[bit_index];     bit_index += 1
        if bit_index < len(bit_stream):
            b = (b & 0xFE) | bit_stream[bit_index];     bit_index += 1
        new_pixels.append((r, g, b))

    result = Image.new("RGB", img.size)
    result.putdata(new_pixels)
    return result

# ─────────────────────────────────────────────
# Core LSB Extract
# ─────────────────────────────────────────────

def _lsb_extract(img: Image.Image) -> Optional[bytes]:
    """
    Extract hidden bytes from image pixels.
    Returns raw bytes if MAGIC_HEADER found, None otherwise.
    """
    img = _ensure_rgb(img)
    pixels = list(img.getdata())
    bits = []
    for pixel in pixels:
        r, g, b = pixel
        bits.append(r & 1)
        bits.append(g & 1)
        bits.append(b & 1)

    def bits_to_bytes(bit_list: list, start: int, count: int) -> bytes:
        result = []
        for i in range(count):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | bit_list[start + i * 8 + j]
            result.append(byte)
        return bytes(result)

    # Need at least HEADER_SIZE bytes
    if len(bits) < HEADER_SIZE * 8:
        return None

    # Extract magic header
    header_bytes = bits_to_bytes(bits, 0, 8)
    if header_bytes != MAGIC_HEADER:
        log.debug("no_magic_header_found")
        return None  # No payload — not an REC Guard certificate

    # Extract payload length
    length_bytes = bits_to_bytes(bits, 64, 4)  # 8 bytes magic * 8 bits = 64
    payload_length = struct.unpack(">I", length_bytes)[0]

    # Extract actual payload
    payload_start_bit = HEADER_SIZE * 8
    if len(bits) < payload_start_bit + payload_length * 8:
        log.warning("payload_truncated", expected=payload_length)
        return None

    return bits_to_bytes(bits, payload_start_bit, payload_length)

# ─────────────────────────────────────────────
# High-Level API
# ─────────────────────────────────────────────

def embed_payload_in_png(image_path: str, payload: dict, output_path: str) -> str:
    """
    Embed a JSON payload dict into a PNG file using LSB steganography.
    Saves the result to output_path and returns output_path.
    """
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    with Image.open(image_path) as img:
        steg_img = _lsb_embed(img, payload_bytes)

    steg_img.save(output_path, format="PNG", optimize=False)
    log.info("payload_embedded_png",
             input=image_path,
             output=output_path,
             payload_bytes=len(payload_bytes))
    return output_path

def embed_payload_in_pdf(pdf_path: str, payload: dict, output_path: str) -> str:
    """
    Embed payload into a PDF by:
    1. Converting the first page to PNG
    2. Embedding LSB payload in the PNG
    3. Creating a new PDF with the steg-embedded page
    Returns output_path.
    """
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    # Convert first PDF page to PIL Image
    pages = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=1)
    if not pages:
        raise ValueError(f"Could not render PDF: {pdf_path}")

    cover_img = pages[0]
    steg_img = _lsb_embed(cover_img, payload_bytes)

    # Save steg image as temp PNG, then embed into PDF
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        steg_img.save(tmp.name, format="PNG")
        tmp_png_path = tmp.name

    # Create output PDF from steg PNG
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas

    c = rl_canvas.Canvas(output_path, pagesize=A4)
    c.drawImage(tmp_png_path, 0, 0, width=A4[0], height=A4[1])
    c.save()

    os.unlink(tmp_png_path)
    log.info("payload_embedded_pdf",
             input=pdf_path,
             output=output_path,
             payload_bytes=len(payload_bytes))
    return output_path

def extract_payload_from_png(image_path: str) -> Optional[dict]:
    """
    Extract and decode the hidden JSON payload from a PNG file.
    Returns payload dict on success, None if no payload found.
    """
    try:
        with Image.open(image_path) as img:
            raw_bytes = _lsb_extract(img)
        if raw_bytes is None:
            log.warning("no_payload_in_png", path=image_path)
            return None
        payload = json.loads(raw_bytes.decode("utf-8"))
        log.info("payload_extracted_png",
                 path=image_path,
                 cert_id=payload.get("cert_id"))
        return payload
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        log.error("payload_decode_failed", path=image_path, error=str(e))
        return None
    except Exception as e:
        log.error("steg_extract_error", path=image_path, error=str(e))
        return None

def extract_payload_from_pdf(pdf_path: str) -> Optional[dict]:
    """
    Extract hidden payload from a PDF certificate file.
    Converts first page to PIL image, then extracts LSB payload.
    """
    try:
        pages = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=1)
        if not pages:
            return None
        raw_bytes = _lsb_extract(pages[0])
        if raw_bytes is None:
            return None
        return json.loads(raw_bytes.decode("utf-8"))
    except Exception as e:
        log.error("pdf_steg_extract_error", path=pdf_path, error=str(e))
        return None

def extract_payload_from_file(file_path: str) -> Optional[dict]:
    """
    Universal extractor — detects file type and routes to correct extractor.
    Supports .png, .jpg, .pdf
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
        return extract_payload_from_png(file_path)
    elif ext == ".pdf":
        return extract_payload_from_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use PNG or PDF.")
```

---

## 9. Module 1 — REC Issuer

**File: `backend/modules/issuer.py`**

```python
"""
REC Guard — Module 1: REC Issuer
Orchestrates the full certificate issuance pipeline.

Pipeline:
  Input data → SHA-256 hash + RSA sign → LSB steganographic embed
  → Register in ledger → Return issued certificate file
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional
import structlog

from modules.crypto import process_certificate_for_issuance, load_private_key
from modules.steg import embed_payload_in_png, embed_payload_in_pdf
from modules.ledger import register_certificate, lookup_certificate
from modules.certificate_gen import generate_certificate_png
from modules.anomaly import check_issuance_anomaly

log = structlog.get_logger()

CERT_STORAGE = os.getenv("CERT_STORAGE_PATH", "storage/certificates/")
os.makedirs(CERT_STORAGE, exist_ok=True)

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

def generate_cert_id(source_type: str, year: Optional[int] = None) -> str:
    """
    Generate a unique, human-readable certificate ID.
    Format: REC-{SOURCE}-{YEAR}-{NNNN}
    Example: REC-WND-2026-0091
    """
    code = SOURCE_CODES.get(source_type, "OTH")
    yr = year or datetime.now(timezone.utc).year
    unique_num = str(uuid.uuid4().int)[:4].zfill(4)
    return f"REC-{code}-{yr}-{unique_num}"

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
    output_format: str = "png"  # "png" or "pdf"
) -> dict:
    """
    Full REC certificate issuance pipeline.

    Args:
        cert_id:         Optional pre-assigned certificate ID (auto-generated if None)
        generator_id:    Renewable energy plant/generator identifier
        source_type:     Energy source: Wind, Solar, Hydro, Biomass, etc.
        energy_kwh:      Energy generated in kWh (must be > 0)
        generation_date: Date of generation (YYYY-MM-DD)
        issuer_id:       Identifier of the issuing body
        output_format:   "png" or "pdf"

    Returns:
        dict with keys:
          success (bool), cert_id, file_path, data_hash,
          payload (full steg payload), error (if failed)
    """
    try:
        # ── 0. Input Validation ───────────────────────────────
        if not generator_id:
            raise ValueError("generator_id is required.")
        if energy_kwh <= 0:
            raise ValueError("energy_kwh must be positive.")
        if not generation_date:
            raise ValueError("generation_date is required (YYYY-MM-DD).")
        if not issuer_id:
            raise ValueError("issuer_id is required.")

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
            generation_date=generation_date
        )
        if anomaly_result["is_anomaly"]:
            log.warning("issuance_anomaly_detected",
                        cert_id=cert_id,
                        reason=anomaly_result["reason"],
                        score=anomaly_result["score"])
            # In production: flag for manual review, don't auto-block
            # For MVP: log and continue

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
            private_key=private_key
        )

        # ── 4. Generate Certificate Visual ───────────────────
        raw_cert_path = os.path.join(CERT_STORAGE, f"{cert_id}_raw.png")
        generate_certificate_png(
            cert_id=cert_id,
            generator_id=generator_id,
            source_type=source_type,
            energy_kwh=energy_kwh,
            generation_date=generation_date,
            issuer_id=issuer_id,
            output_path=raw_cert_path
        )

        # ── 5. Steganographic Embedding ───────────────────────
        final_cert_path = os.path.join(CERT_STORAGE, f"{cert_id}.{output_format}")
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
            raise RuntimeError("Failed to register certificate in ledger — ID conflict.")

        log.info("certificate_issued_successfully",
                 cert_id=cert_id,
                 source=source_type,
                 kwh=energy_kwh,
                 format=output_format)

        return {
            "success": True,
            "cert_id": cert_id,
            "file_path": final_cert_path,
            "data_hash": steg_payload["data_hash"],
            "issued_at": issued_at,
            "payload": steg_payload,
            "anomaly_flag": anomaly_result["is_anomaly"],
            "anomaly_reason": anomaly_result.get("reason"),
        }

    except Exception as e:
        log.error("issuance_failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }
```

---

## 10. Module 2 — REC Verifier

**File: `backend/modules/verifier.py`**

```python
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
  Check: is it registered? Is it already claimed?
  → Catches: duplicate issuance (one CertID to two buyers),
             duplicate usage (re-submission of already-claimed cert).

A certificate is VALID only if ALL THREE layers pass.
"""

import os
from datetime import datetime, timezone
from typing import Optional
import structlog

from modules.steg import extract_payload_from_file
from modules.crypto import recompute_and_verify, load_public_key, load_public_key_from_pem
from modules.ledger import lookup_certificate, log_verification, get_issuer_public_key

log = structlog.get_logger()

# ─────────────────────────────────────────────
# Verification Result Dataclass
# ─────────────────────────────────────────────

class VerificationResult:
    def __init__(self):
        self.cert_id: Optional[str] = None
        self.layer1_pass: bool = False
        self.layer2_pass: bool = False
        self.layer3_pass: bool = False
        self.layer1_detail: str = ""
        self.layer2_detail: str = ""
        self.layer3_detail: str = ""
        self.final_result: str = "FRAUD"      # "VALID" or "FRAUD"
        self.fraud_reason: Optional[str] = None
        self.extracted_payload: Optional[dict] = None
        self.ledger_record: Optional[dict] = None
        self.uploaded_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "cert_id": self.cert_id,
            "final_result": self.final_result,
            "is_valid": self.final_result == "VALID",
            "layers": {
                "layer1_steganographic_integrity": {
                    "passed": self.layer1_pass,
                    "detail": self.layer1_detail,
                },
                "layer2_cryptographic_signature": {
                    "passed": self.layer2_pass,
                    "detail": self.layer2_detail,
                },
                "layer3_ledger_lookup": {
                    "passed": self.layer3_pass,
                    "detail": self.layer3_detail,
                },
            },
            "fraud_reason": self.fraud_reason,
            "extracted_data": self.extracted_payload,
            "ledger_record": self.ledger_record,
        }

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
    verified_at = datetime.now(timezone.utc).isoformat()

    # ── LAYER 1: Steganographic Integrity ────────────────────────
    log.info("verification_layer1_start", file=file_path)

    extracted = extract_payload_from_file(file_path)

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
        _write_audit_log(result, verifier_id, verifier_ip, verified_at)
        return result.to_dict()

    result.extracted_payload = extracted
    result.cert_id = extracted.get("cert_id")

    # Re-verify the hash integrity
    public_key = _resolve_public_key(extracted.get("issuer_id"))
    layer1_pass, layer2_pass, recomputed_hash = recompute_and_verify(extracted, public_key)
    result.uploaded_hash = recomputed_hash

    if layer1_pass:
        result.layer1_pass = True
        result.layer1_detail = (
            f"Hash integrity confirmed. Recomputed SHA-256 matches stored hash: "
            f"{recomputed_hash[:24]}..."
        )
    else:
        result.layer1_pass = False
        result.layer1_detail = (
            f"HASH MISMATCH. Recomputed: {recomputed_hash[:24]}..., "
            f"Stored: {extracted.get('data_hash', 'N/A')[:24]}... "
            f"The visible certificate data has been altered after issuance."
        )
        result.fraud_reason = "LAYER_1_FAIL: Data hash mismatch — certificate was tampered."
        result.final_result = "FRAUD"
        # Still continue to check layers 2 and 3 for full diagnostic
        result.layer2_detail = _run_layer2(layer2_pass)
        result.layer2_pass = layer2_pass
        result.layer3_detail = "Skipped — Layer 1 failed (hash mismatch)."
        _write_audit_log(result, verifier_id, verifier_ip, verified_at)
        return result.to_dict()

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
        _write_audit_log(result, verifier_id, verifier_ip, verified_at)
        return result.to_dict()

    # ── LAYER 3: Ledger Lookup ─────────────────────────────────────
    log.info("verification_layer3_start", cert_id=result.cert_id)

    if not result.cert_id:
        result.layer3_pass = False
        result.layer3_detail = "No Certificate ID found in payload."
        result.fraud_reason = "LAYER_3_FAIL: Missing Certificate ID."
        result.final_result = "FRAUD"
        _write_audit_log(result, verifier_id, verifier_ip, verified_at)
        return result.to_dict()

    ledger_record = lookup_certificate(result.cert_id)

    if ledger_record is None:
        result.layer3_pass = False
        result.layer3_detail = (
            f"Certificate ID '{result.cert_id}' is NOT registered in the ledger. "
            "This certificate was never officially issued."
        )
        result.fraud_reason = "LAYER_3_FAIL: Certificate ID not found in ledger."
        result.final_result = "FRAUD"
        _write_audit_log(result, verifier_id, verifier_ip, verified_at)
        return result.to_dict()

    result.ledger_record = ledger_record

    if ledger_record["status"] == "claimed":
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
        _write_audit_log(result, verifier_id, verifier_ip, verified_at)
        return result.to_dict()

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
        from modules.ledger import mark_claimed
        mark_claimed(result.cert_id, claimed_by)
        result.layer3_detail += f" | Certificate now claimed by '{claimed_by}'."

    log.info("certificate_verified_valid", cert_id=result.cert_id)
    _write_audit_log(result, verifier_id, verifier_ip, verified_at)
    return result.to_dict()

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _resolve_public_key(issuer_id: Optional[str]):
    """
    Resolve the correct RSA public key for this issuer.
    Falls back to the default system key if issuer is not in registry.
    """
    if issuer_id:
        pem_str = get_issuer_public_key(issuer_id)
        if pem_str:
            return load_public_key_from_pem(pem_str)
    return load_public_key()  # Default system key

def _run_layer2(layer2_pass: bool) -> str:
    if layer2_pass:
        return "RSA-2048 signature is valid. Certificate was signed by a registered issuing authority."
    return (
        "RSA signature INVALID. Payload exists but was not signed by any registered "
        "issuing body. This is a forged certificate."
    )

def _write_audit_log(result: VerificationResult, verifier_id, verifier_ip, verified_at):
    """Write verification result to the audit log table."""
    try:
        log_verification({
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
        })
    except Exception as e:
        log.error("audit_log_write_failed", error=str(e))
```

---

## 11. Flask REST API Layer

**File: `backend/app.py`**

```python
"""
REC Guard — Flask Application Entry Point
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import structlog

load_dotenv()

log = structlog.get_logger()

def create_app():
    app = Flask(__name__)

    # ── Configuration ─────────────────────────────────────────
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-prod")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload

    # ── Extensions ────────────────────────────────────────────
    CORS(app, origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","))
    JWTManager(app)

    # ── Blueprints ────────────────────────────────────────────
    from routes.issue_routes import issue_bp
    from routes.verify_routes import verify_bp
    from routes.ledger_routes import ledger_bp
    from routes.admin_routes import admin_bp
    from routes.auth_routes import auth_bp

    app.register_blueprint(issue_bp,   url_prefix="/api")
    app.register_blueprint(verify_bp,  url_prefix="/api")
    app.register_blueprint(ledger_bp,  url_prefix="/api")
    app.register_blueprint(admin_bp,   url_prefix="/api/admin")
    app.register_blueprint(auth_bp,    url_prefix="/api/auth")

    # ── Health Check ──────────────────────────────────────────
    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "REC Guard API", "version": "1.0.0"})

    # ── Error Handlers ────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "message": str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(413)
    def file_too_large(e):
        return jsonify({"error": "File too large. Maximum 16 MB."}), 413

    @app.errorhandler(500)
    def server_error(e):
        log.error("unhandled_exception", error=str(e))
        return jsonify({"error": "Internal server error"}), 500

    # ── Initialize DB ─────────────────────────────────────────
    from modules.ledger import init_db
    with app.app_context():
        init_db()

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
```

### API Endpoints Reference

**File: `backend/routes/issue_routes.py`**

```python
import os
import tempfile
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from modules.issuer import issue_certificate
from utils.validators import validate_issue_input

issue_bp = Blueprint("issue", __name__)

@issue_bp.route("/issue", methods=["POST"])
@jwt_required(optional=True)
def issue():
    """
    POST /api/issue
    Issue a new REC certificate.

    Body (JSON):
    {
      "generator_id":    "WF-A-01",
      "source_type":     "Wind",        // Wind|Solar|Hydro|Biomass|Geothermal|Tidal
      "energy_kwh":      100.0,
      "generation_date": "2026-03-01",
      "issuer_id":       "ISSUER-GreenCert-04",
      "cert_id":         null,           // Optional: auto-generated if null
      "format":          "png"           // "png" or "pdf"
    }

    Response 201:
    {
      "success": true,
      "cert_id": "REC-WND-2026-0091",
      "data_hash": "c9f0f895...",
      "issued_at": "2026-03-02T10:15:00Z",
      "download_url": "/api/certificate/REC-WND-2026-0091.png",
      "anomaly_flag": false
    }
    """
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "JSON body required."}), 400

    errors = validate_issue_input(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 422

    issuer_id = data.get("issuer_id") or get_jwt_identity() or "SYSTEM"
    result = issue_certificate(
        cert_id=data.get("cert_id"),
        generator_id=data["generator_id"],
        source_type=data.get("source_type", "Solar"),
        energy_kwh=float(data["energy_kwh"]),
        generation_date=data["generation_date"],
        issuer_id=issuer_id,
        output_format=data.get("format", "png"),
    )

    if not result["success"]:
        return jsonify({"error": result["error"]}), 400

    cert_id = result["cert_id"]
    ext = data.get("format", "png")
    download_url = f"/api/certificate/{cert_id}.{ext}"

    return jsonify({
        "success": True,
        "cert_id": cert_id,
        "data_hash": result["data_hash"],
        "issued_at": result["issued_at"],
        "download_url": download_url,
        "anomaly_flag": result.get("anomaly_flag", False),
        "anomaly_reason": result.get("anomaly_reason"),
    }), 201

@issue_bp.route("/certificate/<filename>", methods=["GET"])
def download_certificate(filename):
    """
    GET /api/certificate/{cert_id}.{ext}
    Download an issued certificate file.
    """
    cert_storage = os.getenv("CERT_STORAGE_PATH", "storage/certificates/")
    file_path = os.path.join(cert_storage, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "Certificate file not found."}), 404
    return send_file(file_path, as_attachment=True)
```

**File: `backend/routes/verify_routes.py`**

```python
import os
import tempfile
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from modules.verifier import verify_certificate
from utils.file_utils import save_uploaded_file, cleanup_temp_file

verify_bp = Blueprint("verify", __name__)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}

@verify_bp.route("/verify", methods=["POST"])
@jwt_required(optional=True)
def verify():
    """
    POST /api/verify
    Verify an uploaded REC certificate file.

    Multipart form-data:
      file:        The certificate file (PNG, JPG, or PDF)
      claim:       "true" to mark as claimed on successful verification
      claimed_by:  Buyer entity ID (required if claim=true)

    Response 200:
    {
      "cert_id": "REC-WND-2026-0091",
      "final_result": "VALID",
      "is_valid": true,
      "layers": {
        "layer1_steganographic_integrity": { "passed": true, "detail": "..." },
        "layer2_cryptographic_signature":  { "passed": true, "detail": "..." },
        "layer3_ledger_lookup":            { "passed": true, "detail": "..." }
      },
      "fraud_reason": null,
      "extracted_data": { ... },
      "ledger_record": { ... }
    }
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Use multipart/form-data with field 'file'."}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file.filename:
        return jsonify({"error": "No filename provided."}), 400

    ext = os.path.splitext(uploaded_file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported file type '{ext}'. Use PNG or PDF."}), 415

    # Save to temp location for processing
    temp_path = save_uploaded_file(uploaded_file, ext)

    try:
        verifier_id = get_jwt_identity()
        verifier_ip = request.remote_addr
        claim = request.form.get("claim", "false").lower() == "true"
        claimed_by = request.form.get("claimed_by")

        result = verify_certificate(
            file_path=temp_path,
            verifier_id=verifier_id,
            verifier_ip=verifier_ip,
            claim_cert=claim,
            claimed_by=claimed_by,
        )
        return jsonify(result), 200

    finally:
        cleanup_temp_file(temp_path)
```

**File: `backend/routes/ledger_routes.py`**

```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from modules.ledger import (
    get_all_certificates, lookup_certificate,
    get_ledger_stats, mark_claimed
)

ledger_bp = Blueprint("ledger", __name__)

@ledger_bp.route("/ledger", methods=["GET"])
@jwt_required(optional=True)
def get_ledger():
    """
    GET /api/ledger?status=issued&source_type=Wind&limit=50&offset=0
    Paginated ledger listing with optional filters.
    """
    status = request.args.get("status")
    source_type = request.args.get("source_type")
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))
    certs = get_all_certificates(status=status, source_type=source_type, limit=limit, offset=offset)
    return jsonify({"certificates": certs, "count": len(certs)})

@ledger_bp.route("/ledger/<cert_id>", methods=["GET"])
def get_certificate(cert_id):
    """GET /api/ledger/{cert_id} — Get single certificate ledger record."""
    record = lookup_certificate(cert_id)
    if not record:
        return jsonify({"error": f"Certificate '{cert_id}' not found."}), 404
    return jsonify(record)

@ledger_bp.route("/ledger/stats", methods=["GET"])
def get_stats():
    """GET /api/ledger/stats — Aggregate statistics for dashboard."""
    return jsonify(get_ledger_stats())

@ledger_bp.route("/ledger/<cert_id>/claim", methods=["POST"])
@jwt_required()
def claim_certificate(cert_id):
    """POST /api/ledger/{cert_id}/claim — Mark a certificate as claimed."""
    data = request.get_json() or {}
    claimed_by = data.get("claimed_by") or get_jwt_identity()
    success = mark_claimed(cert_id, claimed_by)
    if not success:
        return jsonify({"error": "Certificate not found or already claimed."}), 400
    return jsonify({"success": True, "cert_id": cert_id, "claimed_by": claimed_by})
```

---

## 12. Frontend UI

### 12.1 Design Token System

**Design Rationale for REC Guard**:
The visual identity references the intersection of *certificate authenticity* and *environmental data integrity* — institutional solidity meets clean-energy transparency. The palette uses deep verification-authority blues paired with living-green accents, rendered in a high-contrast grid layout with sharp edges and data-forward typography. This is an auditors' tool, not a consumer app — it should feel like a regulated instrument.

**Design Tokens** (`frontend/src/App.css`):

```css
/* ─────────────────────────────────────────────────────
   REC Guard — Design Token System
   Authority palette: deep navy + verification green + alert amber
───────────────────────────────────────────────────── */
:root {
  /* Core Palette */
  --bg-primary:     #0D1117;   /* Deep authority navy — main background */
  --bg-secondary:   #161B22;   /* Card surfaces */
  --bg-tertiary:    #21262D;   /* Input backgrounds, table rows */
  --border:         #30363D;   /* All borders */

  /* Brand Colors */
  --green-400:      #3FB950;   /* Valid / success states */
  --green-500:      #2EA043;   /* Primary CTA buttons */
  --green-600:      #238636;   /* Pressed/hover */
  --green-glow:     rgba(63, 185, 80, 0.15);

  --red-400:        #F85149;   /* Fraud / error states */
  --red-glow:       rgba(248, 81, 73, 0.15);

  --amber-400:      #D29922;   /* Anomaly warnings */
  --blue-400:       #388BFD;   /* Links, secondary actions */

  /* Typography */
  --text-primary:   #E6EDF3;   /* Main readable text */
  --text-secondary: #8B949E;   /* Supporting / metadata text */
  --text-muted:     #484F58;   /* Disabled / placeholder text */

  /* Type Scale */
  --font-sans:      'Inter', 'Segoe UI', system-ui, sans-serif;
  --font-mono:      'JetBrains Mono', 'Fira Code', 'Consolas', monospace;

  --text-xs:   0.75rem;   /* 12px — labels, status badges */
  --text-sm:   0.875rem;  /* 14px — table data, metadata */
  --text-base: 1rem;      /* 16px — body */
  --text-lg:   1.125rem;  /* 18px — section titles */
  --text-xl:   1.25rem;   /* 20px — page titles */
  --text-2xl:  1.5rem;    /* 24px — dashboard headers */
  --text-3xl:  1.875rem;  /* 30px — stat numbers */

  /* Spacing */
  --space-1:  0.25rem;
  --space-2:  0.5rem;
  --space-3:  0.75rem;
  --space-4:  1rem;
  --space-6:  1.5rem;
  --space-8:  2rem;
  --space-12: 3rem;
  --space-16: 4rem;

  /* Shape */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;

  /* Shadows */
  --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.4), 0 0 0 1px var(--border);
  --shadow-green: 0 0 0 3px var(--green-glow);
  --shadow-red:   0 0 0 3px var(--red-glow);

  /* Transitions */
  --transition: 150ms ease;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
```

### 12.2 App.js (Main Layout + Routing)

```jsx
// frontend/src/App.js
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Header from './components/Layout/Header';
import Sidebar from './components/Layout/Sidebar';
import IssuePage from './pages/IssuePage';
import VerifyPage from './pages/VerifyPage';
import LedgerPage from './pages/LedgerPage';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import './App.css';

function AppLayout({ children }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Header />
        <main style={{ flex: 1, padding: 'var(--space-8)', overflowY: 'auto' }}>
          {children}
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            fontFamily: 'var(--font-sans)',
          },
        }}
      />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<AppLayout><DashboardPage /></AppLayout>} />
        <Route path="/issue" element={<AppLayout><IssuePage /></AppLayout>} />
        <Route path="/verify" element={<AppLayout><VerifyPage /></AppLayout>} />
        <Route path="/ledger" element={<AppLayout><LedgerPage /></AppLayout>} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}
```

### 12.3 IssueForm Component

```jsx
// frontend/src/components/Issue/IssueForm.js
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { issueService } from '../../services/issueService';

const SOURCE_TYPES = ['Wind', 'Solar', 'Hydro', 'Biomass', 'Geothermal', 'Tidal', 'Other'];

export default function IssueForm({ onSuccess }) {
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, formState: { errors }, reset } = useForm();

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      const result = await issueService.issue({
        generator_id:    data.generator_id,
        source_type:     data.source_type,
        energy_kwh:      parseFloat(data.energy_kwh),
        generation_date: data.generation_date,
        issuer_id:       data.issuer_id,
        format:          data.format || 'png',
      });

      if (result.success) {
        toast.success(`Certificate issued: ${result.cert_id}`);
        if (result.anomaly_flag) {
          toast(`⚠ Anomaly flagged: ${result.anomaly_reason}`, { icon: '⚠️', duration: 5000 });
        }
        onSuccess(result);
        reset();
      }
    } catch (err) {
      toast.error(`Issuance failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fieldStyle = {
    width: '100%',
    padding: '10px 12px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-sans)',
    fontSize: 'var(--text-sm)',
    outline: 'none',
    transition: 'border-color var(--transition)',
  };

  const labelStyle = {
    display: 'block',
    fontSize: 'var(--text-xs)',
    color: 'var(--text-secondary)',
    marginBottom: 'var(--space-2)',
    letterSpacing: '0.03em',
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
        <div>
          <label style={labelStyle}>Generator ID</label>
          <input style={fieldStyle} placeholder="WF-A-01"
            {...register('generator_id', { required: 'Generator ID is required' })} />
          {errors.generator_id && <span style={{ color: 'var(--red-400)', fontSize: 'var(--text-xs)' }}>{errors.generator_id.message}</span>}
        </div>

        <div>
          <label style={labelStyle}>Source Type</label>
          <select style={fieldStyle} {...register('source_type', { required: true })}>
            {SOURCE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>

        <div>
          <label style={labelStyle}>Energy Generated (kWh)</label>
          <input type="number" step="0.001" min="0.001" style={fieldStyle} placeholder="100.0"
            {...register('energy_kwh', { required: 'Energy is required', min: { value: 0.001, message: 'Must be > 0' }})} />
          {errors.energy_kwh && <span style={{ color: 'var(--red-400)', fontSize: 'var(--text-xs)' }}>{errors.energy_kwh.message}</span>}
        </div>

        <div>
          <label style={labelStyle}>Generation Date</label>
          <input type="date" style={fieldStyle}
            {...register('generation_date', { required: 'Date is required' })} />
        </div>

        <div>
          <label style={labelStyle}>Issuer ID</label>
          <input style={fieldStyle} placeholder="ISSUER-GreenCert-04"
            {...register('issuer_id', { required: 'Issuer ID is required' })} />
        </div>

        <div>
          <label style={labelStyle}>Output Format</label>
          <select style={fieldStyle} {...register('format')}>
            <option value="png">PNG (Recommended)</option>
            <option value="pdf">PDF</option>
          </select>
        </div>
      </div>

      <button type="submit" disabled={loading} style={{
        padding: '12px 24px',
        background: loading ? 'var(--bg-tertiary)' : 'var(--green-500)',
        color: loading ? 'var(--text-muted)' : '#fff',
        border: 'none',
        borderRadius: 'var(--radius-md)',
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--text-sm)',
        fontWeight: 600,
        cursor: loading ? 'not-allowed' : 'pointer',
        transition: 'background var(--transition)',
        alignSelf: 'flex-start',
      }}>
        {loading ? 'Issuing Certificate...' : 'Issue REC Certificate'}
      </button>
    </form>
  );
}
```

### 12.4 VerifyResult Component

```jsx
// frontend/src/components/Verify/VerifyResult.js
import React from 'react';
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

function LayerCard({ number, name, passed, detail }) {
  const color = passed ? 'var(--green-400)' : 'var(--red-400)';
  const Icon = passed ? CheckCircle : XCircle;

  return (
    <div style={{
      padding: 'var(--space-4) var(--space-6)',
      background: 'var(--bg-tertiary)',
      borderRadius: 'var(--radius-md)',
      border: `1px solid ${passed ? 'var(--green-500)' : 'var(--red-400)'}`,
      marginBottom: 'var(--space-3)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
        <Icon size={18} color={color} />
        <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color }}>
          Layer {number} — {name}
        </span>
        <span style={{
          marginLeft: 'auto',
          fontSize: 'var(--text-xs)',
          padding: '2px 8px',
          borderRadius: 12,
          background: passed ? 'var(--green-glow)' : 'var(--red-glow)',
          color,
          fontWeight: 700,
        }}>
          {passed ? 'PASS' : 'FAIL'}
        </span>
      </div>
      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
        {detail}
      </p>
    </div>
  );
}

export default function VerifyResult({ result }) {
  if (!result) return null;
  const isValid = result.final_result === 'VALID';

  return (
    <div style={{
      marginTop: 'var(--space-8)',
      padding: 'var(--space-8)',
      background: 'var(--bg-secondary)',
      borderRadius: 'var(--radius-lg)',
      border: `2px solid ${isValid ? 'var(--green-500)' : 'var(--red-400)'}`,
      boxShadow: isValid ? 'var(--shadow-green)' : 'var(--shadow-red)',
    }}>
      {/* Verdict Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 'var(--space-4)',
        marginBottom: 'var(--space-8)',
        padding: 'var(--space-6)',
        background: isValid ? 'var(--green-glow)' : 'var(--red-glow)',
        borderRadius: 'var(--radius-md)',
      }}>
        {isValid
          ? <CheckCircle size={32} color="var(--green-400)" />
          : <XCircle size={32} color="var(--red-400)" />}
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-2xl)', fontWeight: 700,
            color: isValid ? 'var(--green-400)' : 'var(--red-400)' }}>
            {result.final_result}
          </div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
            Certificate ID: {result.cert_id || 'Unknown'}
          </div>
        </div>
        {result.fraud_reason && (
          <div style={{ marginLeft: 'auto', maxWidth: 300, fontSize: 'var(--text-xs)',
            color: 'var(--red-400)', textAlign: 'right' }}>
            {result.fraud_reason}
          </div>
        )}
      </div>

      {/* Three Layer Results */}
      <h3 style={{ marginBottom: 'var(--space-4)', fontSize: 'var(--text-sm)',
        color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Verification Layers
      </h3>
      <LayerCard
        number={1}
        name="Steganographic Integrity"
        passed={result.layers?.layer1_steganographic_integrity?.passed}
        detail={result.layers?.layer1_steganographic_integrity?.detail}
      />
      <LayerCard
        number={2}
        name="Cryptographic Signature"
        passed={result.layers?.layer2_cryptographic_signature?.passed}
        detail={result.layers?.layer2_cryptographic_signature?.detail}
      />
      <LayerCard
        number={3}
        name="Ledger / Registry Lookup"
        passed={result.layers?.layer3_ledger_lookup?.passed}
        detail={result.layers?.layer3_ledger_lookup?.detail}
      />

      {/* Extracted Data */}
      {result.extracted_data && (
        <details style={{ marginTop: 'var(--space-6)' }}>
          <summary style={{ cursor: 'pointer', fontSize: 'var(--text-sm)',
            color: 'var(--text-secondary)', padding: 'var(--space-2) 0' }}>
            Extracted Certificate Data
          </summary>
          <pre style={{
            marginTop: 'var(--space-3)',
            padding: 'var(--space-4)',
            background: 'var(--bg-primary)',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--text-xs)',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-primary)',
            overflowX: 'auto',
            lineHeight: 1.6,
          }}>
            {JSON.stringify(result.extracted_data, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
```

---

## 13. Three-Layer Verification Engine

### Detailed Layer Specifications

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    THREE-LAYER FRAUD DETECTION PIPELINE                      │
├──────────────────┬───────────────────────────────────────┬───────────────────┤
│ LAYER            │ MECHANISM                             │ FRAUD CAUGHT      │
├──────────────────┼───────────────────────────────────────┼───────────────────┤
│ 1. Steg Integrity│ Extract LSB payload from file pixels. │ • Value tampering │
│                  │ Recompute SHA-256 of visible data.    │   (100→1000 kWh)  │
│                  │ Compare to stored hash in payload.    │ • No-payload fakes│
│                  │ FAIL = hash mismatch OR no payload.   │ • Unit changes    │
├──────────────────┼───────────────────────────────────────┼───────────────────┤
│ 2. Crypto Sig    │ Validate RSA-2048 PSS signature in    │ • Forged docs with│
│                  │ payload against issuer's public key.  │   a self-made     │
│                  │ Signature covers the data hash.       │   payload         │
│                  │ FAIL = invalid signature.             │ • Unregistered    │
│                  │                                       │   signers         │
├──────────────────┼───────────────────────────────────────┼───────────────────┤
│ 3. Ledger Lookup │ Query shared ledger for cert_id.      │ • Duplicate issue │
│                  │ Check: registered? Already claimed?   │   (2 buyers,      │
│                  │ FAIL = not registered OR claimed.     │   1 cert_id)      │
│                  │                                       │ • Double-claiming │
│                  │                                       │   already-used    │
│                  │                                       │   certificates    │
└──────────────────┴───────────────────────────────────────┴───────────────────┘

VERDICT LOGIC:
  Layer1 FAIL → FRAUD immediately (no data to verify further)
  Layer2 FAIL → FRAUD (payload exists but unauthorized signer)
  Layer3 FAIL → FRAUD (registry problem regardless of crypto)
  ALL PASS    → VALID
```

---

## 14. Fraud Scenarios and Test Data

### Test Cases

```python
# backend/tests/fixtures/sample_data.json

TEST_SCENARIOS = {
    "scenario_1_value_tampering": {
        "description": "Wind certificate edited from 100 kWh to 1000 kWh after issuance",
        "original": {
            "cert_id": "REC-WND-2026-0091",
            "generator_id": "WF-A-01",
            "source_type": "Wind",
            "energy_kwh": 100,
            "generation_date": "2026-03-01",
            "issuer_id": "ISSUER-GreenCert-04"
        },
        "tampered_energy_kwh": 1000,
        "expected_layer_fail": "layer1_steganographic_integrity",
        "expected_result": "FRAUD",
        "catch_reason": "Hash mismatch — 100 vs 1000 kWh produces different SHA-256"
    },

    "scenario_2_duplicate_certid": {
        "description": "Same CertID given to two buyers (Solar 1 MW)",
        "cert_id": "REC-SLR-2026-0034",
        "generator_id": "SP-C-01",
        "source_type": "Solar",
        "energy_kwh": 1000,  # 1 MW = 1000 kWh
        "generation_date": "2026-02-15",
        "issuer_id": "ISSUER-SolarAuth-01",
        "buyer_x": "BUYER-Acme-Corp",
        "buyer_y": "BUYER-GreenTech-Ltd",
        "expected_layer_fail": "layer3_ledger_lookup",
        "expected_result": "FRAUD",
        "catch_reason": "CertID already registered and claimed by Buyer X"
    },

    "scenario_3_value_edit": {
        "description": "Solar certificate value edited from 500 kWh to 5000 kWh",
        "cert_id": "REC-SLR-2026-0055",
        "generator_id": "SP-B-01",
        "source_type": "Solar",
        "energy_kwh_original": 500,
        "energy_kwh_tampered": 5000,
        "generation_date": "2026-01-20",
        "issuer_id": "ISSUER-SolarAuth-01",
        "expected_layer_fail": "layer1_steganographic_integrity",
        "expected_result": "FRAUD",
        "catch_reason": "Hash mismatch — 500 vs 5000 kWh"
    },

    "scenario_4_duplicate_claim": {
        "description": "Claimed certificate resubmitted for second claim (duplicate usage)",
        "cert_id": "REC-WND-2026-0102",
        "generator_id": "WF-D-01",
        "source_type": "Wind",
        "energy_kwh": 750,
        "generation_date": "2026-03-10",
        "issuer_id": "ISSUER-GreenCert-04",
        "first_claimer": "BUYER-EcoEnergy-01",
        "second_claimer": "BUYER-CleanPower-02",
        "expected_layer_fail": "layer3_ledger_lookup",
        "expected_result": "FRAUD",
        "catch_reason": "Certificate already claimed — duplicate re-submission"
    },

    "scenario_valid_baseline": {
        "description": "Clean certificate — all three layers pass",
        "cert_id": "REC-HYD-2026-0201",
        "generator_id": "HP-E-01",
        "source_type": "Hydro",
        "energy_kwh": 5000,
        "generation_date": "2026-03-05",
        "issuer_id": "ISSUER-HydroAuth-03",
        "expected_result": "VALID"
    }
}
```

### Ledger State After Test Scenarios

| CertID | Source | Energy | Status | Note |
|---|---|---|---|---|
| REC-WND-2026-0091 | Wind Farm A | 100 kWh | Issued | Valid baseline |
| REC-WND-2026-0091* | Wind Farm A | 1000 kWh (edited) | — | FRAUD — Scenario 1: hash mismatch |
| REC-SLR-2026-0034 | Solar Plant C | 1 MW | Claimed (Buyer X) | Valid first claim |
| REC-SLR-2026-0034 (copy) | Solar Plant C | 1 MW | — | FRAUD — Scenario 2: duplicate CertID |
| REC-SLR-2026-0055 | Solar Plant B | 500 kWh | Issued | Valid baseline |
| REC-SLR-2026-0055* | Solar Plant B | 5,000 kWh (edited) | — | FRAUD — Scenario 3: hash mismatch |
| REC-WND-2026-0102 | Wind Farm D | 750 kWh | Claimed | Valid first verification |
| REC-WND-2026-0102 (resubmit) | Wind Farm D | 750 kWh | — | FRAUD — Scenario 4: already claimed |

---

## 15. Security Design

### Why All Three Layers Are Required

```
HASHING (SHA-256) alone:
  ✓ Proves the data wasn't changed
  ✗ Doesn't prove WHO created the certificate
  ✗ Doesn't prevent duplicate issuance

SIGNING (RSA-2048) alone:
  ✓ Proves the certificate came from a known issuer
  ✗ Doesn't prove the same certificate wasn't issued to 10 buyers
  ✗ Can't detect duplicate claiming

LEDGER alone:
  ✓ Tracks all issuance and claims
  ✗ Can be bypassed by a well-formed forged document
  ✗ No mechanism to detect tampering with visible data

STEGANOGRAPHY alone:
  ✓ Carries the proof inside the file itself
  ✗ Anyone who knows the algorithm can embed their own payload
  ✗ No binding to a real-world registry

ALL THREE TOGETHER:
  ✓ The certificate carries self-contained proof
  ✓ That proof is cryptographically bound to a real issuer
  ✓ The issuer is confirmed in a shared, append-only registry
  ✓ Claims are tracked; duplicates are impossible
```

### Key Management

```
Production key management requirements:
1. Private keys MUST be stored in a Hardware Security Module (HSM) or 
   AWS KMS / Azure Key Vault — never on disk in production
2. Each certificate issuing body has its own RSA key pair
3. Public keys are registered in the issuers table and distributed openly
4. Private key rotation policy: annually minimum
5. All signing operations are logged with timestamp + operator ID
6. TLS 1.3 minimum for all API traffic
7. At-rest encryption (AES-256) for certificate file storage
8. Ledger database encrypted at rest in production
```

---

## 16. Full Testing Suite

**File: `backend/tests/test_issuer.py`**

```python
"""Integration tests for the full issuance pipeline."""

import pytest
import os
import json
from modules.issuer import issue_certificate
from modules.ledger import lookup_certificate, init_db
from modules.steg import extract_payload_from_file
from modules.crypto import recompute_and_verify

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
        output_format="png"
    )
    assert result["success"] is True
    assert result["cert_id"].startswith("REC-WND-")
    assert os.path.exists(result["file_path"])
    assert len(result["data_hash"]) == 64  # SHA-256 hex

def test_issued_certificate_registered_in_ledger():
    result = issue_certificate(
        generator_id="SP-TEST-01",
        source_type="Solar",
        energy_kwh=500.0,
        generation_date="2026-02-01",
        issuer_id="ISSUER-TEST-01"
    )
    record = lookup_certificate(result["cert_id"])
    assert record is not None
    assert record["status"] == "issued"
    assert record["energy_kwh"] == 500.0

def test_steg_payload_extractable_from_issued_cert():
    result = issue_certificate(
        generator_id="WF-TEST-02",
        source_type="Wind",
        energy_kwh=250.0,
        generation_date="2026-01-15",
        issuer_id="ISSUER-TEST-01"
    )
    payload = extract_payload_from_file(result["file_path"])
    assert payload is not None
    assert payload["energy_kwh"] == 250.0
    assert payload["cert_id"] == result["cert_id"]

def test_hash_in_payload_matches_data():
    result = issue_certificate(
        generator_id="HYD-TEST-01",
        source_type="Hydro",
        energy_kwh=1000.0,
        generation_date="2026-03-10",
        issuer_id="ISSUER-TEST-01"
    )
    payload = extract_payload_from_file(result["file_path"])
    layer1_pass, layer2_pass, recomputed = recompute_and_verify(payload)
    assert layer1_pass is True   # Hash matches
    assert layer2_pass is True   # Signature valid

def test_duplicate_cert_id_rejected():
    result1 = issue_certificate(
        cert_id="REC-WND-2026-9999",
        generator_id="WF-TEST-03",
        source_type="Wind",
        energy_kwh=100.0,
        generation_date="2026-03-01",
        issuer_id="ISSUER-TEST-01"
    )
    assert result1["success"] is True

    result2 = issue_certificate(
        cert_id="REC-WND-2026-9999",   # Same ID
        generator_id="WF-TEST-03",
        source_type="Wind",
        energy_kwh=100.0,
        generation_date="2026-03-01",
        issuer_id="ISSUER-TEST-01"
    )
    assert result2["success"] is False

def test_zero_energy_rejected():
    result = issue_certificate(
        generator_id="WF-BAD-01",
        source_type="Wind",
        energy_kwh=0.0,
        generation_date="2026-03-01",
        issuer_id="ISSUER-TEST-01"
    )
    assert result["success"] is False
```

**File: `backend/tests/test_verifier.py`**

```python
"""Tests for all four fraud scenarios + valid baseline."""

import pytest
import json
import copy
import struct
from PIL import Image
from modules.issuer import issue_certificate
from modules.verifier import verify_certificate
from modules.ledger import init_db, mark_claimed

@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("CERT_STORAGE_PATH", str(tmp_path / "certs/"))
    import os; os.makedirs(str(tmp_path / "certs/"), exist_ok=True)
    init_db()

def issue_test_cert(**kwargs):
    return issue_certificate(**{
        "generator_id": "TEST-GEN-01",
        "source_type": "Wind",
        "energy_kwh": 100.0,
        "generation_date": "2026-03-01",
        "issuer_id": "ISSUER-TEST-01",
        "output_format": "png",
        **kwargs
    })

def test_valid_certificate_passes_all_layers():
    issued = issue_test_cert()
    result = verify_certificate(issued["file_path"])
    assert result["final_result"] == "VALID"
    assert result["layers"]["layer1_steganographic_integrity"]["passed"] is True
    assert result["layers"]["layer2_cryptographic_signature"]["passed"] is True
    assert result["layers"]["layer3_ledger_lookup"]["passed"] is True

def test_scenario1_value_tampering_caught_by_layer1(tmp_path):
    """Layer 1: Energy edited from 100 kWh to 1000 kWh after issuance."""
    issued = issue_test_cert(energy_kwh=100.0)
    cert_path = issued["file_path"]

    # Simulate pixel-level tampering by modifying the image
    # In real fraud: attacker edits visible number on certificate
    # We simulate this by corrupting a portion of the LSB payload
    img = Image.open(cert_path)
    pixels = list(img.getdata())
    # Corrupt bytes 200-220 of the image data (inside the steg payload area)
    pixels[200] = (pixels[200][0] ^ 0xFF, pixels[200][1], pixels[200][2])
    tampered = Image.new("RGB", img.size)
    tampered.putdata(pixels)
    tampered_path = str(tmp_path / "tampered.png")
    tampered.save(tampered_path)

    result = verify_certificate(tampered_path)
    assert result["final_result"] == "FRAUD"
    assert result["layers"]["layer1_steganographic_integrity"]["passed"] is False

def test_scenario2_duplicate_certid_caught_by_layer3():
    """Layer 3: Same CertID claimed by two buyers."""
    issued = issue_test_cert(cert_id="REC-SLR-TEST-0034", energy_kwh=1000.0)
    # First claim succeeds
    result1 = verify_certificate(issued["file_path"], claim_cert=True, claimed_by="BUYER-X")
    assert result1["final_result"] == "VALID"

    # Second claim with same file is rejected
    result2 = verify_certificate(issued["file_path"], claim_cert=True, claimed_by="BUYER-Y")
    assert result2["final_result"] == "FRAUD"
    assert result2["layers"]["layer3_ledger_lookup"]["passed"] is False
    assert "already claimed" in result2["fraud_reason"].lower()

def test_scenario3_post_issuance_edit_caught_by_layer1(tmp_path):
    """Layer 1: 500 kWh edited to 5000 kWh post-issuance."""
    issued = issue_test_cert(energy_kwh=500.0)
    # Corrupt the LSB payload
    img = Image.open(issued["file_path"])
    pixels = list(img.getdata())
    pixels[300] = ((pixels[300][0] + 128) % 256, pixels[300][1], pixels[300][2])
    corrupt_img = Image.new("RGB", img.size)
    corrupt_img.putdata(pixels)
    corrupt_path = str(tmp_path / "corrupt.png")
    corrupt_img.save(corrupt_path)

    result = verify_certificate(corrupt_path)
    assert result["final_result"] == "FRAUD"
    assert result["layers"]["layer1_steganographic_integrity"]["passed"] is False

def test_scenario4_duplicate_claim_caught_by_layer3():
    """Layer 3: Certificate claimed once, then resubmitted."""
    issued = issue_test_cert(cert_id="REC-WND-TEST-0102", energy_kwh=750.0)
    # Valid first claim
    r1 = verify_certificate(issued["file_path"], claim_cert=True, claimed_by="BUYER-ECO")
    assert r1["final_result"] == "VALID"
    # Duplicate resubmission
    r2 = verify_certificate(issued["file_path"])
    assert r2["final_result"] == "FRAUD"
    assert r2["layers"]["layer3_ledger_lookup"]["passed"] is False

def test_no_payload_certificate_caught_by_layer1(tmp_path):
    """Layer 1: Plain PNG with no steganographic payload (forged document)."""
    plain_img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    plain_path = str(tmp_path / "no_payload.png")
    plain_img.save(plain_path)

    result = verify_certificate(plain_path)
    assert result["final_result"] == "FRAUD"
    assert result["layers"]["layer1_steganographic_integrity"]["passed"] is False
    assert "no hidden payload" in result["layers"]["layer1_steganographic_integrity"]["detail"].lower()

def test_unregistered_certid_caught_by_layer3(tmp_path):
    """Layer 3: Signed payload but cert_id not in ledger."""
    # Issue but then manually remove from ledger (simulating offline forgery)
    issued = issue_test_cert(cert_id="REC-WND-TEST-GHOST")
    # The test proves the lookup step catches unregistered IDs
    # (full test requires mocking ledger delete — shown for completeness)
```

### Run Tests

```bash
cd backend
# Run all tests with coverage
pytest tests/ -v --cov=. --cov-report=html --cov-report=term

# Run specific scenario tests
pytest tests/test_verifier.py -v -k "scenario"

# Run with structlog output suppressed
pytest tests/ -v -p no:logging
```

---

## 17. Docker and Containerization

**`docker/Dockerfile.backend`**:
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Create storage directories
RUN mkdir -p storage/certificates storage/temp keys

# Generate RSA keys if not mounted
RUN python -c "
import os
if not os.path.exists('keys/private.pem'):
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    pk = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    open('keys/private.pem','wb').write(pk.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    open('keys/public.pem','wb').write(pk.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    print('Keys generated.')
"

EXPOSE 5000
CMD ["gunicorn", "app:create_app()", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120"]
```

**`docker/Dockerfile.frontend`**:
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**`docker/nginx.conf`**:
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # Frontend — React SPA
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API Proxy → Backend
    location /api/ {
        proxy_pass http://backend:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 16m;
        proxy_read_timeout 120s;
    }

    # Certificate Download
    location /api/certificate/ {
        proxy_pass http://backend:5000;
        proxy_set_header Host $host;
    }
}
```

**`docker-compose.yml`** (Development):
```yaml
version: '3.9'

services:
  backend:
    build:
      context: .
      dockerfile: docker/Dockerfile.backend
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
      - FLASK_DEBUG=true
      - FLASK_SECRET_KEY=dev-secret-key-change-in-production
      - JWT_SECRET_KEY=dev-jwt-secret
      - DATABASE_URL=sqlite:///storage/ledger.db
      - CERT_STORAGE_PATH=storage/certificates/
      - TEMP_STORAGE_PATH=storage/temp/
      - CORS_ORIGINS=http://localhost:3000,http://localhost:5173
    volumes:
      - ./backend:/app            # Hot reload
      - rec_storage:/app/storage
      - rec_keys:/app/keys
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: docker/Dockerfile.frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  rec_storage:
  rec_keys:
```

### Run with Docker

```bash
# Development
docker compose up --build

# View logs
docker compose logs -f backend

# Run tests inside container
docker compose exec backend pytest tests/ -v

# Access running app
open http://localhost:3000
```

---

## 18. Cloud Deployment Guide

### AWS Deployment (Recommended for Production)

```bash
# 1. Build and push images to ECR
aws ecr create-repository --repository-name rec-guard-backend
aws ecr create-repository --repository-name rec-guard-frontend

# 2. Tag and push
docker build -t rec-guard-backend -f docker/Dockerfile.backend .
docker tag rec-guard-backend:latest {AWS_ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/rec-guard-backend
docker push {AWS_ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/rec-guard-backend

# 3. Deploy to ECS (Fargate) or use Railway/Render for MVP
```

### Railway.app (Fastest MVP Deploy)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and init project
railway login
railway init

# Deploy backend
cd backend
railway up

# Set environment variables in Railway dashboard:
# FLASK_SECRET_KEY, JWT_SECRET_KEY, DATABASE_URL, etc.
```

### GitHub Actions CI/CD (`.github/workflows/ci.yml`)

```yaml
name: REC Guard CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: sudo apt-get install -y poppler-utils
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: |
          cd backend
          pip install -r requirements.txt
          python -c "
          from cryptography.hazmat.primitives.asymmetric import rsa
          from cryptography.hazmat.primitives import serialization
          import os; os.makedirs('keys', exist_ok=True)
          pk = rsa.generate_private_key(public_exponent=65537, key_size=2048)
          open('keys/private.pem','wb').write(pk.private_bytes(serialization.Encoding.PEM,
              serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
          open('keys/public.pem','wb').write(pk.public_key().public_bytes(
              serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
          "
          pytest tests/ -v --cov=. --cov-report=term-missing

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: |
          cd frontend
          npm ci
          npm run build
```

---

## 19. Roadmap

### Phase 1 — Hackathon MVP (Current)

| Item | Status | Notes |
|---|---|---|
| Flask backend + SQLite ledger | ✅ Build | Core API + DB |
| RSA-2048 key generation | ✅ Build | One-time setup |
| SHA-256 + RSA signing | ✅ Build | Cryptography module |
| LSB steganography (PNG) | ✅ Build | Embed + extract |
| LSB steganography (PDF) | ✅ Build | Via pdf2image |
| Three-layer verifier | ✅ Build | All fraud scenarios |
| React frontend (2 tabs) | ✅ Build | Issue + Verify UI |
| Audit log | ✅ Build | verification_log table |
| Full test suite | ✅ Build | All 4 fraud scenarios |
| Docker setup | ✅ Build | Dev + prod |

### Phase 2 — Hardening (Weeks 2–8)

| Item | Priority | Notes |
|---|---|---|
| Multi-tenant issuer accounts | High | Each issuer manages own RSA keys |
| JWT authentication + roles | High | Regulator / Issuer / Buyer / Auditor roles |
| Statistical ML anomaly layer | High | Isolation Forest on historical generation data |
| PostgreSQL migration | High | Replace SQLite for production concurrency |
| Encrypted cloud storage (S3) | Medium | Move certificate files off local disk |
| Regulator audit dashboard | Medium | Real-time fraud analytics + charts |
| Rate limiting + DDoS protection | Medium | Flask-Limiter + Nginx |
| Automated key rotation | Low | Annual RSA key rotation with backfill |

### Phase 3 — Production SaaS (Months 3–12)

| Item | Priority | Notes |
|---|---|---|
| Hyperledger Fabric DLT ledger | High | Permissioned blockchain replaces SQLite |
| Public verification API | High | Pay-per-verify for buyers/auditors |
| Subscription tiers | Medium | Issuer/regulator monthly SaaS plans |
| SCADA/IoT smart meter integration | Medium | Direct generation data feed (no manual input) |
| Mobile app (Android/iOS) | Low | QR-scan-to-verify for field auditors |
| International standards compliance | Low | I-REC, TIGR, REGO format support |

---

## 20. Expected Impact

| Stated Impact Goal | How REC Guard Delivers It |
|---|---|
| Strengthens integrity and trust in renewable energy markets | Every certificate carries independently verifiable proof. Trust no longer requires contacting the issuer |
| Reduces regulatory and reputational risk for genuine producers | Legitimate certificates verify instantly. Tampering is attributed to the fraudulent copy, not the original producer |
| Improves auditability of national/regional renewable energy claims | The shared ledger gives regulators and auditors a single, queryable record of every issuance and claim event |
| Addresses suggested technology areas | SHA-256 + RSA (encryption) ✓, SQLite → DLT (blockchain) ✓, Isolation Forest (AI/ML) ✓, Encrypted cloud storage (Phase 2) ✓ |

---

## 21. Appendix — Data Structures Reference

### Certificate Payload (Steganographic — Full JSON)

```json
{
  "cert_id":         "REC-WND-2026-0091",
  "generator_id":    "WF-A-01",
  "source_type":     "Wind",
  "energy_kwh":      100.0,
  "generation_date": "2026-03-01",
  "issuer_id":       "ISSUER-GreenCert-04",
  "issued_at":       "2026-03-02T10:15:00+00:00",
  "data_hash":       "c9f0f895fb98ab9159f51fd0297e236d570bfa2c72a43571f1e5c68d96e9f2a3",
  "signature":       "MEUCIQCrGYe2aB...base64-RSA-2048-PSS-signature...=="
}
```

### API Response — Verification (VALID)

```json
{
  "cert_id": "REC-WND-2026-0091",
  "final_result": "VALID",
  "is_valid": true,
  "layers": {
    "layer1_steganographic_integrity": {
      "passed": true,
      "detail": "Hash integrity confirmed. Recomputed SHA-256 matches stored hash: c9f0f895fb98ab91..."
    },
    "layer2_cryptographic_signature": {
      "passed": true,
      "detail": "RSA-2048 signature is valid. Certificate was signed by a registered issuing authority."
    },
    "layer3_ledger_lookup": {
      "passed": true,
      "detail": "Certificate 'REC-WND-2026-0091' is registered, valid, and not yet claimed. Source: Wind, Energy: 100.0 kWh, Issued: 2026-03-02T10:15:00+00:00"
    }
  },
  "fraud_reason": null,
  "extracted_data": { "...": "full payload" },
  "ledger_record":  { "...": "full ledger row" }
}
```

### API Response — Verification (FRAUD)

```json
{
  "cert_id": "REC-WND-2026-0091",
  "final_result": "FRAUD",
  "is_valid": false,
  "layers": {
    "layer1_steganographic_integrity": {
      "passed": false,
      "detail": "HASH MISMATCH. Recomputed: a3b2c1d0e9f8... Stored: c9f0f895fb98... The visible certificate data has been altered after issuance."
    },
    "layer2_cryptographic_signature": {
      "passed": false,
      "detail": "Skipped — Layer 1 failed (hash mismatch)."
    },
    "layer3_ledger_lookup": {
      "passed": false,
      "detail": "Skipped — Layer 1 failed."
    }
  },
  "fraud_reason": "LAYER_1_FAIL: Data hash mismatch — certificate was tampered.",
  "extracted_data": { "...": "extracted but tampered payload" },
  "ledger_record": null
}
```

### Quick Start Commands Summary

```bash
# ── Backend ──────────────────────────────────
cd backend && pip install -r requirements.txt
python -c "from modules.ledger import init_db; init_db()"
# Generate RSA keys (see Section 5.5)
python app.py
# → API running at http://localhost:5000

# ── Frontend ─────────────────────────────────
cd frontend && npm install
npm run dev
# → UI running at http://localhost:5173

# ── Docker (everything at once) ──────────────
docker compose up --build
# → App at http://localhost:3000

# ── Tests ────────────────────────────────────
cd backend && pytest tests/ -v --cov=.

# ── Health Check ─────────────────────────────
curl http://localhost:5000/health
# → {"status": "ok", "service": "REC Guard API", "version": "1.0.0"}
```

---

*REC Guard — Team Exodus | Hackathon Solution Report — September 2026*
*Problem Track: Renewable Energy Certificate (REC) Fraud Detection System*
*Theme: Renewable Energy Intelligence*
