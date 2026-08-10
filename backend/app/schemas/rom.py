from pydantic import BaseModel, Field


class RomPriceRequest(BaseModel):
    type_query: str
    denominator: str
    size: float
    qty: int = 1
    freight_unit: float = 0.0
    tariff_pct: float = 0.0
    escalation_pct: float = 0.0


class RomBand(BaseModel):
    """A ROM price band — a byproduct of the executed record, not a separate estimate."""

    type_query: str
    denominator: str
    size: float
    qty: int

    comparables_count: int
    confidence_tier: str  # high | medium | low | none

    unit_low: float | None
    unit_mid: float | None
    unit_high: float | None
    extended_mid: float | None

    layers: dict[str, float]  # base · services · freight · tariff_pct · tax_pct · escalation_pct
    note: str | None = None


class RomBatchLine(BaseModel):
    """One row of the line-item grid: what it is, how big, how many."""

    type_query: str
    denominator: str
    size: float
    qty: int = 1
    freight_unit: float | None = None  # per-unit override of the batch default


class RomPriceBatchRequest(BaseModel):
    lines: list[RomBatchLine] = Field(min_length=1, max_length=500)
    freight_unit: float = 0.0
    tariff_pct: float = 0.0
    escalation_pct: float = 0.0


class RomRollup(BaseModel):
    """The work-in-progress project ROM — the total that falls out of the line items."""

    line_count: int
    priced_count: int
    unpriced_count: int  # lines with no comparables; they add nothing to the totals
    total_qty: int

    total_low: float
    total_mid: float
    total_high: float

    confidence_tier: str  # the weakest tier present — a total is only as good as its worst line
    tier_counts: dict[str, int]


class RomPriceBatchResponse(BaseModel):
    lines: list[RomBand]  # same order as the request
    rollup: RomRollup
