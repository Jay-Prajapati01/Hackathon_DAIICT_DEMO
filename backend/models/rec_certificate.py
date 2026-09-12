"""REC Certificate dataclass — the data that gets hashed, signed and embedded."""

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class RECCertificate:
    cert_id: str
    generator_id: str
    source_type: str
    energy_kwh: float
    generation_date: str  # YYYY-MM-DD
    issuer_id: str
    issued_at: str  # ISO-8601 UTC
    data_hash: Optional[str] = None
    signature: Optional[str] = None
    file_path: Optional[str] = None
    output_format: str = "png"
    anomaly_flag: bool = False
    anomaly_reason: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def canonical(self) -> dict:
        """Fields (in fixed order) that are covered by the SHA-256 hash."""
        return {
            "cert_id": self.cert_id,
            "generator_id": self.generator_id,
            "source_type": self.source_type,
            "energy_kwh": round(float(self.energy_kwh), 6),
            "generation_date": self.generation_date,
            "issuer_id": self.issuer_id,
            "issued_at": self.issued_at,
        }

    def steg_payload(self) -> dict:
        """Full payload hidden inside the certificate file."""
        return {**self.canonical(), "data_hash": self.data_hash, "signature": self.signature}

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RECCertificate":
        known = {k: d.get(k) for k in cls.__dataclass_fields__ if k in d}
        return cls(**known)
