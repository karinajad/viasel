import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import require_token
from app.models import Agreement
from app.schemas.agreement import (
    AgreementCreate,
    AgreementRead,
    AgreementRelease,
    ExecutedAgreementCreate,
    ExecutedAgreementRead,
    ExhibitItemCreate,
    ExhibitItemRead,
    ExhibitSet,
    ReconciliationRead,
)
from app.services.agreements import (
    RELEASED,
    AgreementError,
    add_exhibit_item,
    create_agreement,
    exhibits,
    list_agreements,
    read,
    reconciliation,
    register_executed,
    remove_exhibit_item,
    transition,
)

router = APIRouter(prefix="/agreements", tags=["agreements"], dependencies=[Depends(require_token)])


def _agreement(session: Session, ag_id: uuid.UUID) -> Agreement:
    ag = session.get(Agreement, ag_id)
    if ag is None:
        raise HTTPException(status_code=404, detail="agreement not found")
    return ag


def _conflict(e: Exception) -> HTTPException:
    return HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=list[AgreementRead])
def get_agreements(project: str, session: Session = Depends(get_session)) -> list[AgreementRead]:
    return list_agreements(session, project)


@router.post("", response_model=AgreementRead, status_code=201)
def post_agreement(body: AgreementCreate, session: Session = Depends(get_session)) -> AgreementRead:
    """Raise an agreement over awarded lots. Its scope is the record's, not retyped."""
    try:
        ag = create_agreement(
            session, body.project_id, body.package_ids,
            code=body.code, agreement_type=body.agreement_type,
        )
    except AgreementError as e:
        raise _conflict(e) from e
    session.commit()
    return read(session, ag)


@router.get("/{ag_id}", response_model=AgreementRead)
def get_agreement(ag_id: uuid.UUID, session: Session = Depends(get_session)) -> AgreementRead:
    return read(session, _agreement(session, ag_id))


@router.get("/{ag_id}/exhibits", response_model=ExhibitSet)
def get_exhibits(ag_id: uuid.UUID, session: Session = Depends(get_session)) -> ExhibitSet:
    """The exhibits, generated from the record — a view, never an attachment."""
    return exhibits(session, _agreement(session, ag_id))


@router.post("/{ag_id}/release", response_model=AgreementRead)
def post_release(
    ag_id: uuid.UUID, body: AgreementRelease, session: Session = Depends(get_session)
) -> AgreementRead:
    """Hand the exhibit data over for signature. Signing happens in the client's own system."""
    ag = _agreement(session, ag_id)
    try:
        transition(session, ag, RELEASED, released_date=body.released_date)
    except AgreementError as e:
        raise _conflict(e) from e
    session.commit()
    return read(session, ag)


@router.post("/{ag_id}/executed", response_model=ExecutedAgreementRead, status_code=201)
def post_executed(
    ag_id: uuid.UUID, body: ExecutedAgreementCreate, session: Session = Depends(get_session)
) -> ExecutedAgreementRead:
    """Register the signed version — where it lives, and what it says — and reconcile it."""
    ag = _agreement(session, ag_id)
    try:
        ex = register_executed(session, ag, **body.model_dump())
    except AgreementError as e:
        raise _conflict(e) from e
    session.commit()
    session.refresh(ex)
    return ExecutedAgreementRead.model_validate(ex)


@router.get("/{ag_id}/reconciliation", response_model=ReconciliationRead | None)
def get_reconciliation(
    ag_id: uuid.UUID, session: Session = Depends(get_session)
) -> ReconciliationRead | None:
    """What the signed document says against what the record generated."""
    return reconciliation(session, _agreement(session, ag_id))


@router.post("/{ag_id}/exhibit-items", response_model=ExhibitItemRead, status_code=201)
def post_exhibit_item(
    ag_id: uuid.UUID, body: ExhibitItemCreate, session: Session = Depends(get_session)
) -> ExhibitItemRead:
    """Enter a line of an exhibit the record can't derive, against the scope it covers."""
    ag = _agreement(session, ag_id)
    try:
        item = add_exhibit_item(session, ag, **body.model_dump())
    except AgreementError as e:
        raise _conflict(e) from e
    session.commit()
    session.refresh(item)
    return ExhibitItemRead.model_validate(item)


@router.delete("/{ag_id}/exhibit-items/{item_id}", status_code=204)
def delete_exhibit_item(
    ag_id: uuid.UUID, item_id: uuid.UUID, session: Session = Depends(get_session)
) -> None:
    ag = _agreement(session, ag_id)
    try:
        remove_exhibit_item(session, ag, item_id)
    except AgreementError as e:
        raise _conflict(e) from e
    session.commit()
