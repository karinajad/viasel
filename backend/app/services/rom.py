"""The ROM engine — price a requirement from the executed corpus.

Normalization is the mechanism: prices are compared per natural denominator
($/kVA, $/ton, $/kW ...), so any size can be priced from all history of that type.
The band's spread IS the real vendor spread; confidence falls out of the comparable
count and whether the comparables are executed vs. proposal vs. ROM.

One line or a whole line-item list prices the same way: `price_many` reuses one
corpus query per distinct (type, denominator), then `rollup` totals the bands.
"""

from collections import Counter
from collections.abc import Callable, Sequence
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DemandLine, ExecutedScopeLine
from app.schemas.rom import Comparable, ComparableGroup, RomBand, RomBatchLine, RomRollup

# weakest → strongest; a total is only as good as its weakest input
TIER_ORDER = ("none", "low", "medium", "high")


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


def _comparables(session: Session, type_query: str, denominator: str) -> list[ExecutedScopeLine]:
    """Every executed line of this type priced in this denominator."""
    return list(
        session.scalars(
            select(ExecutedScopeLine).where(
                ExecutedScopeLine.etype.ilike(f"%{type_query}%"),
                ExecutedScopeLine.denominator == denominator,
                ExecutedScopeLine.base_unit.is_not(None),
                ExecutedScopeLine.size.is_not(None),
            )
        )
    )


def _route(r: ExecutedScopeLine) -> tuple[str | None, str | None]:
    """Who you buy it from, and who made it. A distributor sourcing a different OEM is a
    different buy, and the corpus shows that difference dwarfing every other variable."""
    return (r.supplier, r.oem)


def _groups(
    pool: Sequence[ExecutedScopeLine],
    size: float,
    scale: Callable[[float], float],
) -> list[ComparableGroup]:
    """The receipts behind the band, grouped by supply route and priced at this size."""
    by_route: dict[tuple[str | None, str | None], list[ExecutedScopeLine]] = {}
    for r in pool:
        by_route.setdefault(_route(r), []).append(r)

    out = []
    for (supplier, oem), rows in by_route.items():
        per = sorted(_all_in_per_denom(r) for r in rows)
        lo, mid, hi = per[0], median(per), per[-1]
        out.append(
            ComparableGroup(
                route=" · ".join(x for x in (supplier, oem) if x) or "unattributed",
                supplier=supplier,
                oem=oem,
                count=len(rows),
                per_denom_low=round(lo, 2),
                per_denom_mid=round(mid, 2),
                per_denom_high=round(hi, 2),
                unit_low=round(scale(lo), 2),
                unit_mid=round(scale(mid), 2),
                unit_high=round(scale(hi), 2),
                layers={
                    # only these three come from the record; freight and tariff are assumptions
                    "base": round(median([_f(r.base_unit) / (_f(r.size, 1.0) or 1.0) for r in rows]) * size, 2),
                    "services": round(median([_f(r.services_unit) for r in rows]), 2),
                    "tax_pct": round(median([_f(r.tax_pct) for r in rows]), 5),
                },
                comparables=[
                    Comparable(
                        supplier=r.supplier, oem=r.oem, status=r.status, spec=r.spec,
                        size=_f(r.size) if r.size is not None else None,
                        per_denominator=round(_all_in_per_denom(r), 2),
                        base_unit=_f(r.base_unit) if r.base_unit is not None else None,
                        services_unit=_f(r.services_unit) if r.services_unit is not None else None,
                        tax_pct=_f(r.tax_pct) if r.tax_pct is not None else None,
                        source_ref=r.source_ref,
                    )
                    for r in sorted(rows, key=_all_in_per_denom)
                ],
            )
        )
    out.sort(key=lambda g: g.per_denom_mid)
    return out


def _band(
    rows: Sequence[ExecutedScopeLine],
    type_query: str,
    denominator: str,
    size: float,
    qty: int,
    *,
    freight_unit: float = 0.0,
    tariff_pct: float = 0.0,
    escalation_pct: float = 0.0,
) -> RomBand:
    """Turn a corpus slice into a band for one requirement (no DB access)."""

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
        groups=_groups(pool, size, scale),
    )


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
    return _band(
        _comparables(session, type_query, denominator),
        type_query, denominator, size, qty,
        freight_unit=freight_unit, tariff_pct=tariff_pct, escalation_pct=escalation_pct,
    )


def price_many(
    session: Session,
    lines: Sequence[RomBatchLine],
    *,
    freight_unit: float = 0.0,
    tariff_pct: float = 0.0,
    escalation_pct: float = 0.0,
) -> list[RomBand]:
    """Price a line-item list. Returns bands in request order, one per line.

    Tariff and escalation are project-level assumptions and apply to every line;
    freight is per-unit and type-specific, so a line may override it.
    """
    corpus: dict[tuple[str, str], list[ExecutedScopeLine]] = {}
    bands = []
    for line in lines:
        key = (line.type_query, line.denominator)
        if key not in corpus:
            corpus[key] = _comparables(session, *key)
        bands.append(
            _band(
                corpus[key], line.type_query, line.denominator, line.size, line.qty,
                freight_unit=freight_unit if line.freight_unit is None else line.freight_unit,
                tariff_pct=tariff_pct, escalation_pct=escalation_pct,
            )
        )
    return bands


def rollup(bands: Sequence[RomBand]) -> RomRollup:
    """Total a list of bands into the work-in-progress project ROM.

    Unpriced lines (no comparables) contribute nothing to the totals and are counted
    separately — a total that quietly skips lines is worse than one that says so.
    """
    priced = [b for b in bands if b.unit_mid is not None]
    tier_counts = Counter(b.confidence_tier for b in bands)

    def total(attr: str) -> float:
        return round(sum(float(getattr(b, attr) or 0.0) * b.qty for b in priced), 2)

    return RomRollup(
        line_count=len(bands),
        priced_count=len(priced),
        unpriced_count=len(bands) - len(priced),
        total_qty=sum(b.qty for b in bands),
        total_low=total("unit_low"),
        total_mid=total("unit_mid"),
        total_high=total("unit_high"),
        confidence_tier=(
            min((b.confidence_tier for b in bands), key=TIER_ORDER.index) if bands else "none"
        ),
        tier_counts=dict(tier_counts),
    )


def price_demand_lines(
    session: Session, project_id: str, *, only_unpriced: bool = True
) -> tuple[list[DemandLine], RomRollup, int]:
    """Price demand that already exists — the ROM as a byproduct of the record.

    Demand capture answers what is needed and where; this answers what it should cost.
    Two different acts, and pricing is the derived one, so it runs over the record rather
    than sitting inside data entry. That also makes it re-runnable: as the corpus grows,
    the same demand re-prices better.

    Drafted lines only. Frozen demand had its budget captured at freeze, and quietly moving
    that number under someone who already acted on it is not a refresh, it's a surprise.
    """
    stmt = select(DemandLine).where(
        DemandLine.project_id == project_id, DemandLine.state == "drafted"
    )
    if only_unpriced:
        stmt = stmt.where(DemandLine.rom_unit_price.is_(None))
    lines = list(session.scalars(stmt.order_by(DemandLine.created_at)))

    requests: list[RomBatchLine] = []
    priceable: list[DemandLine] = []
    no_physics = 0
    for dl in lines:
        a = dl.spec_attributes or {}
        type_query = str(a.get("type_query") or "").strip()
        if not type_query:
            no_physics += 1  # nothing to price against; the requirement is still real
            continue
        requests.append(
            RomBatchLine(
                type_query=type_query,
                denominator=str(a.get("denominator") or "$/unit"),
                size=float(a.get("size") or 1),
                qty=dl.qty,
            )
        )
        priceable.append(dl)

    bands = price_many(session, requests)
    for dl, band in zip(priceable, bands, strict=True):
        dl.rom_unit_price = band.unit_mid
        dl.rom_confidence = band.confidence_tier
        dl.rom_comparables_count = band.comparables_count
        dl.rom_basis = "mid"  # the default; deviating from it is a Quick price judgment
    session.flush()
    return priceable, rollup(bands), no_physics
