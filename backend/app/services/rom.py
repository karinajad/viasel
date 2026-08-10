"""The ROM engine — price a requirement from the executed corpus.

Normalization is the mechanism: prices are compared per natural denominator
($/kVA, $/ton, $/kW ...), so any size can be priced from all history of that type.
The band's spread IS the real vendor spread; confidence falls out of the comparable
count and whether the comparables are executed vs. proposal vs. ROM.
"""

from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExecutedScopeLine
from app.schemas.rom import RomBand


def _f(x: object, default: float = 0.0) -> float:
    return float(x) if x is not None else default  # type: ignore[arg-type]


def _all_in_per_denom(r: ExecutedScopeLine) -> float:
    """Normalized all-in price per denominator unit for one executed line."""
    size = _f(r.size, 1.0) or 1.0
    if r.allin_reported is not None:
        reported = _f(r.allin_reported)
    else:
        reported = (_f(r.base_unit) + _f(r.services_unit)) * (1 + _f(r.tax_pct))
    return reported / size


def price(
    session: Session,
    type_query: str,
    denominator: str,
    size: float,
    qty: int,
    *,
    freight_unit: float = 0.0,
    tariff_pct: float = 0.0,
    escalation_pct: float = 0.0,
) -> RomBand:
    rows = list(
        session.scalars(
            select(ExecutedScopeLine).where(
                ExecutedScopeLine.etype.ilike(f"%{type_query}%"),
                ExecutedScopeLine.denominator == denominator,
                ExecutedScopeLine.base_unit.is_not(None),
                ExecutedScopeLine.size.is_not(None),
            )
        )
    )

    def status_is(r: ExecutedScopeLine, key: str) -> bool:
        return key in (r.status or "").lower()

    executed = [r for r in rows if status_is(r, "exec")]
    proposal = [r for r in rows if status_is(r, "proposal")]
    pool = executed or proposal or rows
    fallback = not executed

    empty = RomBand(
        type_query=type_query, denominator=denominator, size=size, qty=qty,
        comparables_count=0, confidence_tier="none",
        unit_low=None, unit_mid=None, unit_high=None, extended_mid=None,
        layers={}, note="no comparables — fall back to quotes / published pricing / judgment",
    )
    if not pool:
        return empty

    per = sorted(_all_in_per_denom(r) for r in pool)
    lo, mid, hi = per[0], median(per), per[-1]

    def scale(v: float) -> float:
        return (v * size + freight_unit) * (1 + tariff_pct) * (1 + escalation_pct)

    unit_low, unit_mid, unit_high = scale(lo), scale(mid), scale(hi)

    n = len(pool)
    if fallback:
        tier = "low"
    elif n >= 6:
        tier = "high"
    elif n >= 3:
        tier = "medium"
    else:
        tier = "low"

    layers = {
        "base": round(median([_f(r.base_unit) / (_f(r.size, 1.0) or 1.0) for r in pool]) * size, 2),
        "services": round(median([_f(r.services_unit) for r in pool]), 2),
        "freight": round(freight_unit, 2),
        "tariff_pct": tariff_pct,
        "tax_pct": round(median([_f(r.tax_pct) for r in pool]), 5),
        "escalation_pct": escalation_pct,
    }

    return RomBand(
        type_query=type_query, denominator=denominator, size=size, qty=qty,
        comparables_count=n, confidence_tier=tier,
        unit_low=round(unit_low, 2), unit_mid=round(unit_mid, 2), unit_high=round(unit_high, 2),
        extended_mid=round(unit_mid * qty, 2),
        layers=layers,
        note=("comparables are proposals/ROM, not executed — treat as low confidence"
              if fallback else None),
    )
