"""
Seed the ledger with the blueprint's demo scenarios so the dashboard has data.

    cd backend && python scripts/seed_demo.py [--reset]

Creates (from tests/fixtures/sample_data.json):
  * a clean Hydro baseline certificate                         → VALID
  * Scenario 1: Wind 100 kWh, then a tampered copy at 1000 kWh → FRAUD (Layer 1)
  * Scenario 2: Solar 1 MW claimed by Buyer X, re-used by Y    → FRAUD (Layer 3)
  * Scenario 3: Solar 500 kWh edited to 5000 kWh               → FRAUD (Layer 1)
  * Scenario 4: Wind 750 kWh claimed, then resubmitted         → FRAUD (Layer 3)
  * a plain PNG with no payload                                → FRAUD (Layer 1)
The tampered files are written next to the originals as *_TAMPERED.png so they
can be dragged into the Verify page during a demo.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)

from PIL import Image  # noqa: E402

from config import cert_storage_path  # noqa: E402
from modules import ledger  # noqa: E402
from modules.crypto import generate_key_pair  # noqa: E402
from modules.issuer import issue_certificate  # noqa: E402
from modules.steg import embed_payload_in_png, extract_payload_from_file  # noqa: E402
from modules.verifier import verify_certificate  # noqa: E402


def tamper(src_path: str, out_path: str, **changes) -> str:
    payload = extract_payload_from_file(src_path)
    payload.update(changes)
    return embed_payload_in_png(src_path, payload, out_path)


def main():
    if "--reset" in sys.argv:
        for name in os.listdir(os.path.dirname(ledger.get_db_path())):
            if name.startswith("ledger.db"):
                os.remove(os.path.join(os.path.dirname(ledger.get_db_path()), name))
    generate_key_pair()
    ledger.init_db()

    with open(os.path.join(BACKEND, "tests", "fixtures", "sample_data.json")) as f:
        data = json.load(f)
    storage = cert_storage_path()
    os.makedirs(storage, exist_ok=True)

    def issue(spec, **over):
        fields = {k: spec[k] for k in ("cert_id", "generator_id", "source_type", "generation_date", "issuer_id")}
        fields["energy_kwh"] = float(spec.get("energy_kwh", spec.get("energy_kwh_original", 0)))
        fields.update(over)
        if ledger.lookup_certificate(fields["cert_id"]):
            print(f"  = {fields['cert_id']} already in ledger, skipping issuance")
            return ledger.lookup_certificate(fields["cert_id"])["cert_file_path"]
        r = issue_certificate(**fields, output_format="png")
        if not r["success"]:
            raise SystemExit(f"issuance failed: {r['error']}")
        print(f"  + issued {r['cert_id']} ({fields['energy_kwh']:.0f} kWh {fields['source_type']})")
        return r["file_path"]

    def verify(path, label, **kw):
        r = verify_certificate(path, verifier_id="demo-seed", verifier_ip="127.0.0.1", **kw)
        print(f"  → {label}: {r['final_result']}" + (f" — {r['fraud_reason']}" if r["fraud_reason"] else ""))
        return r

    print("Baseline")
    base = issue(data["scenario_valid_baseline"])
    verify(base, "clean Hydro certificate")

    print("Scenario 1 — value tampering 100 → 1000 kWh")
    s1 = data["scenario_1_value_tampering"]
    p1 = issue(s1["original"])
    t1 = tamper(p1, p1.replace(".png", "_TAMPERED.png"), energy_kwh=float(s1["tampered_energy_kwh"]))
    verify(p1, "original")
    verify(t1, "tampered copy")

    print("Scenario 2 — same CertID sold to two buyers")
    s2 = data["scenario_2_duplicate_certid"]
    p2 = issue(s2)
    verify(p2, f"claim by {s2['buyer_x']}", claim_cert=True, claimed_by=s2["buyer_x"])
    verify(p2, f"claim by {s2['buyer_y']}", claim_cert=True, claimed_by=s2["buyer_y"])

    print("Scenario 3 — 500 → 5000 kWh edit")
    s3 = data["scenario_3_value_edit"]
    p3 = issue(s3, energy_kwh=float(s3["energy_kwh_original"]))
    t3 = tamper(p3, p3.replace(".png", "_TAMPERED.png"), energy_kwh=float(s3["energy_kwh_tampered"]))
    verify(t3, "edited copy")

    print("Scenario 4 — duplicate claim")
    s4 = data["scenario_4_duplicate_claim"]
    p4 = issue(s4)
    verify(p4, f"claim by {s4['first_claimer']}", claim_cert=True, claimed_by=s4["first_claimer"])
    verify(p4, f"resubmission by {s4['second_claimer']}")

    print("Forgery — plain image with no payload")
    plain = os.path.join(storage, "FORGED_no_payload.png")
    Image.new("RGB", (1400, 1000), (247, 245, 238)).save(plain)
    verify(plain, "plain PNG")

    print("Anomaly — implausible issuance for review")
    r = issue_certificate(
        generator_id="WF-A-01",
        source_type="Wind",
        energy_kwh=9_000_000,
        generation_date="2026-03-01",
        issuer_id="ISSUER-GreenCert-04",
        output_format="png",
    )
    print(f"  + issued {r['cert_id']} anomaly_flag={r['anomaly_flag']}")

    stats = ledger.get_ledger_stats()
    print("\nLedger stats:", json.dumps(stats, indent=2))
    print(f"Certificate files in {storage}")


if __name__ == "__main__":
    main()
