"""
REC Guard — Statistical Anomaly Detection Layer

Runs *before* a certificate is issued and flags suspicious issuance patterns.
It never blocks issuance (that is a regulator decision); it produces a score,
a human-readable reason, and writes to anomaly_log so the dashboard can surface
open anomalies for review.

Two complementary detectors:

1. Deterministic rules (always on, no training data needed)
   - generation date in the future or implausibly old
   - energy amount above the physical ceiling for the source type
   - duplicate-issuance pattern: same generator + generation date already certified
   - issuance burst: many certificates for one generator inside 24 h

2. Isolation Forest (scikit-learn) on the generator's own history
   - trained on the fly from ledger rows (+ optional historical CSV)
   - needs at least MIN_SAMPLES_FOR_MODEL records; below that a z-score is used
   - decision_function() < ANOMALY_THRESHOLD ⇒ anomaly
"""

import csv
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import structlog

from config import anomaly_threshold, historical_data_path
from modules import ledger

log = structlog.get_logger()

MIN_SAMPLES_FOR_MODEL = 10  # Isolation Forest below this is meaningless
MIN_SAMPLES_FOR_ZSCORE = 4
ZSCORE_LIMIT = 3.0
MAX_AGE_YEARS = 3
BURST_LIMIT_24H = 20

# Physical plausibility ceiling per single certificate (kWh).
# Roughly: largest plausible single-day output of one facility of that type.
MAX_KWH_PER_CERT: Dict[str, float] = {
    "Wind": 2_500_000,  # ~100 MW farm × 24 h
    "Solar": 1_500_000,  # ~250 MWp plant × ~6 h
    "Hydro": 25_000_000,  # ~1 GW station × 24 h
    "Biomass": 2_500_000,
    "Geothermal": 5_000_000,
    "Tidal": 1_000_000,
    "Other": 5_000_000,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_date(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _load_csv_history(generator_id: str) -> List[dict]:
    """Optional historical generation data (HISTORICAL_DATA_PATH) for the generator."""
    path = historical_data_path()
    if not os.path.exists(path):
        return []
    rows: List[dict] = []
    try:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                if row.get("generator_id") == generator_id:
                    try:
                        rows.append(
                            {
                                "energy_kwh": float(row["energy_kwh"]),
                                "generation_date": row.get("generation_date", ""),
                                "source_type": row.get("source_type", ""),
                            }
                        )
                    except (KeyError, ValueError):
                        continue
    except OSError as e:
        log.warning("historical_csv_unreadable", path=path, error=str(e))
    return rows


def _features(energy_kwh: float, generation_date: str) -> List[float]:
    dt = _parse_date(generation_date) or _now()
    doy = dt.timetuple().tm_yday
    return [
        float(energy_kwh),
        math.log1p(max(float(energy_kwh), 0.0)),
        math.sin(2 * math.pi * doy / 366.0),
        math.cos(2 * math.pi * doy / 366.0),
    ]


def _isolation_forest_score(history: List[dict], energy_kwh: float, generation_date: str) -> Optional[float]:
    """Return the Isolation Forest decision score for the new point, or None if not enough data."""
    if len(history) < MIN_SAMPLES_FOR_MODEL:
        return None
    try:
        import numpy as np
        from sklearn.ensemble import IsolationForest
    except ImportError:  # pragma: no cover
        log.warning("sklearn_unavailable")
        return None

    X = np.array([_features(h["energy_kwh"], h.get("generation_date", "")) for h in history])
    model = IsolationForest(n_estimators=100, contamination="auto", random_state=42)
    model.fit(X)
    score = float(model.decision_function(np.array([_features(energy_kwh, generation_date)]))[0])
    return score


def _zscore(history: List[dict], energy_kwh: float) -> Optional[float]:
    values = [float(h["energy_kwh"]) for h in history]
    if len(values) < MIN_SAMPLES_FOR_ZSCORE:
        return None
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    std = math.sqrt(var)
    if std == 0:
        return 0.0 if energy_kwh == mean else float("inf")
    return (energy_kwh - mean) / std


def check_issuance_anomaly(
    generator_id: str,
    source_type: str,
    energy_kwh: float,
    generation_date: str,
    cert_id: Optional[str] = None,
    persist: bool = True,
) -> dict:
    """
    Evaluate a pending issuance for anomalies.

    Returns:
        {
          "is_anomaly": bool,
          "score": float,          # Isolation Forest score (or a rule-derived proxy)
          "reason": str | None,    # first / most severe reason
          "reasons": [str, ...],   # every triggered check
          "method": "rules" | "zscore" | "isolation_forest",
          "history_size": int,
        }
    """
    reasons: List[str] = []
    score = 0.0
    method = "rules"
    history: List[dict] = []

    try:
        energy_kwh = float(energy_kwh)

        # ── Rule 1: generation date sanity ─────────────────────
        gen_dt = _parse_date(generation_date)
        if gen_dt is None:
            reasons.append(f"Invalid generation_date '{generation_date}' (expected YYYY-MM-DD).")
        else:
            today = _now().replace(hour=0, minute=0, second=0, microsecond=0)
            if gen_dt > today:
                reasons.append(f"Generation date {generation_date} is in the future.")
            elif (today - gen_dt).days > MAX_AGE_YEARS * 365:
                reasons.append(f"Generation date {generation_date} is more than {MAX_AGE_YEARS} years old.")

        # ── Rule 2: physical ceiling ───────────────────────────
        ceiling = MAX_KWH_PER_CERT.get(source_type, MAX_KWH_PER_CERT["Other"])
        if energy_kwh > ceiling:
            reasons.append(
                f"{energy_kwh:,.0f} kWh exceeds the plausible single-certificate ceiling "
                f"for {source_type} ({ceiling:,.0f} kWh)."
            )

        # ── Rule 3: duplicate issuance pattern ─────────────────
        same_day = ledger.get_certificates_for_generation(generator_id, generation_date)
        if same_day:
            prior_kwh = sum(float(r["energy_kwh"]) for r in same_day)
            ids = ", ".join(r["cert_id"] for r in same_day[:3])
            reasons.append(
                f"Generator {generator_id} already has {len(same_day)} certificate(s) for "
                f"{generation_date} ({prior_kwh:,.0f} kWh: {ids}). Possible duplicate issuance."
            )
            if prior_kwh + energy_kwh > ceiling:
                reasons.append(
                    f"Cumulative {prior_kwh + energy_kwh:,.0f} kWh certified for {generation_date} "
                    f"exceeds the {source_type} ceiling ({ceiling:,.0f} kWh)."
                )

        # ── Rule 4: issuance burst ─────────────────────────────
        since = (_now() - timedelta(hours=24)).isoformat()
        recent = ledger.count_recent_issuances(generator_id, since)
        if recent >= BURST_LIMIT_24H:
            reasons.append(f"{recent} certificates issued for {generator_id} in the last 24 h (burst).")

        # ── Statistical layer ──────────────────────────────────
        history = ledger.get_generator_history(generator_id) + _load_csv_history(generator_id)
        threshold = anomaly_threshold()
        if_score = _isolation_forest_score(history, energy_kwh, generation_date)
        if if_score is not None:
            method = "isolation_forest"
            score = if_score
            if if_score < threshold:
                reasons.append(
                    f"Isolation Forest score {if_score:.3f} < threshold {threshold} "
                    f"(unusual versus {len(history)} historical records for {generator_id})."
                )
        else:
            z = _zscore(history, energy_kwh)
            if z is not None:
                method = "zscore"
                # map |z| onto the same sign convention as IsolationForest (negative = anomalous)
                score = -min(abs(z), 10.0) / 10.0 if abs(z) > ZSCORE_LIMIT else 0.1
                if abs(z) > ZSCORE_LIMIT:
                    reasons.append(
                        f"{energy_kwh:,.0f} kWh is {abs(z):.1f} standard deviations from "
                        f"{generator_id}'s historical mean ({len(history)} records)."
                    )

        is_anomaly = len(reasons) > 0
        if is_anomaly and method == "rules":
            score = -1.0  # rule violations are treated as maximally anomalous

        result = {
            "is_anomaly": is_anomaly,
            "score": round(float(score), 4),
            "reason": reasons[0] if reasons else None,
            "reasons": reasons,
            "method": method,
            "history_size": len(history),
        }

        if is_anomaly:
            log.warning("issuance_anomaly", generator_id=generator_id, cert_id=cert_id, reasons=reasons)
            if persist and cert_id:
                try:
                    ledger.log_anomaly(cert_id, result["score"], " | ".join(reasons))
                except Exception as e:  # never let logging break issuance
                    log.error("anomaly_log_failed", error=str(e))
        return result

    except Exception as e:
        log.error("anomaly_check_failed", error=str(e))
        return {
            "is_anomaly": False,
            "score": 0.0,
            "reason": None,
            "reasons": [],
            "method": "error",
            "history_size": len(history),
            "error": str(e),
        }
