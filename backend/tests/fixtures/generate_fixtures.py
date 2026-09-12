"""
Regenerate the binary test fixtures in this directory.

    cd backend && python tests/fixtures/generate_fixtures.py

Produces:
  valid_cert.png       — signed with the *current* keys/private.pem, payload intact
  tampered_cert.png    — same certificate with energy_kwh edited (hash mismatch)
  no_payload_cert.png  — plain artwork with no hidden payload (forgery)

The tests never rely on these verifying against the ledger (they issue their own
certificates); the files exist for manual demos and structural checks.
"""

import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from modules.certificate_gen import generate_certificate_png  # noqa: E402
from modules.crypto import process_certificate_for_issuance  # noqa: E402
from modules.steg import embed_payload_in_png  # noqa: E402


def main():
    with open(os.path.join(HERE, "sample_data.json")) as f:
        data = json.load(f)["scenario_1_value_tampering"]
    original = data["original"]
    issued_at = datetime(2026, 3, 2, 10, 15, tzinfo=timezone.utc).isoformat()

    raw = os.path.join(HERE, "_raw.png")
    generate_certificate_png(**original, output_path=raw, issued_at=issued_at)
    payload = process_certificate_for_issuance(**original, issued_at=issued_at)

    embed_payload_in_png(raw, payload, os.path.join(HERE, "valid_cert.png"))
    tampered = {**payload, "energy_kwh": float(data["tampered_energy_kwh"])}
    embed_payload_in_png(raw, tampered, os.path.join(HERE, "tampered_cert.png"))
    os.replace(raw, os.path.join(HERE, "no_payload_cert.png"))
    print("fixtures written to", HERE)


if __name__ == "__main__":
    main()
