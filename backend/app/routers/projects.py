import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import require_token
from app.models import Project, ProjectLocation
from app.schemas.project import LocationCreate, LocationRead, ProjectCreate, ProjectRead

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
            select(ProjectLocation).where(ProjectLocation.project_id == project_id).order_by(ProjectLocation.code)
        )
    )


@router.post("/{project_id}/locations", response_model=LocationRead, status_code=201)
def add_location(project_id: uuid.UUID, body: LocationCreate, session: Session = Depends(get_session)) -> ProjectLocation:
    if session.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")
    loc = ProjectLocation(project_id=project_id, code=body.code, kind=body.kind, label=body.label)
    session.add(loc)
    session.commit()
    session.refresh(loc)
    return loc
