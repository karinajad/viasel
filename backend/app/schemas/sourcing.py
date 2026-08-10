import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QuoteCreate(BaseModel):
    vendor: str
    unit_price: float
    oem: str | None = None
    lead_time_weeks: int | None = None
    denominator: str | None = None
    size: float | None = None
    terms_note: str | None = None


class QuoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    demand_line_id: uuid.UUID
    vendor: str
    oem: str | None
    unit_price: float
    lead_time_weeks: int | None
    denominator: str | None
    size: float | None
    terms_note: str | None
    state: str
    created_at: datetime


class AwardRequest(BaseModel):
    quote_id: uuid.UUID


class ScopeLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    demand_line_id: uuid.UUID
    quote_id: uuid.UUID | None
    vendor: str
    unit_price: float
    qty: int
    change_type: str
    created_at: datetime
