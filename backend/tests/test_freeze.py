"""Freeze state machine + gate tests. Each test runs in a transaction that is
rolled back, so the live DB is never polluted."""

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import DemandLine
from app.services.freeze import (
    DemandNotFrozen,
    InvalidTransition,
    assert_frozen_for_supply,
    freeze,
    thaw,
    transition,
)


@pytest.fixture
def session() -> Iterator[Session]:
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


def _draft(s: Session) -> DemandLine:
    dl = DemandLine(project_id="TEST", qty=1, state="drafted")
    s.add(dl)
    s.flush()
    return dl


def test_illegal_transition_rejected(session: Session) -> None:
    dl = _draft(session)
    with pytest.raises(InvalidTransition):
        transition(dl, "matched")  # can't skip straight from drafted to matched


def test_gate_blocks_unfrozen_then_allows_frozen(session: Session) -> None:
    dl = _draft(session)
    with pytest.raises(DemandNotFrozen):
        assert_frozen_for_supply(dl)  # drafted -> refused
    freeze(session, [dl.id], "TEST", "project", "tester")
    assert dl.state == "frozen"
    assert_frozen_for_supply(dl)  # frozen -> allowed (no raise)


def test_thaw_then_refreeze_preserves_history(session: Session) -> None:
    dl = _draft(session)
    fe = freeze(session, [dl.id], "TEST", "project", "tester")
    assert dl.state == "frozen"

    te = thaw(session, fe.id, [dl.id], "tester", reason="ODD-1")
    assert dl.state == "thawed"
    with pytest.raises(DemandNotFrozen):
        assert_frozen_for_supply(dl)  # thawed lines drop out of the match

    freeze(session, [dl.id], "TEST", "project", "tester")  # refreeze after revision
    assert dl.state == "frozen"

    # the events survive — the record is what was frozen, when, and what thawed it
    assert fe.id is not None
    assert te.freeze_event_id == fe.id
    assert te.released_line_ids == [str(dl.id)]
