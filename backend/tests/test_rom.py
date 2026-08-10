"""ROM engine tests against the seeded executed corpus (read-only)."""

from app.db import SessionLocal
from app.services.rom import price


def test_prices_a_transformer_from_history() -> None:
    with SessionLocal() as s:
        band = price(s, type_query="Transformer", denominator="$/kVA", size=5000, qty=12)

    assert band.comparables_count >= 2
    assert band.unit_mid is not None
    assert band.unit_low is not None and band.unit_high is not None
    assert band.unit_mid > 0
    # band brackets the mid (the spread reflects real vendor differences)
    assert band.unit_low <= band.unit_mid <= band.unit_high
    # extended is per-unit mid times quantity (within rounding)
    assert band.extended_mid is not None
    assert abs(band.extended_mid - band.unit_mid * 12) < 1.0
    # the layers are present and the denominator carried through
    assert "base" in band.layers and band.denominator == "$/kVA"
    print(
        f"\n5000kVA transformer ×12: "
        f"${band.unit_low:,.0f} – ${band.unit_mid:,.0f} – ${band.unit_high:,.0f}/unit "
        f"({band.confidence_tier}, {band.comparables_count} comparables)"
    )


def test_no_comparables_falls_back_honestly() -> None:
    with SessionLocal() as s:
        band = price(s, type_query="Zorptron 9000", denominator="$/kW", size=100, qty=1)

    assert band.comparables_count == 0
    assert band.confidence_tier == "none"
    assert band.unit_mid is None
    assert band.note and "fall back" in band.note
