"""Freeze state machine + gate tests. Each test runs in a transaction that is
rolled back, so the live DB is never polluted."""

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import DemandLine
from app.services.freeze import (
    BadScope,
    DemandNotFrozen,
    InvalidTransition,
    assert_frozen_for_supply,
    freeze,
    scoped_drafted_lines,
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


def test_scope_selects_the_lines_instead_of_trusting_a_handpicked_list() -> None:
    """The scope axis is the project's location legend — design releases by place."""
    with SessionLocal() as s:
        made = [
            DemandLine(project_id="SCOPETEST", qty=q, state="drafted",
                       target_building=b, target_area=a, rom_unit_price=1000.0)
            for q, b, a in [(12, "C1", "C1-DH3"), (8, "C1", "C1-DH4"), (4, "C2", None)]
        ]
        s.add_all(made)
        s.flush()
        try:
            whole = scoped_drafted_lines(s, "SCOPETEST", "project", None)
            assert sum(dl.qty for dl in whole) == 24

            c1 = scoped_drafted_lines(s, "SCOPETEST", "building", "C1")
            assert sum(dl.qty for dl in c1) == 20 and len(c1) == 2

            hall = scoped_drafted_lines(s, "SCOPETEST", "area", "C1-DH3")
            assert [dl.qty for dl in hall] == [12]

            # a building freeze that doesn't say which building isn't a scope
            with pytest.raises(BadScope, match="which building"):
                scoped_drafted_lines(s, "SCOPETEST", "building", None)
            # 'system' is gone — grouping equipment for one vendor is a sourcing concern
            with pytest.raises(BadScope, match="must be one of"):
                scoped_drafted_lines(s, "SCOPETEST", "system", "Electrical")

            # freezing C1 leaves C2 drafted, and the event records which building
            event = freeze(s, [dl.id for dl in c1], "SCOPETEST", "building", "tester", scope_ref="C1")
            assert event.scope == "building" and event.scope_ref == "C1"
            assert event.demand_line_ids is not None and len(event.demand_line_ids) == 2
            assert [dl.state for dl in made] == ["frozen", "frozen", "drafted"]
            assert scoped_drafted_lines(s, "SCOPETEST", "project", None)[0].target_building == "C2"
        finally:
            s.rollback()


def test_freezing_an_empty_scope_is_refused() -> None:
    with SessionLocal() as s, pytest.raises(BadScope, match="nothing drafted"):
        freeze(s, [], "SCOPETEST", "building", "tester", scope_ref="C9")
