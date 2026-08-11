"""Bid packages — scoping the buy per equipment, and leveling the bids against it.

You don't buy one transformer at one hall; you buy every transformer of that size on the
project as a lot. A package is that lot: frozen demand lines pooled on **physics**
(type + denominator + size), quoted once per vendor, leveled per the natural denominator,
awarded to one vendor — which fans a scope line out to every unit's own record.

Pooling is strict by design: same type, same size. Mixing sizes in one lot would mean a
single vendor number standing in for two different physical things.

The §37 gate holds all the way through: every line in a package must be frozen when the
package is formed, when a bid is taken, and when it is awarded.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DemandLine, PackageLine, Quote, ScopeLine, SourcingPackage
from app.schemas.packaging import (
    CandidateGroup,
    CandidatesRead,
    LevelingRow,
    PackageDetail,
    PackageLineRead,
    PackageRead,
)
from app.services.freeze import FROZEN, MATCHED, MATCHING, assert_frozen_for_supply, transition

OPEN = "open"
AWARDED = "awarded"
CANCELLED = "cancelled"

RECEIVED = "received"
SELECTED = "selected"
DECLINED = "declined"

PoolKey = tuple[str, str, float]


class PackagingError(Exception):
    """A packaging rule was broken — surfaced as 409."""


def pool_key(dl: DemandLine) -> PoolKey | None:
    """The physics identity a line pools on. None when the line has no physics captured."""
    a = dl.spec_attributes or {}
    type_query = str(a.get("type_query") or "").strip()
    if not type_query:
        return None
    return (type_query, str(a.get("denominator") or "$/unit"), float(a.get("size") or 1))


def _f(x: object, default: float = 0.0) -> float:
    return float(x) if x is not None else default  # type: ignore[arg-type]


def _rom_extended(lines: Sequence[DemandLine]) -> float | None:
    """What the record already says this lot should cost — the ROM to bid against."""
    priced = [dl for dl in lines if dl.rom_unit_price is not None]
    return round(sum(_f(dl.rom_unit_price) * dl.qty for dl in priced), 2) if priced else None


def packaged_line_ids(session: Session, project_id: str) -> set[uuid.UUID]:
    """Demand lines already sitting in an active package."""
    return set(
        session.scalars(
            select(PackageLine.demand_line_id)
            .join(SourcingPackage, SourcingPackage.id == PackageLine.sourcing_package_id)
            .where(SourcingPackage.project_id == project_id, PackageLine.active.is_(True))
        )
    )


def package_lines(session: Session, pkg: SourcingPackage) -> list[DemandLine]:
    return list(
        session.scalars(
            select(DemandLine)
            .join(PackageLine, PackageLine.demand_line_id == DemandLine.id)
            .where(
                PackageLine.sourcing_package_id == pkg.id,
                PackageLine.active.is_(True),
            )
            .order_by(DemandLine.target_building, DemandLine.target_area)
        )
    )


def candidates(session: Session, project_id: str) -> CandidatesRead:
    """The project's frozen, unpackaged demand grouped into the lots it should be bought as."""
    already = packaged_line_ids(session, project_id)
    lines = [
        dl
        for dl in session.scalars(
            select(DemandLine).where(
                DemandLine.project_id == project_id, DemandLine.state == FROZEN
            )
        )
        if dl.id not in already
    ]

    groups: dict[PoolKey, list[DemandLine]] = {}
    unpoolable = 0
    for dl in lines:
        key = pool_key(dl)
        if key is None:
            unpoolable += 1
            continue
        groups.setdefault(key, []).append(dl)

    out = [
        CandidateGroup(
            type_query=key[0],
            denominator=key[1],
            size=key[2],
            line_count=len(dls),
            total_qty=sum(dl.qty for dl in dls),
            rom_extended=_rom_extended(dls),
            buildings=sorted({dl.target_building for dl in dls if dl.target_building}),
            demand_line_ids=[dl.id for dl in dls],
        )
        for key, dls in groups.items()
    ]
    out.sort(key=lambda g: (-g.total_qty, g.type_query))
    return CandidatesRead(project_id=project_id, groups=out, unpoolable_count=unpoolable)


def _next_code(session: Session, project_id: str) -> str:
    n = len(
        list(
            session.scalars(
                select(SourcingPackage.id).where(SourcingPackage.project_id == project_id)
            )
        )
    )
    return f"PKG-{n + 1:02d}"


def create_package(
    session: Session, project_id: str, demand_line_ids: Sequence[uuid.UUID]
) -> SourcingPackage:
    """Form a lot from frozen demand lines that share one physics identity."""
    lines = list(session.scalars(select(DemandLine).where(DemandLine.id.in_(demand_line_ids))))
    found = {dl.id for dl in lines}
    missing = [str(i) for i in demand_line_ids if i not in found]
    if missing:
        raise PackagingError(f"demand lines not found: {', '.join(missing)}")

    wrong_project = [dl for dl in lines if dl.project_id != project_id]
    if wrong_project:
        raise PackagingError("every line in a package must belong to the same project")

    for dl in lines:
        assert_frozen_for_supply(dl)  # the gate — only frozen demand is sourceable

    keys = {pool_key(dl) for dl in lines}
    if None in keys:
        raise PackagingError("a line with no equipment type captured cannot be packaged")
    if len(keys) > 1:
        raise PackagingError(
            "a package is one equipment type at one size — these lines differ: "
            + "; ".join(sorted(f"{k[0]} {k[2]:g}{k[1].replace('$/', ' ')}" for k in keys if k))
        )

    already = packaged_line_ids(session, project_id) & found
    if already:
        raise PackagingError(f"{len(already)} of these lines are already in an open package")

    key = next(iter(keys))
    assert key is not None  # narrowed above
    type_query, denominator, size = key
    etype_ids = {dl.equipment_type_id for dl in lines if dl.equipment_type_id}
    pkg = SourcingPackage(
        project_id=project_id,
        code=_next_code(session, project_id),
        equipment_type_id=next(iter(etype_ids)) if len(etype_ids) == 1 else None,
        type_query=type_query,
        denominator=denominator,
        size=size,
    )
    session.add(pkg)
    session.flush()
    session.add_all(
        PackageLine(sourcing_package_id=pkg.id, demand_line_id=dl.id) for dl in lines
    )
    session.flush()
    return pkg


def remove_line(session: Session, pkg: SourcingPackage, demand_line_id: uuid.UUID) -> None:
    """Drop a line from an open package. Soft — the package's history stays intact."""
    if pkg.state != OPEN:
        raise PackagingError(f"package {pkg.code} is {pkg.state} — its scope is committed")
    pl = session.scalar(
        select(PackageLine).where(
            PackageLine.sourcing_package_id == pkg.id,
            PackageLine.demand_line_id == demand_line_id,
            PackageLine.active.is_(True),
        )
    )
    if pl is None:
        raise PackagingError("that line is not in this package")
    pl.active = False
    session.flush()


def add_package_quote(
    session: Session,
    pkg: SourcingPackage,
    vendor: str,
    unit_price: float,
    *,
    oem: str | None = None,
    lead_time_weeks: int | None = None,
    terms_note: str | None = None,
    services_unit: float | None = None,
    freight_unit: float | None = None,
    discount_unit: float | None = None,
    one_time_cost: float | None = None,
) -> Quote:
    """Take a vendor's bid for the whole lot: equipment per unit, plus its cost layers."""
    if pkg.state != OPEN:
        raise PackagingError(f"package {pkg.code} is {pkg.state} — bidding is closed")
    lines = package_lines(session, pkg)
    if not lines:
        raise PackagingError(f"package {pkg.code} has no lines to bid on")
    for dl in lines:
        assert_frozen_for_supply(dl)  # the gate, again — demand may have thawed since
    q = Quote(
        sourcing_package_id=pkg.id, vendor=vendor, unit_price=unit_price, oem=oem,
        lead_time_weeks=lead_time_weeks, denominator=pkg.denominator, size=pkg.size,
        terms_note=terms_note, services_unit=services_unit, freight_unit=freight_unit,
        discount_unit=discount_unit, one_time_cost=one_time_cost,
    )
    session.add(q)
    session.flush()
    return q


def decline_quote(session: Session, pkg: SourcingPackage, quote: Quote, reason: str) -> Quote:
    """Rule a bid out, on the record. It stays as market data — a price you rejected is
    as informative as a price you paid — but it no longer sets the benchmark."""
    if quote.sourcing_package_id != pkg.id:
        raise PackagingError("that quote is not a bid on this package")
    if quote.state == SELECTED:
        raise PackagingError("that bid was awarded — it cannot be declined")
    if not reason:
        raise PackagingError("ruling a bid out requires a stated reason")
    quote.state = DECLINED
    quote.disposition_reason = reason
    session.flush()
    return quote


def package_quotes(session: Session, pkg: SourcingPackage) -> list[Quote]:
    return list(
        session.scalars(
            select(Quote)
            .where(Quote.sourcing_package_id == pkg.id)
            .order_by(Quote.unit_price)
        )
    )


def award_package(
    session: Session, pkg: SourcingPackage, quote: Quote
) -> list[ScopeLine]:
    """Commit the lot to one vendor — a scope line per unit record, matched to its demand."""
    if pkg.state != OPEN:
        raise PackagingError(f"package {pkg.code} is already {pkg.state}")
    if quote.sourcing_package_id != pkg.id:
        raise PackagingError("that quote is not a bid on this package")
    if quote.state == DECLINED:
        raise PackagingError(
            f"that bid was ruled out ({quote.disposition_reason}) — reinstate it to award it"
        )
    lines = package_lines(session, pkg)
    if not lines:
        raise PackagingError(f"package {pkg.code} has no lines to award")

    # every unit's scope line carries the all-in price for this lot size, not the
    # equipment price — the one-time layer is real money and it belongs on the commitment
    allin = round(effective_unit(quote, sum(dl.qty for dl in lines)), 2)
    scope_lines = []
    for dl in lines:
        assert_frozen_for_supply(dl)
        sl = ScopeLine(
            demand_line_id=dl.id, quote_id=quote.id, vendor=quote.vendor,
            unit_price=allin, qty=dl.qty,
        )
        session.add(sl)
        transition(dl, MATCHING)
        transition(dl, MATCHED)
        scope_lines.append(sl)

    quote.state = SELECTED
    pkg.state = AWARDED
    session.flush()
    return scope_lines


def _read(session: Session, pkg: SourcingPackage, lines: Sequence[DemandLine], quotes: Sequence[Quote]) -> PackageRead:
    selected = next((q for q in quotes if q.state == SELECTED), None)
    total_qty = sum(dl.qty for dl in lines)
    rom_ext = _rom_extended(lines)
    return PackageRead(
        id=pkg.id,
        code=pkg.code,
        project_id=pkg.project_id,
        type_query=pkg.type_query,
        denominator=pkg.denominator,
        size=_f(pkg.size),
        state=pkg.state,
        created_at=pkg.created_at,
        line_count=len(lines),
        total_qty=total_qty,
        rom_unit_price=round(rom_ext / total_qty, 2) if rom_ext and total_qty else None,
        rom_extended=rom_ext,
        quote_count=len([q for q in quotes if q.state != DECLINED]),
        declined_count=len([q for q in quotes if q.state == DECLINED]),
        awarded_vendor=selected.vendor if selected else None,
        awarded_extended=(
            round(effective_unit(selected, total_qty) * total_qty, 2) if selected else None
        ),
    )


def bid_layers(q: Quote, total_qty: int) -> dict[str, float]:
    """What a bid actually costs per unit, layer by layer.

    Equipment is only the first layer. Services/freight/discount are per unit; a one-time
    cost (factory witness test, owner's training) is per ORDER, so it amortizes over the
    lot — which is exactly why splitting a lot between two vendors costs more than the
    unit prices suggest: you pay the one-time layer twice.
    """
    return {
        "equipment": round(_f(q.unit_price), 2),
        "services": round(_f(q.services_unit), 2),
        "freight": round(_f(q.freight_unit), 2),
        "discount": round(-_f(q.discount_unit), 2),
        "one_time_amortized": round(_f(q.one_time_cost) / total_qty, 2) if total_qty else 0.0,
        "one_time_total": round(_f(q.one_time_cost), 2),
    }


def effective_unit(q: Quote, total_qty: int) -> float:
    """All-in per unit for this lot size — unrounded.

    Deliberately not rounded: amortizing a one-time cost rarely divides evenly, and
    rounding here before extending would push cents of error into a multi-million-dollar
    lot total. Round for display, extend from this.
    """
    return (
        _f(q.unit_price) + _f(q.services_unit) + _f(q.freight_unit) - _f(q.discount_unit)
        + (_f(q.one_time_cost) / total_qty if total_qty else 0.0)
    )


def leveling(
    pkg: SourcingPackage, lines: Sequence[DemandLine], quotes: Sequence[Quote]
) -> list[LevelingRow]:
    """Bid leveling: every bid on the same footing — all-in, per denominator, vs. the ROM.

    Three things have to be true before bids compare. Every layer is counted (equipment
    alone is not the price). The result is normalized to the natural denominator. And it's
    set against what the executed record says the lot should cost.

    Declined bids stay in the table — a bid you ruled out is still market data — but they
    don't set the benchmark, so `delta_vs_low` measures against the cheapest *awardable*
    bid. A ruled-out bid cheaper than that shows a negative delta: the price of compliance.
    """
    if not quotes:
        return []
    total_qty = sum(dl.qty for dl in lines)
    size = _f(pkg.size, 1.0) or 1.0
    rom_ext = _rom_extended(lines)
    rom_unit = rom_ext / total_qty if rom_ext and total_qty else None

    allin = {q.id: effective_unit(q, total_qty) for q in quotes}
    live = [q for q in quotes if q.state != DECLINED]
    low = min((allin[q.id] for q in live), default=min(allin.values()))

    rows = []
    for q in quotes:
        unit = allin[q.id]
        rows.append(
            LevelingRow(
                quote_id=q.id,
                vendor=q.vendor,
                oem=q.oem,
                unit_price=round(_f(q.unit_price), 2),
                effective_unit=round(unit, 2),
                layers=bid_layers(q, total_qty),
                normalized=round(unit / size, 2),
                lead_time_weeks=q.lead_time_weeks,
                terms_note=q.terms_note,
                state=q.state,
                disposition_reason=q.disposition_reason,
                extended=round(unit * total_qty, 2),
                delta_vs_low=round(unit - low, 2),
                delta_vs_low_pct=round((unit - low) / low, 4) if low else None,
                delta_vs_rom=round(unit - rom_unit, 2) if rom_unit else None,
                delta_vs_rom_pct=round((unit - rom_unit) / rom_unit, 4) if rom_unit else None,
                is_low=unit == low and q.state != DECLINED,
                is_selected=q.state == SELECTED,
            )
        )
    rows.sort(key=lambda r: r.effective_unit)
    return rows


def detail(session: Session, pkg: SourcingPackage) -> PackageDetail:
    lines = package_lines(session, pkg)
    quotes = package_quotes(session, pkg)
    return PackageDetail(
        package=_read(session, pkg, lines, quotes),
        lines=[
            PackageLineRead(
                demand_line_id=dl.id,
                qty=dl.qty,
                target_building=dl.target_building,
                target_area=dl.target_area,
                state=dl.state,
                rom_unit_price=_f(dl.rom_unit_price) if dl.rom_unit_price is not None else None,
            )
            for dl in lines
        ],
        leveling=leveling(pkg, lines, quotes),
    )


def list_packages(session: Session, project_id: str) -> list[PackageRead]:
    pkgs = session.scalars(
        select(SourcingPackage)
        .where(SourcingPackage.project_id == project_id)
        .order_by(SourcingPackage.code)
    )
    return [_read(session, p, package_lines(session, p), package_quotes(session, p)) for p in pkgs]
