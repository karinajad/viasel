from pydantic import BaseModel, Field


class RomPriceRequest(BaseModel):
    type_query: str
    denominator: str
    size: float
    qty: int = 1
    freight_unit: float = 0.0
    tariff_pct: float = 0.0
    escalation_pct: float = 0.0


class Comparable(BaseModel):
    """One executed line behind a band — the receipt, not a summary of receipts."""

    supplier: str | None
    oem: str | None
    status: str | None
    spec: str | None
    size: float | None
    per_denominator: float  # its own all-in, normalized — how it compares to the others
    base_unit: float | None
    services_unit: float | None
    tax_pct: float | None
    source_ref: str | None


class ComparableGroup(BaseModel):
    """Comparables sharing a supply route.

    The route matters because it is what drives the spread: a distributor sourcing a
    different OEM is not the same buy as going direct, and averaging the two produces a
    number that describes neither. Grouping also stops the median being decided by which
    route happens to have more rows in the corpus.
    """

    route: str  # "supplier · oem"
    supplier: str | None
    oem: str | None
    count: int
    per_denom_low: float
    per_denom_mid: float
    per_denom_high: float
    unit_low: float  # scaled to the requested size, same adjustments as the band
    unit_mid: float
    unit_high: float
    layers: dict[str, float]  # base · services · tax_pct, from this route's own history
    comparables: list[Comparable]


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

    # the receipts behind the number, grouped by supply route. Freight and tariff are NOT in
    # the corpus — they are assumptions passed in; only base/services/tax come from history.
    groups: list[ComparableGroup] = []


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
