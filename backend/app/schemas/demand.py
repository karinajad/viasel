import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    # captured ROM result (the calculator's output becomes the demand line's budget)
    rom_unit_price: float | None = None
    rom_confidence: str | None = None
    rom_comparables_count: int | None = None
    rom_basis: str | None = None  # mid | low | high | route:<name>
    rom_note: str | None = None

    @model_validator(mode="after")
    def _basis_off_default_needs_a_reason(self) -> "DemandLineCreate":
        # same house rule as thawing a freeze or ruling out a bid: departing from the
        # default is allowed, silently departing from it is not
        if self.rom_basis and self.rom_basis != "mid" and not (self.rom_note or "").strip():
            raise ValueError(
                f"a ROM taken at '{self.rom_basis}' instead of the median needs a stated reason"
            )
        return self


class DemandLineBatchCreate(BaseModel):
    """The line-item grid saved in one shot — every row becomes drafted demand."""

    lines: list[DemandLineCreate] = Field(min_length=1, max_length=500)


class DemandLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: str
    qty: int
    state: str
    revision: int
    equipment_type_id: uuid.UUID | None
    spec_attributes: dict | None
    target_building: str | None
    target_area: str | None
    target_position: str | None
    required_by_date: date | None
    rom_unit_price: float | None
    rom_confidence: str | None
    rom_basis: str | None
    rom_note: str | None
    created_at: datetime


class FreezeRequest(BaseModel):
    project_id: str
    scope: str = "project"  # project | building | area — the project's location legend
    scope_ref: str | None = None  # which building/area; not needed for a project freeze
    actor: str


class FreezeScopePreview(BaseModel):
    """What a freeze at this scope would cover, before committing to it."""

    scope: str
    scope_ref: str | None
    line_count: int
    total_qty: int
    rom_extended: float | None
    demand_line_ids: list[uuid.UUID]


class ThawRequest(BaseModel):
    freeze_event_id: uuid.UUID
    line_ids: list[uuid.UUID]
    actor: str
    reason: str | None = None
    triggering_odd_id: str | None = None


class ThawLineRequest(BaseModel):
    reason: str | None = None


class FreezeEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: str
    scope: str
    scope_ref: str | None
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
