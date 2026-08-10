import uuid

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    legend_frozen: bool = False


class LegendActionRequest(BaseModel):
    reason: str | None = None
    actor: str | None = "web"


class LocationCreate(BaseModel):
    code: str
    kind: str = "building"
    label: str | None = None


class LocationUpdate(BaseModel):
    code: str | None = None
    kind: str | None = None
    label: str | None = None


class LocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    code: str
    kind: str
    label: str | None
