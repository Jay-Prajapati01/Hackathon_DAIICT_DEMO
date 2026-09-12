"""Full REST API tests using the Flask test client."""

import io

import pytest
from PIL import Image

from app import create_app
from modules.steg import embed_payload_in_png, extract_payload_from_file


@pytest.fixture
def app(isolated_env, monkeypatch):
    # Depends on isolated_env explicitly: pytest-flask's autouse fixtures request
    # `app` early, so the fresh DATABASE_URL must already be in place here.
    monkeypatch.setenv("ADMIN_EMAIL", "admin@test.io")
    monkeypatch.setenv("ADMIN_PASSWORD", "adminpass123")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-that-is-at-least-32-bytes-long")
    application = create_app({"TESTING": True})
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_token(client):
    r = client.post("/api/auth/login", json={"email": "admin@test.io", "password": "adminpass123"})
    assert r.status_code == 200, r.get_json()
    return r.get_json()["access_token"]


@pytest.fixture
def buyer_token(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "buyer@acme.com", "password": "password123", "role": "buyer", "organisation": "Acme"},
    )
    assert r.status_code == 201, r.get_json()
    return r.get_json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


ISSUE_BODY = {
    "generator_id": "WF-A-01",
    "source_type": "Wind",
    "energy_kwh": 100.0,
    "generation_date": "2026-03-01",
    "issuer_id": "ISSUER-GreenCert-04",
    "format": "png",
}


def _issue(client, **over):
    r = client.post("/api/issue", json={**ISSUE_BODY, **over})
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _download(client, issued):
    r = client.get(issued["download_url"])
    assert r.status_code == 200
    return r.data


def _verify(client, data, filename="cert.png", headers=None, **form):
    payload = {"file": (io.BytesIO(data), filename), **{k: str(v) for k, v in form.items()}}
    return client.post("/api/verify", data=payload, content_type="multipart/form-data", headers=headers or {})


# ── health / auth ──────────────────────────────────────────────


def test_health(client):
    for path in ("/health", "/api/health"):
        r = client.get(path)
        assert r.status_code == 200 and r.get_json()["status"] == "ok"


def test_404_is_json(client):
    r = client.get("/api/nothing")
    assert r.status_code == 404 and r.get_json()["error"] == "Not found"


def test_register_login_me(client, buyer_token):
    r = client.get("/api/auth/me", headers=_auth(buyer_token))
    assert r.status_code == 200
    assert r.get_json()["email"] == "buyer@acme.com" and r.get_json()["role"] == "buyer"
    # duplicate registration
    r = client.post("/api/auth/register", json={"email": "buyer@acme.com", "password": "password123"})
    assert r.status_code == 409
    # bad password
    r = client.post("/api/auth/login", json={"email": "buyer@acme.com", "password": "nope"})
    assert r.status_code == 401
    # validation
    r = client.post("/api/auth/register", json={"email": "bad", "password": "short", "role": "god"})
    assert r.status_code == 422 and len(r.get_json()["details"]) == 3
    # no token
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=_auth("garbage")).status_code == 401


# ── issue ──────────────────────────────────────────────────────


def test_issue_requires_json(client):
    r = client.post("/api/issue", data="not json", content_type="text/plain")
    assert r.status_code == 400


def test_issue_validation_errors(client):
    r = client.post(
        "/api/issue",
        json={
            "generator_id": "",
            "energy_kwh": -1,
            "generation_date": "x",
            "source_type": "Nuclear",
            "format": "docx",
            "cert_id": "bad id",
        },
    )
    assert r.status_code == 422
    details = r.get_json()["details"]
    assert len(details) == 6


def test_issue_future_date_rejected(client):
    r = client.post("/api/issue", json={**ISSUE_BODY, "generation_date": "2999-01-01"})
    assert r.status_code == 422


def test_issue_png_and_download(client):
    issued = _issue(client, cert_id="REC-WND-2026-0091")
    assert issued["cert_id"] == "REC-WND-2026-0091"
    assert issued["download_url"] == "/api/certificate/REC-WND-2026-0091.png"
    assert issued["preview_url"].endswith("/preview")
    assert len(issued["data_hash"]) == 64
    assert issued["anomaly_flag"] is False
    data = _download(client, issued)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    r = client.get(issued["preview_url"])
    assert r.status_code == 200 and r.mimetype == "image/png"


def test_issue_pdf(client):
    issued = _issue(client, format="pdf", cert_id="REC-WND-2026-0092")
    data = _download(client, issued)
    assert data[:4] == b"%PDF"
    assert client.get(issued["preview_url"]).mimetype == "application/pdf"


def test_issue_duplicate_id(client):
    _issue(client, cert_id="REC-WND-2026-0093")
    r = client.post("/api/issue", json={**ISSUE_BODY, "cert_id": "REC-WND-2026-0093"})
    assert r.status_code == 400 and "already exists" in r.get_json()["error"]


def test_issue_uses_jwt_identity_as_issuer_when_missing(client, buyer_token):
    r = client.post(
        "/api/issue", json={k: v for k, v in ISSUE_BODY.items() if k != "issuer_id"}, headers=_auth(buyer_token)
    )
    assert r.status_code == 201
    rec = client.get(f"/api/ledger/{r.get_json()['cert_id']}").get_json()
    assert rec["issuer_id"] == "buyer@acme.com"


def test_issue_anomaly_flag(client):
    issued = _issue(client, energy_kwh=50_000_000)
    assert issued["anomaly_flag"] is True and "ceiling" in issued["anomaly_reason"]


def test_certificate_download_404_and_traversal(client):
    assert client.get("/api/certificate/NOPE.png").status_code == 404
    assert client.get("/api/certificate/..%2F..%2Fkeys%2Fprivate.pem").status_code == 404
    assert client.get("/api/certificate/../config.py").status_code == 404


# ── verify ─────────────────────────────────────────────────────


def test_verify_valid(client):
    issued = _issue(client)
    r = _verify(client, _download(client, issued))
    body = r.get_json()
    assert r.status_code == 200 and body["success"] is True
    assert body["final_result"] == "VALID" and body["is_valid"] is True
    assert body["cert_id"] == issued["cert_id"]
    assert all(v["passed"] for v in body["layers"].values())


def test_verify_pdf_valid(client):
    issued = _issue(client, format="pdf")
    r = _verify(client, _download(client, issued), filename="cert.pdf")
    assert r.get_json()["final_result"] == "VALID"


def test_verify_claim_flow(client, buyer_token):
    issued = _issue(client)
    data = _download(client, issued)
    r = _verify(client, data, headers=_auth(buyer_token), claim="true")
    body = r.get_json()
    assert body["final_result"] == "VALID" and body["claimed"] is True
    assert body["ledger_record"]["claimed_by"] == "buyer@acme.com"
    # second submission by anyone → FRAUD Layer 3
    r2 = _verify(client, data, claim="true", claimed_by="BUYER-GreenTech")
    assert r2.get_json()["final_result"] == "FRAUD"
    assert r2.get_json()["layers"]["layer3_ledger_lookup"]["passed"] is False


def test_verify_claim_without_identity_rejected(client):
    issued = _issue(client)
    r = _verify(client, _download(client, issued), claim="true")
    assert r.status_code == 400 and "claimed_by" in r.get_json()["error"]


def test_verify_tampered(client, tmp_path):
    issued = _issue(client)
    src = tmp_path / "src.png"
    src.write_bytes(_download(client, issued))
    payload = extract_payload_from_file(str(src))
    payload["energy_kwh"] = 1000.0
    embed_payload_in_png(str(src), payload, str(tmp_path / "t.png"))
    r = _verify(client, (tmp_path / "t.png").read_bytes())
    body = r.get_json()
    assert body["final_result"] == "FRAUD" and body["fraud_reason"].startswith("LAYER_1_FAIL")


def test_verify_no_payload(client):
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), (255, 255, 255)).save(buf, format="PNG")
    r = _verify(client, buf.getvalue())
    assert r.get_json()["final_result"] == "FRAUD"
    assert "No steganographic payload" in r.get_json()["fraud_reason"]


def test_verify_bad_uploads(client):
    assert client.post("/api/verify", data={}, content_type="multipart/form-data").status_code == 400
    assert _verify(client, b"x", filename="").status_code == 400
    assert _verify(client, b"hello", filename="x.txt").status_code == 415
    assert _verify(client, b"hello", filename="fake.png").status_code == 415  # magic bytes mismatch


def test_verify_mislabeled_extension_still_works(client):
    """A PNG uploaded with a .pdf name is detected by magic bytes and verified as PNG."""
    issued = _issue(client)
    r = _verify(client, _download(client, issued), filename="cert.pdf")
    assert r.get_json()["final_result"] == "VALID"


# ── ledger ─────────────────────────────────────────────────────


def test_ledger_listing_filters_and_stats(client):
    a = _issue(client, cert_id="REC-WND-2026-0101")
    _issue(client, cert_id="REC-SLR-2026-0102", source_type="Solar", generator_id="SP-C-01")
    r = client.get("/api/ledger?limit=10")
    body = r.get_json()
    assert body["total"] == 2 and body["count"] == 2
    assert client.get("/api/ledger?source_type=Solar").get_json()["total"] == 1
    assert client.get("/api/ledger?search=0101").get_json()["certificates"][0]["cert_id"] == a["cert_id"]
    assert client.get("/api/ledger?limit=abc").status_code == 400
    stats = client.get("/api/ledger/stats").get_json()
    assert stats["total_certificates"] == 2 and stats["total_kwh_registered"] == 200.0
    assert client.get("/api/ledger/REC-WND-2026-0101").get_json()["status"] == "issued"
    assert client.get("/api/ledger/NOPE").status_code == 404


def test_ledger_history(client):
    issued = _issue(client)
    _verify(client, _download(client, issued))
    r = client.get(f"/api/ledger/{issued['cert_id']}/history")
    assert r.status_code == 200 and r.get_json()["verifications"][0]["final_result"] == "VALID"
    assert client.get("/api/ledger/NOPE/history").status_code == 404


def test_ledger_claim_requires_auth(client, buyer_token):
    issued = _issue(client)
    assert client.post(f"/api/ledger/{issued['cert_id']}/claim").status_code == 401
    r = client.post(f"/api/ledger/{issued['cert_id']}/claim", headers=_auth(buyer_token), json={})
    assert r.status_code == 200 and r.get_json()["claimed_by"] == "buyer@acme.com"
    r = client.post(f"/api/ledger/{issued['cert_id']}/claim", headers=_auth(buyer_token), json={})
    assert r.status_code == 400


def test_revoke_requires_regulator_role(client, buyer_token, admin_token):
    issued = _issue(client)
    assert client.post(f"/api/ledger/{issued['cert_id']}/revoke", headers=_auth(buyer_token)).status_code == 403
    r = client.post(f"/api/ledger/{issued['cert_id']}/revoke", headers=_auth(admin_token))
    assert r.status_code == 200 and r.get_json()["status"] == "revoked"
    assert client.post(f"/api/ledger/{issued['cert_id']}/revoke", headers=_auth(admin_token)).status_code == 400
    body = _verify(client, _download(client, issued)).get_json()
    assert body["final_result"] == "FRAUD" and "revoked" in body["fraud_reason"].lower()


def test_issuer_registry_endpoints(client, admin_token, buyer_token):
    from modules.crypto import load_public_key, public_key_to_pem

    pem = public_key_to_pem(load_public_key())
    assert client.get("/api/issuers").get_json()["issuers"] == []
    body = {"issuer_id": "ISS-1", "issuer_name": "Green Cert", "public_key_pem": pem}
    assert client.post("/api/issuers", json=body, headers=_auth(buyer_token)).status_code == 403
    assert client.post("/api/issuers", json=body, headers=_auth(admin_token)).status_code == 201
    assert client.post("/api/issuers", json=body, headers=_auth(admin_token)).status_code == 409
    assert (
        client.post(
            "/api/issuers", json={**body, "issuer_id": "X", "public_key_pem": "junk"}, headers=_auth(admin_token)
        ).status_code
        == 422
    )
    assert client.post("/api/issuers", json={}, headers=_auth(admin_token)).status_code == 422
    assert client.get("/api/issuers").get_json()["issuers"][0]["issuer_id"] == "ISS-1"


# ── admin ──────────────────────────────────────────────────────


def test_admin_dashboard(client, admin_token):
    issued = _issue(client, energy_kwh=50_000_000)
    data = _download(client, issued)
    _verify(client, data)
    buf = io.BytesIO()
    Image.new("RGB", (100, 100)).save(buf, format="PNG")
    _verify(client, buf.getvalue())

    d = client.get("/api/admin/dashboard?days=7").get_json()
    assert d["stats"]["total_certificates"] == 1
    assert d["stats"]["fraud_attempts_detected"] == 1 and d["stats"]["valid_verifications"] == 1
    assert d["by_source"][0]["source_type"] == "Wind"
    assert d["fraud_by_layer"][0]["layer"].startswith("Layer 1")
    assert len(d["daily_activity"]) == 1
    assert len(d["recent_verifications"]) == 2
    assert d["recent_certificates"][0]["cert_id"] == issued["cert_id"]
    assert len(d["open_anomalies"]) == 1

    assert len(client.get("/api/admin/verifications?limit=1").get_json()["verifications"]) == 1
    anomalies = client.get("/api/admin/anomalies?resolved=false").get_json()["anomalies"]
    aid = anomalies[0]["anomaly_id"]
    assert client.post(f"/api/admin/anomalies/{aid}/resolve").status_code == 401
    assert client.post(f"/api/admin/anomalies/{aid}/resolve", headers=_auth(admin_token)).status_code == 200
    assert client.post(f"/api/admin/anomalies/{aid}/resolve", headers=_auth(admin_token)).status_code == 404
    assert client.get("/api/admin/anomalies?resolved=true").get_json()["anomalies"][0]["anomaly_id"] == aid
