"""Sourcing service tests — each rolls back, so the live DB is untouched."""

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import DemandLine
from app.services.freeze import DemandNotFrozen, freeze
from app.services.sourcing import add_quote, award


@pytest.fixture
def session() -> Iterator[Session]:
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


def _frozen_line(s: Session) -> DemandLine:
    dl = DemandLine(project_id="SRCTEST", qty=10, state="drafted")
    s.add(dl)
    s.flush()
    freeze(s, [dl.id], "SRCTEST", "project", "tester")
    return dl


def test_cannot_quote_unfrozen_demand(session: Session) -> None:
    dl = DemandLine(project_id="SRCTEST", qty=1, state="drafted")
    session.add(dl)
    session.flush()
    with pytest.raises(DemandNotFrozen):
        add_quote(session, dl, "Eaton", 100.0)


def test_quote_and_award_moves_to_matched(session: Session) -> None:
    dl = _frozen_line(session)
    q1 = add_quote(session, dl, "GE Prolec", 283909.0, lead_time_weeks=40)
    add_quote(session, dl, "Eaton", 454429.0, lead_time_weeks=52)

    sl = award(session, dl, q1)
    assert dl.state == "matched"
    assert sl.vendor == "GE Prolec"
    assert sl.qty == 10  # inherited from the demand line
    assert q1.state == "selected"
