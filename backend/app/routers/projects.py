import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import require_token
from app.models import LegendEvent, Project, ProjectLocation
from app.schemas.project import (
    LegendActionRequest,
    LocationCreate,
    LocationRead,
    LocationUpdate,
    ProjectCreate,
    ProjectRead,
)

router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(require_token)])


@router.get("", response_model=list[ProjectRead])
def list_projects(session: Session = Depends(get_session)) -> list[Project]:
    return list(session.scalars(select(Project).order_by(Project.name)))


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(body: ProjectCreate, session: Session = Depends(get_session)) -> Project:
    existing = session.scalar(select(Project).where(Project.name == body.name))
    if existing:
        return existing
    p = Project(name=body.name)
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


@router.get("/{project_id}/locations", response_model=list[LocationRead])
def list_locations(project_id: uuid.UUID, session: Session = Depends(get_session)) -> list[ProjectLocation]:
    return list(
        session.scalars(
            select(ProjectLocation)
            .where(ProjectLocation.project_id == project_id, ProjectLocation.active.is_(True))
            .order_by(ProjectLocation.code)
        )
    )


@router.post("/{project_id}/locations", response_model=LocationRead, status_code=201)
def add_location(project_id: uuid.UUID, body: LocationCreate, session: Session = Depends(get_session)) -> ProjectLocation:
    _assert_legend_editable(session, project_id)
    loc = ProjectLocation(project_id=project_id, code=body.code, kind=body.kind, label=body.label)
    session.add(loc)
    session.commit()
    session.refresh(loc)
    return loc


def _get_location(session: Session, project_id: uuid.UUID, loc_id: uuid.UUID) -> ProjectLocation:
    loc = session.get(ProjectLocation, loc_id)
    if loc is None or loc.project_id != project_id:
        raise HTTPException(status_code=404, detail="location not found")
    return loc


def _assert_legend_editable(session: Session, project_id: uuid.UUID) -> None:
    proj = session.get(Project, project_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="project not found")
    if proj.legend_frozen:
        raise HTTPException(status_code=409, detail="legend is frozen — thaw with a reason to change codes")


@router.patch("/{project_id}/locations/{loc_id}", response_model=LocationRead)
def update_location(
    project_id: uuid.UUID, loc_id: uuid.UUID, body: LocationUpdate, session: Session = Depends(get_session)
) -> ProjectLocation:
    loc = _get_location(session, project_id, loc_id)
    _assert_legend_editable(session, project_id)
    if body.code is not None:
        loc.code = body.code
    if body.kind is not None:
        loc.kind = body.kind
    if body.label is not None:
        loc.label = body.label
    session.commit()
    session.refresh(loc)
    return loc


@router.delete("/{project_id}/locations/{loc_id}", status_code=204)
def delete_location(project_id: uuid.UUID, loc_id: uuid.UUID, session: Session = Depends(get_session)) -> None:
    loc = _get_location(session, project_id, loc_id)
    _assert_legend_editable(session, project_id)
    loc.active = False  # soft delete — the code stays in the crosswalk forever
    session.commit()


@router.post("/{project_id}/legend/freeze", response_model=ProjectRead)
def freeze_legend(
    project_id: uuid.UUID, body: LegendActionRequest, session: Session = Depends(get_session)
) -> Project:
    proj = session.get(Project, project_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="project not found")
    proj.legend_frozen = True
    session.add(LegendEvent(project_id=project_id, action="freeze", reason=body.reason, actor=body.actor))
    session.commit()
    session.refresh(proj)
    return proj


@router.post("/{project_id}/legend/thaw", response_model=ProjectRead)
def thaw_legend(
    project_id: uuid.UUID, body: LegendActionRequest, session: Session = Depends(get_session)
) -> Project:
    if not body.reason:
        raise HTTPException(status_code=400, detail="a reason is required to thaw the legend")
    proj = session.get(Project, project_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="project not found")
    proj.legend_frozen = False
    session.add(LegendEvent(project_id=project_id, action="thaw", reason=body.reason, actor=body.actor))
    session.commit()
    session.refresh(proj)
    return proj
