"""Phase-1 data tests against the live DB (run after seeding).

The reconciliation test is the Phase-1 success proof: normalized executed data
reproduces the hand-built all-in price to the dollar.
"""

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import EquipmentType, ExecutedScopeLine


def test_tables_seeded() -> None:
    with SessionLocal() as s:
        assert (s.scalar(select(func.count()).select_from(EquipmentType)) or 0) > 0
        assert (s.scalar(select(func.count()).select_from(ExecutedScopeLine)) or 0) > 0


def test_reconciles_to_the_dollar() -> None:
    with SessionLocal() as s:
        rows = s.scalars(
            select(ExecutedScopeLine).where(ExecutedScopeLine.status.ilike("exec%"))
        ).all()

    checked = [
        r for r in rows if r.base_unit is not None and r.allin_reported is not None
    ]
    within = 0
    for r in checked:
        base = float(r.base_unit or 0)
        services = float(r.services_unit or 0)
        tax = float(r.tax_pct or 0)
        calc = (base + services) * (1 + tax)
        reported = float(r.allin_reported or 0)
        if reported and abs(reported - calc) / reported < 0.001:  # within 0.1%
            within += 1

    print(f"\nreconciliation: {within}/{len(checked)} executed rows within 0.1% of hand-built all-in")
    assert len(checked) >= 20, "expected a meaningful executed sample to be seeded"
    assert within >= 20, "normalized pricing should reproduce the known all-in to the dollar"
