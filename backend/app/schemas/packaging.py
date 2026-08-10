import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CandidateGroup(BaseModel):
    """Frozen demand that should be bought as one lot — the buy the project implies."""

    type_query: str
    denominator: str
    size: float
    line_count: int
    total_qty: int
    rom_extended: float | None
    buildings: list[str]
    demand_line_ids: list[uuid.UUID]


class CandidatesRead(BaseModel):
    project_id: str
    groups: list[CandidateGroup]
    unpoolable_count: int  # frozen lines with no equipment type captured — can't be pooled


class PackageCreate(BaseModel):
    project_id: str
    demand_line_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class PackageLineRead(BaseModel):
    demand_line_id: uuid.UUID
    qty: int
    target_building: str | None
    target_area: str | None
    state: str
    rom_unit_price: float | None


class LevelingRow(BaseModel):
    """One bid, on the same footing as every other bid on the lot."""

    quote_id: uuid.UUID
    vendor: str
    oem: str | None
    unit_price: float
    normalized: float  # per denominator unit — the only number that compares across vendors
    lead_time_weeks: int | None
    terms_note: str | None
    state: str

    extended: float  # the whole lot at this bid
    delta_vs_low: float
    delta_vs_low_pct: float | None
    delta_vs_rom: float | None  # against what the executed record says the lot should cost
    delta_vs_rom_pct: float | None

    is_low: bool
    is_selected: bool


class PackageRead(BaseModel):
    id: uuid.UUID
    code: str
    project_id: str
    type_query: str
    denominator: str
    size: float
    state: str  # open | awarded | cancelled
    created_at: datetime

    line_count: int
    total_qty: int
    rom_unit_price: float | None
    rom_extended: float | None
    quote_count: int
    awarded_vendor: str | None
    awarded_extended: float | None


class PackageDetail(BaseModel):
    package: PackageRead
    lines: list[PackageLineRead]
    leveling: list[LevelingRow]  # cheapest first


class PackageQuoteCreate(BaseModel):
    vendor: str
    unit_price: float
    oem: str | None = None
    lead_time_weeks: int | None = None
    terms_note: str | None = None


class PackageAwardRequest(BaseModel):
    quote_id: uuid.UUID
