import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import require_token
from app.models import DemandLine, EquipmentType
from app.schemas.demand import (
    DemandLineBatchCreate,
    DemandLineCreate,
    DemandLineRead,
    EquipmentTypeRead,
    FreezeEventRead,
    FreezeRequest,
    ThawEventRead,
    ThawLineRequest,
    ThawRequest,
)
from app.services.freeze import DemandNotFrozen, InvalidTransition, freeze, thaw, thaw_line

router = APIRouter(tags=["demand"], dependencies=[Depends(require_token)])


@router.get("/equipment-types", response_model=list[EquipmentTypeRead])
def list_equipment_types(session: Session = Depends(get_session)) -> list[EquipmentType]:
    return list(session.scalars(select(EquipmentType).order_by(EquipmentType.design_term)))


@router.post("/demand-lines", response_model=DemandLineRead, status_code=201)
def create_demand_line(
    body: DemandLineCreate, session: Session = Depends(get_session)
) -> DemandLine:
    dl = DemandLine(**body.model_dump())
    session.add(dl)
    session.commit()
    session.refresh(dl)
    return dl


@router.post("/demand-lines/batch", response_model=list[DemandLineRead], status_code=201)
def create_demand_lines(
    body: DemandLineBatchCreate, session: Session = Depends(get_session)
) -> list[DemandLine]:
    """Save a whole line-item list as drafted demand — all of it or none of it."""
    dls = [DemandLine(**line.model_dump()) for line in body.lines]
    session.add_all(dls)
    session.commit()
    for dl in dls:
        session.refresh(dl)
    return dls


@router.get("/demand-lines", response_model=list[DemandLineRead])
def list_demand_lines(
    project: str | None = None,
    state: str | None = None,
    session: Session = Depends(get_session),
) -> list[DemandLine]:
    stmt = select(DemandLine)
    if project:
        stmt = stmt.where(DemandLine.project_id == project)
    if state:
        stmt = stmt.where(DemandLine.state == state)
    return list(session.scalars(stmt.order_by(DemandLine.created_at)))


@router.post("/freeze", response_model=FreezeEventRead)
def freeze_lines(body: FreezeRequest, session: Session = Depends(get_session)) -> object:
    try:
        event = freeze(session, body.line_ids, body.project_id, body.scope, body.actor)
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    session.commit()
    session.refresh(event)
    return event


@router.post("/thaw", response_model=ThawEventRead)
def thaw_lines(body: ThawRequest, session: Session = Depends(get_session)) -> object:
    try:
        event = thaw(
            session, body.freeze_event_id, body.line_ids, body.actor,
            body.reason, body.triggering_odd_id,
        )
    except (InvalidTransition, DemandNotFrozen) as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    session.commit()
    session.refresh(event)
    return event


@router.post("/demand-lines/{dl_id}/thaw", response_model=ThawEventRead)
def thaw_one(
    dl_id: uuid.UUID, body: ThawLineRequest, session: Session = Depends(get_session)
) -> object:
    dl = session.get(DemandLine, dl_id)
    if dl is None:
        raise HTTPException(status_code=404, detail="demand line not found")
    try:
        event = thaw_line(session, dl, actor="web", reason=body.reason)
    except (InvalidTransition, ValueError) as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    session.commit()
    session.refresh(event)
    return event
