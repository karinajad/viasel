"""Sourcing — quotes against frozen demand, and award (frozen demand → committed supply).

The §37 gate finally does its job here: you can only solicit/award against a frozen
demand line. Award creates a scope line matched to the demand and moves it to matched.
"""

from sqlalchemy.orm import Session

from app.models import DemandLine, Quote, ScopeLine
from app.services.freeze import MATCHED, MATCHING, assert_frozen_for_supply, transition


def add_quote(
    session: Session,
    dl: DemandLine,
    vendor: str,
    unit_price: float,
    *,
    oem: str | None = None,
    lead_time_weeks: int | None = None,
    denominator: str | None = None,
    size: float | None = None,
    terms_note: str | None = None,
) -> Quote:
    assert_frozen_for_supply(dl)  # can only solicit against frozen demand
    q = Quote(
        demand_line_id=dl.id, vendor=vendor, unit_price=unit_price, oem=oem,
        lead_time_weeks=lead_time_weeks, denominator=denominator, size=size, terms_note=terms_note,
    )
    session.add(q)
    session.flush()
    return q


def award(session: Session, dl: DemandLine, quote: Quote) -> ScopeLine:
    assert_frozen_for_supply(dl)  # the gate: no supply against unfrozen demand
    sl = ScopeLine(
        demand_line_id=dl.id, quote_id=quote.id, vendor=quote.vendor,
        unit_price=quote.unit_price, qty=dl.qty,
    )
    session.add(sl)
    quote.state = "selected"
    transition(dl, MATCHING)
    transition(dl, MATCHED)
    session.flush()
    return sl
