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
    lead_time_weeks: int | None  # what design assumed for this line


class LevelingRow(BaseModel):
    """One bid, on the same footing as every other bid on the lot."""

    quote_id: uuid.UUID
    vendor: str
    vendor_id: uuid.UUID | None
    oem: str | None
    unit_price: float  # equipment only — not what the unit costs
    effective_unit: float  # all-in for this lot size, one-time cost amortized
    layers: dict[str, float]  # equipment · services · freight · discount · one_time_amortized
    normalized: float  # all-in per denominator unit — what compares across vendors
    lead_time_weeks: int | None
    terms_note: str | None
    state: str  # received | selected | declined
    disposition_reason: str | None

    extended: float  # the whole lot at this bid
    delta_vs_low: float  # against the cheapest *awardable* bid
    delta_vs_low_pct: float | None
    delta_vs_rom: float | None  # against what the executed record says the lot should cost
    delta_vs_rom_pct: float | None
    # the vendor's lead time against what design assumed: negative is time won back
    delta_vs_design_lead: int | None

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
    design_lead_weeks: int | None  # the longest design assumption in the lot — the binding one
    quote_count: int  # live bids
    declined_count: int
    awarded_vendor: str | None
    awarded_extended: float | None


class PackageDetail(BaseModel):
    package: PackageRead
    lines: list[PackageLineRead]
    leveling: list[LevelingRow]  # cheapest first


class PackageQuoteCreate(BaseModel):
    vendor: str | None = None  # free text, when the roster doesn't have them yet
    vendor_id: uuid.UUID | None = None  # preferred: a vendor from the roster
    unit_price: float  # equipment, per unit
    oem: str | None = None
    lead_time_weeks: int | None = None
    terms_note: str | None = None
    # cost layers — per unit, except one_time_cost which is per order
    services_unit: float | None = None  # startup · commissioning · IST · warranty
    freight_unit: float | None = None
    discount_unit: float | None = None  # positive = subtracted
    one_time_cost: float | None = None  # factory witness test · owner's training


class PackageAwardRequest(BaseModel):
    quote_id: uuid.UUID


class PackageLinesRequest(BaseModel):
    """Whole demand lines to move into, or split out of, a lot."""

    demand_line_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class QuoteDeclineRequest(BaseModel):
    reason: str = Field(min_length=1)  # ruling a bid out requires a stated reason
