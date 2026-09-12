"""Unit tests for the cryptography module (SHA-256 + RSA-2048 PSS)."""

import base64

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from modules.crypto import (
    build_canonical_payload,
    compute_sha256,
    compute_sha256_string,
    generate_key_pair,
    load_private_key,
    load_public_key,
    load_public_key_from_pem,
    process_certificate_for_issuance,
    public_key_fingerprint,
    public_key_to_pem,
    recompute_and_verify,
    sign_hash,
    verify_signature,
)

CANON = dict(
    cert_id="REC-WND-2026-0091",
    generator_id="WF-A-01",
    source_type="Wind",
    energy_kwh=100.0,
    generation_date="2026-03-01",
    issuer_id="ISSUER-GreenCert-04",
    issued_at="2026-03-02T10:15:00+00:00",
)


def test_sha256_is_deterministic():
    a = compute_sha256(build_canonical_payload(**CANON))
    b = compute_sha256(build_canonical_payload(**CANON))
    assert a == b
    assert len(a) == 64
    assert all(c in "0123456789abcdef" for c in a)


def test_sha256_independent_of_key_order():
    d1 = {"b": 1, "a": 2}
    d2 = {"a": 2, "b": 1}
    assert compute_sha256(d1) == compute_sha256(d2)


def test_sha256_changes_when_energy_changes():
    h1 = compute_sha256(build_canonical_payload(**CANON))
    h2 = compute_sha256(build_canonical_payload(**{**CANON, "energy_kwh": 1000.0}))
    assert h1 != h2


def test_canonical_payload_rounds_energy_and_fixes_order():
    p = build_canonical_payload(**{**CANON, "energy_kwh": "100.0000001"})
    assert p["energy_kwh"] == 100.0
    assert list(p.keys()) == [
        "cert_id",
        "generator_id",
        "source_type",
        "energy_kwh",
        "generation_date",
        "issuer_id",
        "issued_at",
    ]


def test_sha256_string():
    assert compute_sha256_string("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_sign_and_verify_roundtrip():
    priv, pub = load_private_key(), load_public_key()
    h = compute_sha256(CANON)
    sig = sign_hash(h, priv)
    assert base64.b64decode(sig)  # valid base64
    assert verify_signature(h, sig, pub) is True


def test_signature_fails_for_different_hash():
    priv, pub = load_private_key(), load_public_key()
    sig = sign_hash(compute_sha256(CANON), priv)
    assert verify_signature(compute_sha256({**CANON, "energy_kwh": 1}), sig, pub) is False


def test_signature_fails_with_wrong_key():
    priv = load_private_key()
    other_pub = rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key()
    h = compute_sha256(CANON)
    assert verify_signature(h, sign_hash(h, priv), other_pub) is False


def test_garbage_signature_returns_false_not_exception():
    pub = load_public_key()
    assert verify_signature("abc", "not-base64!!", pub) is False
    assert verify_signature("abc", base64.b64encode(b"junk").decode(), pub) is False


def test_process_certificate_for_issuance_builds_payload():
    payload = process_certificate_for_issuance(**CANON)
    assert payload["data_hash"] == compute_sha256(build_canonical_payload(**CANON))
    assert verify_signature(payload["data_hash"], payload["signature"], load_public_key())
    for k in CANON:
        assert payload[k] == CANON[k]


def test_recompute_and_verify_passes_for_authentic_payload():
    payload = process_certificate_for_issuance(**CANON)
    l1, l2, h = recompute_and_verify(payload)
    assert (l1, l2) == (True, True)
    assert h == payload["data_hash"]


def test_recompute_and_verify_detects_tampered_value():
    payload = process_certificate_for_issuance(**CANON)
    payload["energy_kwh"] = 1000.0
    l1, l2, h = recompute_and_verify(payload)
    assert l1 is False  # hash no longer matches the data
    assert l2 is True  # signature over the *stored* hash is still genuine
    assert h != payload["data_hash"]


def test_recompute_and_verify_detects_forged_signature():
    payload = process_certificate_for_issuance(**CANON)
    payload["signature"] = base64.b64encode(b"\x00" * 256).decode()
    l1, l2, _ = recompute_and_verify(payload)
    assert (l1, l2) == (True, False)


def test_recompute_and_verify_handles_missing_fields():
    payload = process_certificate_for_issuance(**CANON)
    del payload["generator_id"]
    assert recompute_and_verify(payload) == (False, False, "")


def test_key_pair_generation_and_pem_roundtrip(tmp_path):
    priv, pub = generate_key_pair(str(tmp_path / "p.pem"), str(tmp_path / "pub.pem"))
    private_key = load_private_key(priv)
    public_key = load_public_key(pub)
    pem = public_key_to_pem(public_key)
    assert pem.startswith("-----BEGIN PUBLIC KEY-----")
    assert public_key_fingerprint(load_public_key_from_pem(pem)) == public_key_fingerprint(public_key)
    h = compute_sha256(CANON)
    assert verify_signature(h, sign_hash(h, private_key), load_public_key_from_pem(pem))
    # second call keeps existing keys
    assert generate_key_pair(priv, pub) == (priv, pub)
    assert public_key_fingerprint(load_public_key(pub)) == public_key_fingerprint(public_key)


def test_generate_key_pair_overwrite(tmp_path):
    priv, pub = generate_key_pair(str(tmp_path / "p.pem"), str(tmp_path / "pub.pem"))
    fp1 = public_key_fingerprint(load_public_key(pub))
    generate_key_pair(priv, pub, overwrite=True)
    assert public_key_fingerprint(load_public_key(pub)) != fp1


@pytest.mark.parametrize("kwh", [0.1, 1, 1e6, 123.456789])
def test_hash_covers_energy_precision(kwh):
    p1 = build_canonical_payload(**{**CANON, "energy_kwh": kwh})
    p2 = build_canonical_payload(**{**CANON, "energy_kwh": kwh + 0.001})
    assert compute_sha256(p1) != compute_sha256(p2)
