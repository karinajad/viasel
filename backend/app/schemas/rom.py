from pydantic import BaseModel


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
