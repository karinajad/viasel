"""Demand-line state machine + freeze/thaw + the §37 gate.

Only frozen demand is matchable. Supply can never be committed against demand
that isn't frozen — that rule lives here (`assert_frozen_for_supply`), not as a
generic validation checkbox.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DemandLine, FreezeEvent, ThawEvent

DRAFTED = "drafted"
FROZEN = "frozen"
MATCHING = "matching"
MATCHED = "matched"
SATISFIED = "satisfied"
THAWED = "thawed"
CANCELLED = "cancelled"

VALID_TRANSITIONS: dict[str, set[str]] = {
    DRAFTED: {FROZEN, CANCELLED},
    FROZEN: {MATCHING, THAWED, CANCELLED},
    MATCHING: {MATCHED, THAWED, CANCELLED},
    MATCHED: {SATISFIED, THAWED, CANCELLED},
    SATISFIED: {THAWED, CANCELLED},
    THAWED: {FROZEN, CANCELLED},  # refreeze after revision
    CANCELLED: set(),
}


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str) -> None:
        super().__init__(f"illegal demand-line transition: {frm} -> {to}")
        self.frm, self.to = frm, to


class DemandNotFrozen(Exception):
    def __init__(self, state: str) -> None:
        super().__init__(f"supply requires a frozen demand line (state={state})")
        self.state = state


def transition(dl: DemandLine, to: str) -> None:
    if to not in VALID_TRANSITIONS.get(dl.state, set()):
        raise InvalidTransition(dl.state, to)
    dl.state = to


PROJECT = "project"
BUILDING = "building"
AREA = "area"
SCOPES = (PROJECT, BUILDING, AREA)


class BadScope(Exception):
    """The freeze scope doesn't describe a real slice of the design."""


def scoped_drafted_lines(
    session: Session, project_id: str, scope: str, scope_ref: str | None
) -> list[DemandLine]:
    """Every drafted line the scope covers.

    Freeze is a design-release event over a slice of the design, not a hand-picked set of
    rows — so the scope decides what gets frozen. The axis is the project's location
    legend, because design releases by place. Grouping equipment to buy from one vendor is
    a sourcing decision (bid packages) and has no business in this gate.
    """
    if scope not in SCOPES:
        raise BadScope(f"scope must be one of {', '.join(SCOPES)} — got '{scope}'")
    if scope != PROJECT and not scope_ref:
        raise BadScope(f"a {scope} freeze has to say which {scope}")

    stmt = select(DemandLine).where(
        DemandLine.project_id == project_id, DemandLine.state == DRAFTED
    )
    if scope == BUILDING:
        stmt = stmt.where(DemandLine.target_building == scope_ref)
    elif scope == AREA:
        stmt = stmt.where(DemandLine.target_area == scope_ref)
    return list(session.scalars(stmt.order_by(DemandLine.created_at)))


def freeze(
    session: Session,
    line_ids: list[uuid.UUID],
    project_id: str,
    scope: str,
    actor: str,
    scope_ref: str | None = None,
) -> FreezeEvent:
    """Flip the given demand lines to frozen and record a FreezeEvent snapshot."""
    if scope not in SCOPES:
        raise BadScope(f"scope must be one of {', '.join(SCOPES)} — got '{scope}'")
    if scope != PROJECT and not scope_ref:
        raise BadScope(f"a {scope} freeze has to say which {scope}")
    if not line_ids:
        raise BadScope("nothing drafted in that scope to freeze")
    for dl in session.scalars(select(DemandLine).where(DemandLine.id.in_(line_ids))):
        transition(dl, FROZEN)
    event = FreezeEvent(
        project_id=project_id,
        scope=scope,
        scope_ref=scope_ref,
        demand_line_ids=[str(i) for i in line_ids],
        actor=actor,
    )
    session.add(event)
    session.flush()
    return event


def thaw(
    session: Session,
    freeze_event_id: uuid.UUID,
    line_ids: list[uuid.UUID],
    actor: str,
    reason: str | None = None,
    triggering_odd_id: str | None = None,
) -> ThawEvent:
    """Reopen the given demand lines (frozen -> thawed) and record a ThawEvent."""
    for dl in session.scalars(select(DemandLine).where(DemandLine.id.in_(line_ids))):
        transition(dl, THAWED)
    event = ThawEvent(
        freeze_event_id=freeze_event_id,
        released_line_ids=[str(i) for i in line_ids],
        actor=actor,
        reason=reason,
        triggering_odd_id=triggering_odd_id,
    )
    session.add(event)
    session.flush()
    return event


def assert_frozen_for_supply(dl: DemandLine) -> None:
    """The gate: supply may only be committed against a frozen demand line."""
    if dl.state != FROZEN:
        raise DemandNotFrozen(dl.state)


def thaw_line(session: Session, dl: DemandLine, actor: str, reason: str | None = None) -> ThawEvent:
    """Reopen one demand line by finding the latest freeze event that covers it."""
    events = session.scalars(
        select(FreezeEvent)
        .where(FreezeEvent.project_id == dl.project_id)
        .order_by(FreezeEvent.created_at.desc())
    ).all()
    fe = next((e for e in events if e.demand_line_ids and str(dl.id) in e.demand_line_ids), None)
    if fe is None:
        raise ValueError("no freeze event found for this line")
    transition(dl, THAWED)
    event = ThawEvent(freeze_event_id=fe.id, released_line_ids=[str(dl.id)], actor=actor, reason=reason)
    session.add(event)
    session.flush()
    return event
