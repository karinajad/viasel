"""Bid package tests — scoping per equipment, leveling, award fan-out.

Every test rolls back, so the live DB is untouched.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import DemandLine, ScopeLine, Vendor
from app.services.freeze import DemandNotFrozen, freeze
from app.services.packaging import (
    PackagingError,
    add_package_quote,
    award_package,
    bid_layers,
    candidates,
    create_package,
    decline_quote,
    delete_quote,
    detail,
    effective_unit,
    leveling,
    merge_lines,
    move_lines,
    package_lines,
    package_quotes,
    remove_line,
    split_package,
)

PROJECT = "PKGTEST"


# every bid names a firm on the roster — a free-typed vendor is the identity drift that
# makes vendor reliability impossible to accumulate, so the service refuses it
ROSTER = ("Eaton", "Parrish Hare", "Vertiv", "Ambient Enterprises", "Latecomer")


@pytest.fixture
def session() -> Iterator[Session]:
    s = SessionLocal()
    # get-or-create: these tests run against the live database, which has real vendors in it
    have = set(s.scalars(select(Vendor.name).where(Vendor.name.in_(ROSTER))))
    s.add_all(Vendor(name=n) for n in ROSTER if n not in have)
    s.flush()
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


def test_all_in_unit_price_stacks_every_layer_and_amortizes_one_time_cost(session: Session) -> None:
    """Arithmetic checked against the real Cheyenne chiller lot (84 units, winning bid).

    equipment 608,380 + services&freight 29,450 − discount 12,756.60
      + one-time 67,500/84  ==  625,876.97 all-in per unit
      × 84                  ==  52,573,665.60 extended
    """
    lines = [_line(session, size=343, qty=84, building="C1", type_query="Air-Cooled Chiller",
                   denominator="$/ton", rom=771768.0)]
    pkg = create_package(session, PROJECT, [lines[0].id])
    q = add_package_quote(
        session, pkg, "Ambient Enterprises", 608380.0, oem="Dunham Bush", lead_time_weeks=36,
        services_unit=29450.0, discount_unit=12756.60, one_time_cost=67500.0,
    )

    assert round(effective_unit(q, 84), 2) == 625876.97
    layers = bid_layers(q, 84)
    assert layers["equipment"] == 608380.0
    assert layers["discount"] == -12756.60
    assert layers["one_time_amortized"] == round(67500 / 84, 2)
    assert layers["one_time_total"] == 67500.0

    row = leveling(pkg, package_lines(session, pkg), package_quotes(session, pkg))[0]
    assert row.effective_unit == 625876.97
    # extended is built from the unrounded per-unit figure — cents of amortization rounding
    # must not propagate into a lot total
    assert row.extended == 52573665.6  # not unit_price × qty — that would be 51,103,920
    assert row.unit_price == 608380.0  # equipment alone is still visible
    assert row.normalized == round(625876.97 / 343, 2)  # all-in per ton, not equipment per ton


def test_one_time_cost_amortizes_over_the_lot_so_a_smaller_lot_costs_more_per_unit(
    session: Session,
) -> None:
    big = _line(session, size=5000, qty=20, building="C1")
    small = _line(session, size=5000, qty=4, building="C2")
    pkg_big = create_package(session, PROJECT, [big.id])
    pkg_small = create_package(session, PROJECT, [small.id])
    for pkg in (pkg_big, pkg_small):
        add_package_quote(session, pkg, "Eaton", 300000.0, one_time_cost=60000.0)

    q_big = package_quotes(session, pkg_big)[0]
    q_small = package_quotes(session, pkg_small)[0]
    assert effective_unit(q_big, 20) == 303000.0  # 60,000 / 20
    assert effective_unit(q_small, 4) == 315000.0  # 60,000 / 4 — the split-award penalty
    # splitting the 20-unit lot in two would pay the 60,000 layer twice
    assert effective_unit(q_big, 10) * 10 * 2 == pytest.approx(6120000.0)
    assert effective_unit(q_big, 20) * 20 == 6060000.0


def test_a_declined_bid_stays_as_market_data_but_stops_setting_the_benchmark(
    session: Session,
) -> None:
    dl = _line(session, size=343, qty=84, building="C1", rom=700000.0)
    pkg = create_package(session, PROJECT, [dl.id])
    cheap = add_package_quote(session, pkg, "Vertiv", 550053.0)
    compliant = add_package_quote(session, pkg, "Ambient Enterprises", 625877.0)

    decline_quote(session, pkg, cheap, "deviates on power input — 1.44 kW/ton vs 1.05 spec")

    rows = {r.vendor: r for r in leveling(pkg, package_lines(session, pkg), package_quotes(session, pkg))}
    assert rows["Vertiv"].state == "declined"
    assert rows["Vertiv"].disposition_reason is not None and "kW/ton" in rows["Vertiv"].disposition_reason
    assert not rows["Vertiv"].is_low  # ruled out — it no longer sets the benchmark
    assert rows["Ambient Enterprises"].is_low
    # the ruled-out bid shows a negative delta: what compliance is costing
    assert rows["Vertiv"].delta_vs_low == round(550053.0 - 625877.0, 2)
    assert rows["Ambient Enterprises"].delta_vs_low == 0.0

    d = detail(session, pkg)
    assert d.package.quote_count == 1 and d.package.declined_count == 1
    with pytest.raises(PackagingError, match="ruled out"):
        award_package(session, pkg, cheap)
    assert award_package(session, pkg, compliant)


def test_declining_requires_a_reason_and_an_awarded_bid_cannot_be_declined(
    session: Session,
) -> None:
    dl = _line(session, size=5000, qty=12, building="C1")
    pkg = create_package(session, PROJECT, [dl.id])
    q = add_package_quote(session, pkg, "Eaton", 500000.0)
    with pytest.raises(PackagingError, match="requires a stated reason"):
        decline_quote(session, pkg, q, "")
    award_package(session, pkg, q)
    with pytest.raises(PackagingError, match="cannot be declined"):
        decline_quote(session, pkg, q, "changed my mind")


def test_award_commits_the_all_in_price_not_the_equipment_price(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1")
    b = _line(session, size=5000, qty=8, building="C2")
    pkg = create_package(session, PROJECT, [a.id, b.id])
    q = add_package_quote(
        session, pkg, "Parrish Hare", 300000.0,
        services_unit=5000.0, freight_unit=2000.0, one_time_cost=20000.0,
    )
    scope_lines = award_package(session, pkg, q)

    allin = 300000.0 + 5000.0 + 2000.0 + 1000.0  # 20,000 / 20 units
    assert all(sl.unit_price == allin for sl in scope_lines)
    assert detail(session, pkg).package.awarded_extended == allin * 20


def test_lots_combine_when_the_physics_match(session: Session) -> None:
    a = _line(session, size=5000, qty=20, building="C1")
    later = _line(session, size=5000, qty=4, building="C4")  # frozen a week later
    first = create_package(session, PROJECT, [a.id])
    second = create_package(session, PROJECT, [later.id])

    move_lines(session, first, [later.id])

    assert {dl.id for dl in package_lines(session, first)} == {a.id, later.id}
    assert detail(session, first).package.total_qty == 24
    # the emptied lot retires rather than lingering as a ghost
    assert second.state == "cancelled"
    assert package_lines(session, second) == []


def test_a_lot_separates_into_two(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1")
    b = _line(session, size=5000, qty=8, building="C2")
    pkg = create_package(session, PROJECT, [a.id, b.id])

    fresh = split_package(session, pkg, [b.id])

    assert [dl.id for dl in package_lines(session, pkg)] == [a.id]
    assert fresh.id != pkg.id and fresh.code != pkg.code
    assert [dl.id for dl in package_lines(session, fresh)] == [b.id]
    assert pkg.state == "open"  # still has a line, so still live


def test_a_line_of_different_physics_cannot_join_a_lot(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1")
    other = _line(session, size=3250, qty=4, building="C3")
    pkg = create_package(session, PROJECT, [a.id])
    with pytest.raises(PackagingError, match="different physics"):
        move_lines(session, pkg, [other.id])


def test_a_live_bid_blocks_restructuring_until_it_is_dealt_with(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1")
    b = _line(session, size=5000, qty=8, building="C2")
    loose = _line(session, size=5000, qty=4, building="C4")
    pkg = create_package(session, PROJECT, [a.id, b.id])
    q = add_package_quote(session, pkg, "Eaton", 300000.0, one_time_cost=60000.0)

    # the bid was priced against 20 units — changing the lot breaks it
    for op in (
        lambda: move_lines(session, pkg, [loose.id]),
        lambda: split_package(session, pkg, [b.id]),
        lambda: remove_line(session, pkg, b.id),
    ):
        with pytest.raises(PackagingError, match="live bid"):
            op()

    # deleting the bid unblocks it
    delete_quote(session, pkg, q)
    move_lines(session, pkg, [loose.id])
    assert detail(session, pkg).package.total_qty == 24

    # ruling one out works too — a declined bid is history, not a live promise
    q2 = add_package_quote(session, pkg, "Vertiv", 280000.0)
    decline_quote(session, pkg, q2, "lead time misses Phase 1")
    fresh = split_package(session, pkg, [loose.id])
    assert [dl.id for dl in package_lines(session, fresh)] == [loose.id]


def test_the_source_lot_must_also_be_free_to_change(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1")
    b = _line(session, size=5000, qty=8, building="C2")
    keeper = create_package(session, PROJECT, [a.id])
    bid_on = create_package(session, PROJECT, [b.id])
    add_package_quote(session, bid_on, "Eaton", 300000.0)

    # pulling b out of a lot that has a live bid on it breaks that bid too
    with pytest.raises(PackagingError, match=f"{bid_on.code} has 1 live bid"):
        move_lines(session, keeper, [b.id])


def test_splitting_out_every_line_is_refused_as_a_no_op(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1")
    pkg = create_package(session, PROJECT, [a.id])
    with pytest.raises(PackagingError, match="just rename the lot"):
        split_package(session, pkg, [a.id])


def test_an_awarded_bid_can_be_neither_deleted_nor_its_lot_restructured(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1")
    b = _line(session, size=5000, qty=8, building="C2")
    pkg = create_package(session, PROJECT, [a.id, b.id])
    q = add_package_quote(session, pkg, "Eaton", 300000.0)
    award_package(session, pkg, q)

    with pytest.raises(PackagingError, match="part of the commitment"):
        delete_quote(session, pkg, q)
    with pytest.raises(PackagingError, match="scope is committed"):
        split_package(session, pkg, [b.id])


def test_duplicate_lines_in_the_same_place_merge_into_one(session: Session) -> None:
    a = _line(session, size=5000, qty=8, building="C1", rom=300000.0)
    dup = _line(session, size=5000, qty=4, building="C1", rom=300000.0)
    a.target_area = dup.target_area = "C1-DH3"
    session.flush()
    pkg = create_package(session, PROJECT, [a.id, dup.id])
    assert detail(session, pkg).package.line_count == 2

    survivor = merge_lines(session, pkg, [a.id, dup.id])

    assert survivor.qty == 12
    assert survivor.revision == 2  # the consolidation is a revision, not a silent edit
    assert dup.state == "cancelled"
    d = detail(session, pkg)
    assert d.package.line_count == 1 and d.package.total_qty == 12
    assert d.package.rom_extended == 300000.0 * 12  # the lot's value is unchanged


def test_lines_in_different_places_refuse_to_merge(session: Session) -> None:
    a = _line(session, size=5000, qty=12, building="C1")
    b = _line(session, size=5000, qty=8, building="C2")
    pkg = create_package(session, PROJECT, [a.id, b.id])
    with pytest.raises(PackagingError, match="different places"):
        merge_lines(session, pkg, [a.id, b.id])


def test_a_bid_on_the_lot_blocks_a_merge_until_it_is_wiped(session: Session) -> None:
    a = _line(session, size=5000, qty=8, building="C1")
    dup = _line(session, size=5000, qty=4, building="C1")
    pkg = create_package(session, PROJECT, [a.id, dup.id])
    q = add_package_quote(session, pkg, "Eaton", 300000.0, one_time_cost=60000.0)

    with pytest.raises(PackagingError, match="live bid"):
        merge_lines(session, pkg, [a.id, dup.id])

    delete_quote(session, pkg, q)  # wipe it, merge, re-enter the bid
    merge_lines(session, pkg, [a.id, dup.id])
    again = add_package_quote(session, pkg, "Eaton", 300000.0, one_time_cost=60000.0)
    assert effective_unit(again, 12) == 305000.0  # 60,000 over 12 now, not 12 + 4 separately
