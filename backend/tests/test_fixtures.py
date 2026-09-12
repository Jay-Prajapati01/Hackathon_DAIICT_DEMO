"""Structural checks on the committed fixture files."""

import os

from modules.crypto import recompute_and_verify
from modules.steg import extract_payload_from_file

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def test_valid_fixture_has_consistent_payload():
    p = extract_payload_from_file(os.path.join(FIX, "valid_cert.png"))
    assert p and p["cert_id"] == "REC-WND-2026-0091" and p["energy_kwh"] == 100.0
    layer1, _, _ = recompute_and_verify(p)  # signature depends on whichever key signed it
    assert layer1 is True


def test_tampered_fixture_fails_hash():
    p = extract_payload_from_file(os.path.join(FIX, "tampered_cert.png"))
    assert p and p["energy_kwh"] == 1000.0
    assert recompute_and_verify(p)[0] is False


def test_no_payload_fixture():
    assert extract_payload_from_file(os.path.join(FIX, "no_payload_cert.png")) is None
