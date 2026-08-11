"""ROM engine tests against the seeded executed corpus (read-only)."""

from app.db import SessionLocal
from app.schemas.rom import RomBatchLine
from app.services.rom import price, price_many, rollup


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


def test_batch_prices_a_line_item_list_and_rolls_up() -> None:
    lines = [
        RomBatchLine(type_query="Transformer", denominator="$/kVA", size=5000, qty=12),
        RomBatchLine(type_query="Transformer", denominator="$/kVA", size=3250, qty=4),
        RomBatchLine(type_query="Zorptron 9000", denominator="$/kW", size=100, qty=2),
    ]
    with SessionLocal() as s:
        bands = price_many(s, lines)
    roll = rollup(bands)

    # one band per row, in request order, and size carried through
    assert len(bands) == 3
    assert [b.size for b in bands] == [5000, 3250, 100]
    # the batch agrees line-for-line with the single-line engine
    with SessionLocal() as s:
        one = price(s, type_query="Transformer", denominator="$/kVA", size=3250, qty=4)
    assert bands[1].unit_mid == one.unit_mid

    # rollup: the unpriced row is counted, not silently absorbed
    assert roll.line_count == 3 and roll.priced_count == 2 and roll.unpriced_count == 1
    assert roll.total_qty == 18
    assert roll.total_low <= roll.total_mid <= roll.total_high
    expected_mid = sum((b.unit_mid or 0) * b.qty for b in bands)
    assert abs(roll.total_mid - expected_mid) < 1.0
    # a total is only as good as its weakest line — one 'none' drags the tier down
    assert roll.confidence_tier == "none"
    print(
        f"\nline-item ROM ({roll.line_count} rows, {roll.total_qty} units): "
        f"${roll.total_low:,.0f} – ${roll.total_mid:,.0f} – ${roll.total_high:,.0f} "
        f"({roll.confidence_tier}; {roll.unpriced_count} unpriced)"
    )


def test_batch_scales_project_assumptions_across_every_line() -> None:
    lines = [
        RomBatchLine(type_query="Transformer", denominator="$/kVA", size=5000, qty=1),
        RomBatchLine(type_query="Transformer", denominator="$/kVA", size=5000, qty=1, freight_unit=1000),
    ]
    with SessionLocal() as s:
        plain = price_many(s, lines)
        escalated = price_many(s, lines, escalation_pct=0.10)

    assert plain[0].unit_mid is not None and escalated[0].unit_mid is not None
    assert abs(escalated[0].unit_mid - plain[0].unit_mid * 1.10) < 1.0
    # the per-line freight override applies only to its own line
    assert plain[1].unit_mid == (plain[0].unit_mid or 0) + 1000


def test_rollup_of_nothing_is_honest() -> None:
    roll = rollup([])
    assert roll.line_count == 0 and roll.total_mid == 0.0
    assert roll.confidence_tier == "none"


def test_comparables_are_grouped_by_supply_route() -> None:
    """The 5000kVA transformer band is two populations, not one.

    Six distributor lines sit within 5% of each other; two direct-from-OEM lines are 1.6x
    higher. The median is therefore decided by which route has more rows in the corpus —
    which is why the groups have to be visible and selectable.
    """
    with SessionLocal() as s:
        band = price(s, type_query="Transformer", denominator="$/kVA", size=5000, qty=12)

    assert len(band.groups) >= 2
    # cheapest route first, and every comparable is accounted for
    assert band.groups == sorted(band.groups, key=lambda g: g.per_denom_mid)
    assert sum(g.count for g in band.groups) == band.comparables_count

    routes = {g.route: g for g in band.groups}
    ph = next(g for r, g in routes.items() if "Parrish" in r)
    eaton = next(g for r, g in routes.items() if "Eaton" in r)

    # each route is tighter than the band that averages them
    assert ph.per_denom_high / ph.per_denom_low < 1.1
    assert eaton.per_denom_mid > ph.per_denom_high * 1.5
    # only history-backed layers per group — freight and tariff are assumptions, not record
    assert set(ph.layers) == {"base", "services", "tax_pct"}
    # the receipts are attached, cheapest first
    assert [c.per_denominator for c in ph.comparables] == sorted(c.per_denominator for c in ph.comparables)
    assert all(c.supplier == ph.supplier for c in ph.comparables)


def test_a_band_with_no_comparables_has_no_groups() -> None:
    with SessionLocal() as s:
        band = price(s, type_query="Zorptron 9000", denominator="$/kW", size=100, qty=1)
    assert band.groups == []
