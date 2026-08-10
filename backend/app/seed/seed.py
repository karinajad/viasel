"""Seed the canonical taxonomy + sample executed prices from rom_seed/ into the DB.

Idempotent: clears the two seed tables, then reloads. Run:
    PYTHONPATH=. .venv/bin/python -m app.seed.seed
"""

import csv
from pathlib import Path

from app.db import SessionLocal
from app.models import EquipmentType, ExecutedScopeLine

ROM_SEED = Path(__file__).resolve().parents[3] / "rom_seed"


def _num(x: str | None) -> float | None:
    if x is None:
        return None
    x = x.strip().replace(",", "").replace("$", "").replace("%", "")
    try:
        return float(x)
    except ValueError:
        return None


def run() -> None:
    session = SessionLocal()
    try:
        # idempotent reload
        session.query(ExecutedScopeLine).delete()
        session.query(EquipmentType).delete()

        with (ROM_SEED / "equipment_types_canonical.csv").open() as f:
            types = [
                EquipmentType(
                    design_term=r["design_term"],
                    unit_type_code=r["unit_type_code"],
                    sub_type=r["sub_type"] or None,
                    natural_denominator=r["natural_denominator"],
                )
                for r in csv.DictReader(f)
            ]
        session.add_all(types)

        with (ROM_SEED / "executed_scope_lines.csv").open() as f:
            lines = [
                ExecutedScopeLine(
                    etype=r.get("etype") or None,
                    spec=r.get("spec") or None,
                    designation=r.get("designation") or None,
                    supplier=r.get("supplier") or None,
                    oem=r.get("oem") or None,
                    qty=_num(r.get("qty")),
                    status=r.get("status") or None,
                    denominator=r.get("denominator") or None,
                    size=_num(r.get("size")),
                    base_unit=_num(r.get("base_unit")),
                    services_unit=_num(r.get("services_unit")),
                    tax_pct=_num(r.get("tax_pct")),
                    normalized=_num(r.get("normalized")),
                    allin_reported=_num(r.get("allin_reported")),
                    source_ref=r.get("sheet") or None,
                )
                for r in csv.DictReader(f)
            ]
        session.add_all(lines)
        session.commit()
        print(f"seeded: {len(types)} equipment_type, {len(lines)} executed_scope_line")
    finally:
        session.close()


if __name__ == "__main__":
    run()
