import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import require_token
from app.models import LegendEvent, Project, ProjectContact, ProjectLocation
from app.schemas.project import (
    ACCOUNTABILITY,
    COOLING,
    FUNCTIONS,
    REDUNDANCY,
    CapacityCheck,
    ContactCreate,
    ContactRead,
    LegendActionRequest,
    LocationCreate,
    LocationRead,
    LocationUpdate,
    ProjectCreate,
    ProjectDetail,
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


def _one_of(value: str | None, allowed: tuple[str, ...], field: str) -> None:
    if value is not None and value not in allowed:
        raise HTTPException(
            status_code=400, detail=f"{field} must be one of {', '.join(allowed)} — got '{value}'"
        )


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: uuid.UUID, session: Session = Depends(get_session)) -> Project:
    return _project(session, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: uuid.UUID, body: ProjectDetail, session: Session = Depends(get_session)
) -> Project:
    """Fill in what makes the project inferable. Only what's sent is changed."""
    proj = _project(session, project_id)
    _one_of(body.redundancy, REDUNDANCY, "redundancy")
    _one_of(body.cooling, COOLING, "cooling")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(proj, field, value)
    session.commit()
    session.refresh(proj)
    return proj


@router.get("/{project_id}/capacity", response_model=CapacityCheck)
def project_capacity(project_id: uuid.UUID, session: Session = Depends(get_session)) -> CapacityCheck:
    """Whether the buildings account for the project's stated capacity."""
    proj = _project(session, project_id)
    buildings = list(
        session.scalars(
            select(ProjectLocation).where(
                ProjectLocation.project_id == project_id,
                ProjectLocation.kind == "building",
                ProjectLocation.active.is_(True),
            )
        )
    )
    stated = [b for b in buildings if b.mw_it is not None]
    total = round(sum(float(b.mw_it or 0) for b in stated), 3)
    project_mw = float(proj.mw_it) if proj.mw_it is not None else None
    return CapacityCheck(
        project_mw_it=project_mw,
        building_mw_it=total,
        buildings_with_capacity=len(stated),
        buildings_total=len(buildings),
        reconciles=(
            project_mw is not None
            and len(stated) == len(buildings)
            and len(buildings) > 0
            and abs(total - project_mw) < 0.01
        ),
    )


@router.get("/{project_id}/contacts", response_model=list[ContactRead])
def list_contacts(project_id: uuid.UUID, session: Session = Depends(get_session)) -> list[ProjectContact]:
    return list(
        session.scalars(
            select(ProjectContact)
            .where(ProjectContact.project_id == project_id, ProjectContact.active.is_(True))
            .order_by(ProjectContact.function, ProjectContact.name)
        )
    )


@router.post("/{project_id}/contacts", response_model=ContactRead, status_code=201)
def add_contact(
    project_id: uuid.UUID, body: ContactCreate, session: Session = Depends(get_session)
) -> ProjectContact:
    _project(session, project_id)
    _one_of(body.function, FUNCTIONS, "function")
    _one_of(body.accountability, ACCOUNTABILITY, "accountability")
    c = ProjectContact(project_id=project_id, **body.model_dump())
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


@router.delete("/{project_id}/contacts/{contact_id}", status_code=204)
def delete_contact(
    project_id: uuid.UUID, contact_id: uuid.UUID, session: Session = Depends(get_session)
) -> None:
    c = session.get(ProjectContact, contact_id)
    if c is None or c.project_id != project_id:
        raise HTTPException(status_code=404, detail="contact not found")
    c.active = False  # soft — who signed off stays on the record
    session.commit()


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
    loc = ProjectLocation(project_id=project_id, **body.model_dump())
    session.add(loc)
    session.commit()
    session.refresh(loc)
    return loc


def _get_location(session: Session, project_id: uuid.UUID, loc_id: uuid.UUID) -> ProjectLocation:
    loc = session.get(ProjectLocation, loc_id)
    if loc is None or loc.project_id != project_id:
        raise HTTPException(status_code=404, detail="location not found")
    return loc


def _project(session: Session, project_id: uuid.UUID) -> Project:
    proj = session.get(Project, project_id)
    if proj is None:
        raise HTTPException(status_code=404, detail="project not found")
    return proj


def _assert_legend_editable(session: Session, project_id: uuid.UUID) -> None:
    proj = _project(session, project_id)
    if proj.legend_frozen:
        raise HTTPException(status_code=409, detail="legend is frozen — thaw with a reason to change codes")


@router.patch("/{project_id}/locations/{loc_id}", response_model=LocationRead)
def update_location(
    project_id: uuid.UUID, loc_id: uuid.UUID, body: LocationUpdate, session: Session = Depends(get_session)
) -> ProjectLocation:
    loc = _get_location(session, project_id, loc_id)
    patch = body.model_dump(exclude_unset=True)
    # the legend freeze exists so codes can't drift. `code` and `kind` are the crosswalk keys
    # and stay locked; a building's capacity and label are attributes of it, not identity, and
    # refining them doesn't move a code — so the freeze has no business blocking them.
    if any(k in patch for k in ("code", "kind")):
        _assert_legend_editable(session, project_id)
    for field, value in patch.items():
        setattr(loc, field, value)
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
