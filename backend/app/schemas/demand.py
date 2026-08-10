import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class EquipmentTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    design_term: str
    unit_type_code: str
    sub_type: str | None
    natural_denominator: str


class DemandLineCreate(BaseModel):
    project_id: str
    qty: int
    equipment_type_id: uuid.UUID | None = None
    spec_attributes: dict | None = None
    target_building: str | None = None
    target_area: str | None = None
    target_position: str | None = None
    required_by_date: date | None = None


class DemandLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: str
    qty: int
    state: str
    revision: int
    equipment_type_id: uuid.UUID | None
    target_building: str | None
    target_area: str | None
    target_position: str | None
    required_by_date: date | None
    rom_unit_price: float | None
    rom_confidence: str | None
    created_at: datetime


class FreezeRequest(BaseModel):
    line_ids: list[uuid.UUID]
    project_id: str
    scope: str  # project | building | system
    actor: str


class ThawRequest(BaseModel):
    freeze_event_id: uuid.UUID
    line_ids: list[uuid.UUID]
    actor: str
    reason: str | None = None
    triggering_odd_id: str | None = None


class FreezeEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: str
    scope: str
    demand_line_ids: list | None
    actor: str | None
    created_at: datetime


class ThawEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    freeze_event_id: uuid.UUID
    released_line_ids: list | None
    actor: str | None
    reason: str | None
    created_at: datetime
