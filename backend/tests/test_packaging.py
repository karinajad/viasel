"""Bid package tests — scoping per equipment, leveling, award fan-out.

Every test rolls back, so the live DB is untouched.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import DemandLine, ScopeLine
from app.services.freeze import DemandNotFrozen, freeze
from app.services.packaging import (
    PackagingError,
    add_package_quote,
    award_package,
    candidates,
    create_package,
    detail,
    leveling,
    package_lines,
    package_quotes,
    remove_line,
)

PROJECT = "PKGTEST"


@pytest.fixture
def session() -> Iterator[Session]:
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


def _line(
    s: Session, *, size: float, qty: int, building: str, rom: float | None = None,
    type_query: str = "Padmount Transformer", denominator: str = "$/kVA", frozen: bool = True,
) -> DemandLine:
    dl = DemandLine(
        project_id=PROJECT, qty=qty, state="drafted", target_building=building,
        rom_unit_price=rom,
        spec_attributes={"type_query": type_query, "denominator": denominator, "size": size},
    )
    s.add(dl)
    s.flush()
    if frozen:
        freeze(s, [dl.id], PROJECT, "project", "tester")
    return dl


def test_candidates_group_the_buy_by_physics(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1")
    b = _line(session, size=5000, qty=8, building="C2")
    c = _line(session, size=3250, qty=4, building="C3")
    _line(session, size=2000, qty=6, building="C1", type_query="UPS", denominator="$/kW")

    got = candidates(session, PROJECT)
    by_key = {(g.type_query, g.size): g for g in got.groups}

    # same type at the same size pools across buildings; a different size is its own lot
    xfmr5000 = by_key[("Padmount Transformer", 5000)]
    assert xfmr5000.line_count == 2 and xfmr5000.total_qty == 20
    assert set(xfmr5000.demand_line_ids) == {a.id, b.id}
    assert xfmr5000.buildings == ["C1", "C2"]
    assert by_key[("Padmount Transformer", 3250)].demand_line_ids == [c.id]
    assert ("UPS", 2000) in by_key
    assert len(got.groups) == 3
    # biggest lot first — that's the buy worth scoping
    assert got.groups[0].total_qty == 20


def test_candidates_skip_drafted_demand_and_count_the_unpoolable(session: Session) -> None:
    _line(session, size=5000, qty=12, building="C1")
    _line(session, size=5000, qty=3, building="C2", frozen=False)  # not frozen — not sourceable
    bare = DemandLine(project_id=PROJECT, qty=2, state="drafted")  # no physics captured
    session.add(bare)
    session.flush()
    freeze(session, [bare.id], PROJECT, "project", "tester")

    got = candidates(session, PROJECT)
    assert sum(g.total_qty for g in got.groups) == 12
    assert got.unpoolable_count == 1


def test_strict_pooling_rejects_mixed_sizes(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1")
    b = _line(session, size=3250, qty=4, building="C3")
    with pytest.raises(PackagingError, match="one equipment type at one size"):
        create_package(session, PROJECT, [a.id, b.id])


def test_only_frozen_demand_can_be_packaged(session: Session) -> None:
    dl = _line(session, size=5000, qty=12, building="C1", frozen=False)
    with pytest.raises(DemandNotFrozen):
        create_package(session, PROJECT, [dl.id])


def test_a_line_cannot_sit_in_two_open_packages(session: Session) -> None:
    dl = _line(session, size=5000, qty=12, building="C1")
    create_package(session, PROJECT, [dl.id])
    with pytest.raises(PackagingError, match="already in an open package"):
        create_package(session, PROJECT, [dl.id])


def test_a_line_with_no_physics_cannot_be_packaged(session: Session) -> None:
    bare = DemandLine(project_id=PROJECT, qty=2, state="drafted")
    session.add(bare)
    session.flush()
    freeze(session, [bare.id], PROJECT, "project", "tester")
    with pytest.raises(PackagingError, match="no equipment type captured"):
        create_package(session, PROJECT, [bare.id])


def test_removing_a_line_returns_it_to_the_candidate_pool(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1")
    b = _line(session, size=5000, qty=8, building="C2")
    pkg = create_package(session, PROJECT, [a.id, b.id])
    assert candidates(session, PROJECT).groups == []

    remove_line(session, pkg, b.id)
    assert [dl.id for dl in package_lines(session, pkg)] == [a.id]
    back = candidates(session, PROJECT)
    assert back.groups[0].demand_line_ids == [b.id]  # sourceable again


def test_leveling_normalizes_the_bids_and_sets_them_against_the_rom(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1", rom=300000.0)
    b = _line(session, size=5000, qty=8, building="C2", rom=300000.0)
    pkg = create_package(session, PROJECT, [a.id, b.id])
    add_package_quote(session, pkg, "Eaton", 507533.0, lead_time_weeks=52)
    add_package_quote(session, pkg, "Parrish Hare", 306074.0, lead_time_weeks=34)

    rows = leveling(pkg, package_lines(session, pkg), package_quotes(session, pkg))
    assert [r.vendor for r in rows] == ["Parrish Hare", "Eaton"]  # cheapest first
    low, high = rows

    # the only number that compares across vendors: price per denominator unit
    assert low.normalized == round(306074.0 / 5000, 2)
    assert low.is_low and not high.is_low
    # the whole lot at each bid — 20 units, not one
    assert low.extended == round(306074.0 * 20, 2)
    assert low.delta_vs_low == 0.0
    assert high.delta_vs_low == round(507533.0 - 306074.0, 2)
    assert high.delta_vs_low_pct is not None and high.delta_vs_low_pct > 0.6
    # and against what the executed record said the lot should cost
    assert low.delta_vs_rom == round(306074.0 - 300000.0, 2)
    assert high.delta_vs_rom is not None and high.delta_vs_rom > low.delta_vs_rom


def test_award_fans_a_scope_line_out_to_every_unit_record(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1", rom=300000.0)
    b = _line(session, size=5000, qty=8, building="C2", rom=300000.0)
    pkg = create_package(session, PROJECT, [a.id, b.id])
    winner = add_package_quote(session, pkg, "Parrish Hare", 306074.0, lead_time_weeks=34)
    add_package_quote(session, pkg, "Eaton", 507533.0)

    scope_lines = award_package(session, pkg, winner)

    # one scope line per demand line, each carrying its own quantity
    assert len(scope_lines) == 2
    assert {sl.qty for sl in scope_lines} == {12, 8}
    assert all(sl.vendor == "Parrish Hare" and sl.unit_price == 306074.0 for sl in scope_lines)
    assert {sl.demand_line_id for sl in scope_lines} == {a.id, b.id}
    # every unit's own record is matched — the package is the vehicle, not the record
    assert a.state == "matched" and b.state == "matched"
    assert winner.state == "selected"
    assert pkg.state == "awarded"

    d = detail(session, pkg)
    assert d.package.awarded_vendor == "Parrish Hare"
    assert d.package.awarded_extended == round(306074.0 * 20, 2)
    assert d.package.rom_extended == 300000.0 * 20
    assert session.query(ScopeLine).filter(ScopeLine.quote_id == winner.id).count() == 2


def test_an_awarded_package_is_closed_to_further_bids_and_awards(session: Session) -> None:
    dl = _line(session, size=5000, qty=12, building="C1")
    pkg = create_package(session, PROJECT, [dl.id])
    q = add_package_quote(session, pkg, "Eaton", 500000.0)
    award_package(session, pkg, q)

    with pytest.raises(PackagingError, match="bidding is closed"):
        add_package_quote(session, pkg, "Latecomer", 1.0)
    with pytest.raises(PackagingError, match="already awarded"):
        award_package(session, pkg, q)
    with pytest.raises(PackagingError, match="scope is committed"):
        remove_line(session, pkg, dl.id)


def test_a_quote_from_another_package_cannot_win_this_one(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1")
    b = _line(session, size=3250, qty=4, building="C3")
    p1 = create_package(session, PROJECT, [a.id])
    p2 = create_package(session, PROJECT, [b.id])
    q2 = add_package_quote(session, p2, "Eaton", 200000.0)
    with pytest.raises(PackagingError, match="not a bid on this package"):
        award_package(session, p1, q2)
