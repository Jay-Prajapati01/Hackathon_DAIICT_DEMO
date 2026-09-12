"""Input validation helpers for the REST API."""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from config import ALLOWED_OUTPUT_FORMATS, ALLOWED_SOURCE_TYPES

CERT_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9\-_]{2,63}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-_.@ ]{0,99}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_date(value: Any) -> bool:
    try:
        datetime.strptime(str(value), "%Y-%m-%d")
        return True
    except (TypeError, ValueError):
        return False


def is_future_date(value: str) -> bool:
    try:
        d = datetime.strptime(value, "%Y-%m-%d").date()
        return d > datetime.now(timezone.utc).date()
    except (TypeError, ValueError):
        return False


def validate_cert_id(cert_id: Any) -> bool:
    return isinstance(cert_id, str) and bool(CERT_ID_RE.match(cert_id))


def validate_issue_input(data: Dict[str, Any]) -> List[str]:
    """Return a list of human-readable validation errors (empty list = valid)."""
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["Request body must be a JSON object."]

    gen = data.get("generator_id")
    if not gen or not isinstance(gen, str) or not gen.strip():
        errors.append("generator_id is required.")
    elif not ID_RE.match(gen.strip()):
        errors.append("generator_id contains invalid characters (max 100, alphanumeric, - _ . @).")

    source = data.get("source_type", "Solar")
    if source not in ALLOWED_SOURCE_TYPES:
        errors.append(f"source_type must be one of: {', '.join(ALLOWED_SOURCE_TYPES)}.")

    kwh = data.get("energy_kwh")
    try:
        kwh_f = float(kwh)
        if kwh_f <= 0:
            errors.append("energy_kwh must be a positive number.")
        elif kwh_f != kwh_f or kwh_f == float("inf"):
            errors.append("energy_kwh must be a finite number.")
    except (TypeError, ValueError):
        errors.append("energy_kwh is required and must be numeric.")

    gdate = data.get("generation_date")
    if not gdate:
        errors.append("generation_date is required (YYYY-MM-DD).")
    elif not is_valid_date(gdate):
        errors.append("generation_date must be in YYYY-MM-DD format.")
    elif is_future_date(gdate):
        errors.append("generation_date cannot be in the future.")

    issuer = data.get("issuer_id")
    if issuer is not None and issuer != "" and (not isinstance(issuer, str) or not ID_RE.match(issuer)):
        errors.append("issuer_id contains invalid characters.")

    cert_id = data.get("cert_id")
    if cert_id not in (None, "") and not validate_cert_id(cert_id):
        errors.append(
            "cert_id must be 3-64 uppercase alphanumeric characters (hyphens allowed), e.g. REC-WND-2026-0091."
        )

    fmt = data.get("format", "png")
    if fmt not in ALLOWED_OUTPUT_FORMATS:
        errors.append("format must be 'png' or 'pdf'.")

    return errors


def validate_register_input(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["Request body must be a JSON object."]
    email = data.get("email", "")
    if not isinstance(email, str) or not EMAIL_RE.match(email):
        errors.append("A valid email is required.")
    pwd = data.get("password", "")
    if not isinstance(pwd, str) or len(pwd) < 8:
        errors.append("password must be at least 8 characters.")
    role = data.get("role", "auditor")
    if role not in ("regulator", "issuer", "buyer", "auditor"):
        errors.append("role must be one of regulator, issuer, buyer, auditor.")
    return errors
