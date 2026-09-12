"""Verification result — the three-layer verdict returned by Module 2."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VerificationResult:
    cert_id: Optional[str] = None
    layer1_pass: bool = False
    layer2_pass: bool = False
    layer3_pass: bool = False
    layer1_detail: str = ""
    layer2_detail: str = ""
    layer3_detail: str = ""
    final_result: str = "FRAUD"  # "VALID" or "FRAUD"
    fraud_reason: Optional[str] = None
    extracted_payload: Optional[dict] = None
    ledger_record: Optional[dict] = None
    uploaded_hash: str = ""
    file_sha256: str = ""
    verified_at: str = ""
    claimed: bool = False
    anomalies: list = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.final_result == "VALID"

    def to_dict(self) -> dict:
        return {
            "cert_id": self.cert_id,
            "final_result": self.final_result,
            "is_valid": self.is_valid,
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
            "uploaded_hash": self.uploaded_hash,
            "file_sha256": self.file_sha256,
            "verified_at": self.verified_at,
            "claimed": self.claimed,
            "anomalies": self.anomalies,
        }
