import uuid

from pydantic import BaseModel, ConfigDict

REDUNDANCY = ("N", "N+1", "2N", "2N+1")
COOLING = ("air-cooled", "liquid", "hybrid")
FUNCTIONS = (
    "procurement", "electrical design", "mechanical design",
    "schedule", "cost", "program", "commissioning",
)
ACCOUNTABILITY = ("accountable", "responsible", "consulted", "informed")


class ProjectCreate(BaseModel):
    name: str


class ProjectDetail(BaseModel):
    """Everything about a project that lets history be inferred onto it. All optional —
    a project is usable the moment it has a name, and gets sharper as this fills in."""

    site_code: str | None = None
    buyer_entity: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    mw_it: float | None = None
    redundancy: str | None = None
    cooling: str | None = None
    elevation_ft: int | None = None
    ambient_max_f: int | None = None
    sound_limit_dba: int | None = None


class ProjectRead(ProjectDetail):
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
    mw_it: float | None = None


class LocationUpdate(BaseModel):
    code: str | None = None
    kind: str | None = None
    label: str | None = None
    mw_it: float | None = None


class LocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    code: str
    kind: str
    label: str | None
    mw_it: float | None


class ContactCreate(BaseModel):
    name: str
    function: str
    accountability: str = "responsible"
    org: str | None = None
    email: str | None = None


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    function: str
    accountability: str
    org: str | None
    email: str | None


class CapacityCheck(BaseModel):
    """Does the per-building capacity add up to the project's? A quiet mismatch here makes
    every units-per-MW inference wrong, so it is surfaced rather than left to be noticed."""

    project_mw_it: float | None
    building_mw_it: float  # sum of the buildings that state one
    buildings_with_capacity: int
    buildings_total: int
    reconciles: bool
