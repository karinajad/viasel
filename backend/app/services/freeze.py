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


def freeze(
    session: Session, line_ids: list[uuid.UUID], project_id: str, scope: str, actor: str
) -> FreezeEvent:
    """Flip the given demand lines to frozen and record a FreezeEvent snapshot."""
    for dl in session.scalars(select(DemandLine).where(DemandLine.id.in_(line_ids))):
        transition(dl, FROZEN)
    event = FreezeEvent(
        project_id=project_id,
        scope=scope,
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
