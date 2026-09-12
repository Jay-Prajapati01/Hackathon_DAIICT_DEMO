"""Ledger entry dataclass — one row of rec_ledger."""

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class LedgerEntry:
    cert_id: str
    generator_id: str
    source_type: str
    energy_kwh: float
    generation_date: str
    issuer_id: str
    data_hash: str
    signature: str
    status: str = "issued"  # issued | claimed | revoked
    issued_at: str = ""
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None
    cert_file_path: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "LedgerEntry":
        d = dict(row)
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__})

    def to_dict(self) -> dict:
        return asdict(self)

    def to_insert_dict(self) -> dict:
        """Dict matching the named parameters used by ledger.register_certificate."""
        return {
            "cert_id": self.cert_id,
            "generator_id": self.generator_id,
            "source_type": self.source_type,
            "energy_kwh": self.energy_kwh,
            "generation_date": self.generation_date,
            "issuer_id": self.issuer_id,
            "data_hash": self.data_hash,
            "signature": self.signature,
            "issued_at": self.issued_at,
            "cert_file_path": self.cert_file_path,
        }
