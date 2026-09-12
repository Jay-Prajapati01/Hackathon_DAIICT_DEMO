# REC Guard — Renewable Energy Certificate Fraud Detection

REC Guard makes Renewable Energy Certificate (REC) fraud detectable **by construction**.
Every certificate carries its own cryptographic proof, hidden inside the file itself, and is
registered in a shared ledger. Anyone can verify a certificate in seconds without contacting
the issuing body.

Team Exodus · Theme: Renewable Energy Intelligence · Track: REC Fraud Detection System

## How it works

```
 MODULE 1 — ISSUER                          MODULE 2 — VERIFIER
 ───────────────────                        ───────────────────
 REC data (ID · generator · kWh · date)     Upload suspect PNG / PDF
          │                                          │
          ▼                                          ▼
 SHA-256 hash  ──►  RSA-2048 PSS signature   Layer 1  extract LSB payload, recompute hash
          │                                          │  catches edited values, no-payload fakes
          ▼                                          ▼
 Render certificate artwork                  Layer 2  verify issuer's RSA signature
          │                                          │  catches forged payloads / unknown signers
          ▼                                          ▼
 Hide payload in pixel LSBs (PNG or PDF)     Layer 3  ledger lookup: registered? hash matches?
          │                                          │  already claimed? revoked?
          ▼                                          ▼
 Register in shared ledger                   VALID only if all three layers pass
```

| Fraud type | Caught by |
|---|---|
| Value tampering after issuance (100 → 1000 kWh) | Layer 1 — hash mismatch |
| Forged certificate with no hidden payload | Layer 1 — no payload |
| Payload re-signed with an attacker's key | Layer 2 — signature invalid |
| Same certificate ID sold to two buyers | Layer 3 — already claimed / ledger hash mismatch |
| Re-using an already-claimed certificate | Layer 3 — already claimed |
| Certificate never issued / revoked by regulator | Layer 3 — not found / revoked |

A statistical anomaly layer (deterministic rules + Isolation Forest on the generator's history)
screens every issuance and flags suspicious patterns for regulator review without blocking them.

## Repository layout

```
backend/     Flask API — modules/ (ledger, crypto, steg, issuer, verifier, anomaly,
             certificate_gen), routes/, models/, utils/, scripts/, tests/
frontend/    React 18 + Vite + Redux Toolkit UI (dashboard, issue, verify, ledger, login)
docker/      Dockerfiles, nginx config, entrypoint
.github/     CI: backend lint + tests, frontend tests + build, docker builds
```

## Quick start (local)

Prerequisites: Python 3.11+, Node 18+, poppler (`brew install poppler` / `apt install poppler-utils`).

```bash
# Backend
cd backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/generate_keys.py        # RSA-2048 key pair (once)
python scripts/init_db.py              # SQLite ledger
python scripts/seed_demo.py            # optional: demo certificates + fraud scenarios
python app.py                          # → http://localhost:5000

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env                   # VITE_API_URL=http://localhost:5000
npm run dev                            # → http://localhost:5173
```

Default admin (from `.env`): `admin@recguard.io` / `changeme`.
On macOS, port 5000 may be used by AirPlay Receiver; set `FLASK_PORT=5001` in `backend/.env`
and `VITE_API_URL=http://localhost:5001` in `frontend/.env` if so.

`make setup`, `make backend`, `make frontend`, `make test`, `make seed` wrap the same steps.

## Docker

```bash
docker compose up --build                      # dev: UI http://localhost:3000, API :5000
docker compose -f docker-compose.prod.yml up -d --build   # prod: gunicorn + nginx on :80
```

Keys and the ledger live on named volumes and are created on first start.

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | – | Service health |
| POST | `/api/auth/register` · `/login` | – | JWT auth (roles: regulator, issuer, buyer, auditor) |
| GET | `/api/auth/me` | JWT | Current user |
| POST | `/api/issue` | optional | Issue a certificate (JSON body, `format: png|pdf`) |
| GET | `/api/certificate/<file>` · `/preview` | – | Download / inline preview |
| POST | `/api/verify` | optional | Multipart `file`, optional `claim=true`, `claimed_by` |
| GET | `/api/ledger` | – | Filter by `status`, `source_type`, `search`, paginate |
| GET | `/api/ledger/stats` · `/<id>` · `/<id>/history` | – | Stats, record, audit trail |
| POST | `/api/ledger/<id>/claim` | JWT | Claim a certificate |
| POST | `/api/ledger/<id>/revoke` | regulator | Revoke a certificate |
| GET/POST | `/api/issuers` | – / regulator | Issuer registry (public keys) |
| GET | `/api/admin/dashboard` · `/verifications` · `/anomalies` | – | Dashboard data |
| POST | `/api/admin/anomalies/<id>/resolve` | regulator | Close an anomaly |

Example:

```bash
curl -X POST http://localhost:5000/api/issue -H 'Content-Type: application/json' -d '{
  "generator_id": "WF-A-01", "source_type": "Wind", "energy_kwh": 100,
  "generation_date": "2026-03-01", "issuer_id": "ISSUER-GreenCert-04", "format": "png"}'

curl -X POST http://localhost:5000/api/verify -F file=@REC-WND-2026-XXXX.png
```

## Tests

```bash
cd backend && pytest tests/ -v --cov=. -p no:logging     # 130 tests, all fraud scenarios
cd frontend && npm test                                   # Vitest + Testing Library smoke suite
```

## Security notes

* Hashing proves the data was not changed; signing proves who issued it; the ledger proves it
  was issued once and claimed once. Steganography carries that proof inside the file. All four
  are needed — see the blueprint's Security Design section.
* The private key is generated locally (`backend/keys/private.pem`, git-ignored). In production
  keep it in an HSM / KMS, use one key pair per issuing body (registered via `/api/issuers`),
  rotate annually, and serve everything over TLS.
* Verification never stores the uploaded file; every attempt (valid or fraudulent, including
  payload-less forgeries) is written to the audit log.

## Roadmap

Phase 2: multi-tenant issuer keys, PostgreSQL, S3 storage, rate limiting, key rotation.
Phase 3: Hyperledger Fabric ledger, public verification API, SCADA/smart-meter feeds,
mobile QR verification, I-REC / REGO format support.

Full specification: `REC_GUARD_BLUEPRINT.md`.
