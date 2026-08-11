"""API tests via TestClient. Read-only endpoints + a create that cleans up after itself."""

import json
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal
from app.main import app
from app.models import DemandLine

client = TestClient(app, headers={"X-API-Key": settings.API_TOKEN})


def test_requires_api_key() -> None:
    r = TestClient(app).get("/equipment-types")  # no key
    assert r.status_code == 401


def test_rom_price_endpoint() -> None:
    r = client.post(
        "/rom/price",
        json={"type_query": "Transformer", "denominator": "$/kVA", "size": 5000, "qty": 12},
    )
    assert r.status_code == 200
    band = r.json()
    assert band["comparables_count"] > 0
    assert band["unit_mid"] > 0
    assert band["confidence_tier"] in {"high", "medium", "low", "none"}


def test_equipment_types_endpoint() -> None:
    r = client.get("/equipment-types")
    assert r.status_code == 200
    assert isinstance(r.json(), list) and len(r.json()) > 0


def test_create_demand_line_then_cleanup() -> None:
    r = client.post("/demand-lines", json={"project_id": "APITEST", "qty": 2})
    assert r.status_code == 201
    body = r.json()
    assert body["state"] == "drafted"
    created_id = uuid.UUID(body["id"])

    # verify it lists, then delete it so the live DB stays clean
    listed = client.get("/demand-lines", params={"project": "APITEST"})
    assert any(d["id"] == body["id"] for d in listed.json())

    with SessionLocal() as s:
        s.query(DemandLine).filter(DemandLine.id == created_id).delete()
        s.commit()


def test_rom_price_batch_endpoint() -> None:
    r = client.post(
        "/rom/price-batch",
        json={
            "lines": [
                {"type_query": "Transformer", "denominator": "$/kVA", "size": 5000, "qty": 12},
                {"type_query": "Generator", "denominator": "$/kW", "size": 500, "qty": 2},
            ],
            "escalation_pct": 0.05,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["lines"]) == 2
    roll = body["rollup"]
    assert roll["line_count"] == 2 and roll["total_qty"] == 14
    assert roll["total_low"] <= roll["total_mid"] <= roll["total_high"]
    assert roll["confidence_tier"] in {"high", "medium", "low", "none"}


def test_rom_price_batch_rejects_an_empty_list() -> None:
    r = client.post("/rom/price-batch", json={"lines": []})
    assert r.status_code == 422


def test_create_demand_lines_batch_then_cleanup() -> None:
    rows = [
        {
            "project_id": "APIBATCH",
            "qty": q,
            "spec_attributes": {"type_query": "Transformer", "denominator": "$/kVA", "size": 5000},
            "target_building": "C1",
            "rom_unit_price": 500000.0,
        }
        for q in (3, 5)
    ]
    r = client.post("/demand-lines/batch", json={"lines": rows})
    assert r.status_code == 201
    created = r.json()
    assert len(created) == 2
    assert {d["qty"] for d in created} == {3, 5}
    assert all(d["state"] == "drafted" for d in created)
    assert all(d["target_building"] == "C1" for d in created)

    listed = client.get("/demand-lines", params={"project": "APIBATCH"}).json()
    assert len(listed) == 2

    with SessionLocal() as s:
        s.query(DemandLine).filter(DemandLine.project_id == "APIBATCH").delete()
        s.commit()


def test_package_candidates_quote_and_award_then_cleanup() -> None:
    project = "APIPKG"
    spec = {"type_query": "Padmount Transformer", "denominator": "$/kVA", "size": 5000}
    created = client.post(
        "/demand-lines/batch",
        json={
            "lines": [
                {"project_id": project, "qty": 12, "spec_attributes": spec,
                 "target_building": "C1", "rom_unit_price": 300000.0},
                {"project_id": project, "qty": 8, "spec_attributes": spec,
                 "target_building": "C2", "rom_unit_price": 300000.0},
            ]
        },
    ).json()
    ids = [d["id"] for d in created]

    try:
        # nothing is sourceable until it is frozen
        assert client.get("/packages/candidates", params={"project": project}).json()["groups"] == []
        client.post("/freeze", json={"line_ids": ids, "project_id": project, "scope": "project", "actor": "test"})

        cand = client.get("/packages/candidates", params={"project": project}).json()
        assert len(cand["groups"]) == 1
        group = cand["groups"][0]
        assert group["total_qty"] == 20 and group["line_count"] == 2

        r = client.post("/packages", json={"project_id": project, "demand_line_ids": group["demand_line_ids"]})
        assert r.status_code == 201
        pkg = r.json()["package"]
        assert pkg["code"] == "PKG-01" and pkg["total_qty"] == 20
        assert pkg["rom_extended"] == 300000.0 * 20

        # the same lines can't be packaged twice
        again = client.post("/packages", json={"project_id": project, "demand_line_ids": group["demand_line_ids"]})
        assert again.status_code == 409

        client.post(f"/packages/{pkg['id']}/quotes", json={"vendor": "Eaton", "unit_price": 507533.0, "lead_time_weeks": 52})
        d = client.post(
            f"/packages/{pkg['id']}/quotes",
            json={"vendor": "Parrish Hare", "unit_price": 306074.0, "lead_time_weeks": 34},
        ).json()
        rows = d["leveling"]
        assert [x["vendor"] for x in rows] == ["Parrish Hare", "Eaton"]  # leveled, cheapest first
        assert rows[0]["is_low"] and rows[0]["normalized"] == round(306074.0 / 5000, 2)
        assert rows[0]["extended"] == round(306074.0 * 20, 2)

        awarded = client.post(f"/packages/{pkg['id']}/award", json={"quote_id": rows[0]["quote_id"]})
        assert awarded.status_code == 200
        assert sorted(sl["qty"] for sl in awarded.json()) == [8, 12]  # one scope line per unit record

        after = client.get(f"/packages/{pkg['id']}").json()["package"]
        assert after["state"] == "awarded" and after["awarded_vendor"] == "Parrish Hare"
        assert client.post(f"/packages/{pkg['id']}/award", json={"quote_id": rows[0]["quote_id"]}).status_code == 409
        states = [d["state"] for d in client.get("/demand-lines", params={"project": project}).json()]
        assert states == ["matched", "matched"]
    finally:
        with SessionLocal() as s:
            s.execute(
                text(
                    "delete from viasel.scope_line where demand_line_id in"
                    " (select id from viasel.demand_line where project_id = :p)"
                ),
                {"p": project},
            )
            s.execute(
                text(
                    "delete from viasel.quote where sourcing_package_id in"
                    " (select id from viasel.sourcing_package where project_id = :p)"
                ),
                {"p": project},
            )
            s.execute(
                text(
                    "delete from viasel.package_line where sourcing_package_id in"
                    " (select id from viasel.sourcing_package where project_id = :p)"
                ),
                {"p": project},
            )
            s.execute(text("delete from viasel.sourcing_package where project_id = :p"), {"p": project})
            s.execute(text("delete from viasel.freeze_event where project_id = :p"), {"p": project})
            s.execute(text("delete from viasel.demand_line where project_id = :p"), {"p": project})
            s.commit()


def test_rom_basis_off_the_median_requires_a_reason() -> None:
    base = {"project_id": "APIBASIS", "qty": 4, "rom_unit_price": 316599.0}
    try:
        bad = client.post("/demand-lines", json={**base, "rom_basis": "route:Parrish Hare"})
        assert bad.status_code == 422
        assert "needs a stated reason" in json.dumps(bad.json())

        ok = client.post("/demand-lines", json={
            **base, "rom_basis": "route:Parrish Hare", "rom_note": "integrator route on this campus"})
        assert ok.status_code == 201
        assert ok.json()["rom_basis"] == "route:Parrish Hare"
        assert ok.json()["rom_note"] == "integrator route on this campus"

        # the default needs no ceremony
        assert client.post("/demand-lines", json={**base, "rom_basis": "mid"}).status_code == 201
    finally:
        with SessionLocal() as s:
            s.query(DemandLine).filter(DemandLine.project_id == "APIBASIS").delete()
            s.commit()


def test_project_detail_capacity_and_accountability() -> None:
    p = client.post("/projects", json={"name": "APIPROJ"}).json()
    try:
        d = client.patch(f"/projects/{p['id']}", json={
            "site_code": "DTW01", "mw_it": 88, "redundancy": "2N", "cooling": "air-cooled",
            "elevation_ft": 6000, "ambient_max_f": 120, "sound_limit_dba": 70,
        }).json()
        assert d["mw_it"] == 88 and d["redundancy"] == "2N" and d["elevation_ft"] == 6000
        # a partial patch leaves everything it didn't mention alone
        assert client.patch(f"/projects/{p['id']}", json={"city": "Saline"}).json()["site_code"] == "DTW01"
        # the vocabulary is closed, so inference can rely on it
        assert client.patch(f"/projects/{p['id']}", json={"redundancy": "N+7"}).status_code == 400

        # per-building capacity has to add up, or units-per-MW is wrong
        for code, mw in (("C1", 30), ("C2", 30)):
            client.post(f"/projects/{p['id']}/locations", json={"code": code, "kind": "building", "mw_it": mw})
        cap = client.get(f"/projects/{p['id']}/capacity").json()
        assert cap["building_mw_it"] == 60 and cap["project_mw_it"] == 88 and cap["reconciles"] is False
        locs = client.get(f"/projects/{p['id']}/locations").json()
        client.patch(f"/projects/{p['id']}/locations/{locs[0]['id']}", json={"mw_it": 58})
        assert client.get(f"/projects/{p['id']}/capacity").json()["reconciles"] is True

        c = client.post(f"/projects/{p['id']}/contacts",
                        json={"name": "G. Singel", "function": "procurement", "accountability": "accountable"})
        assert c.status_code == 201
        assert client.post(f"/projects/{p['id']}/contacts",
                           json={"name": "X", "function": "vibes"}).status_code == 400
        assert len(client.get(f"/projects/{p['id']}/contacts").json()) == 1
        # removal is soft — who signed off stays on the record
        client.delete(f"/projects/{p['id']}/contacts/{c.json()['id']}")
        assert client.get(f"/projects/{p['id']}/contacts").json() == []
    finally:
        with SessionLocal() as s:
            for table in ("project_contact", "project_location", "legend_event"):
                s.execute(text(f"delete from viasel.{table} where project_id = :i"), {"i": p["id"]})
            s.execute(text("delete from viasel.project where id = :i"), {"i": p["id"]})
            s.commit()


def test_vendor_roster_is_one_record_per_firm_and_gates_bidding() -> None:
    """Free-typed vendor names are why §11 reliability can't accumulate. One record fixes it."""
    ph = client.post("/vendors", json={
        "name": "T-Roster Distributor", "code": "TRD", "role": "distributor",
        "oem_names": ["GE Prolec", "MCI"], "factory_country": "USA", "status": "preferred"}).json()
    oem = client.post("/vendors", json={"name": "T-Roster OEM", "role": "oem"}).json()
    try:
        # the same firm cannot be entered twice under a different casing
        assert client.post("/vendors", json={"name": "t-roster oem"}).status_code == 409
        assert client.post("/vendors", json={"name": "T-Roster X", "role": "wizard"}).status_code == 400
        assert ph["oem_names"] == ["GE Prolec", "MCI"]

        # putting a vendor out of play is a decision, so it carries its reason
        assert client.patch(f"/vendors/{oem['id']}", json={"status": "hold"}).status_code == 400
        client.patch(f"/vendors/{oem['id']}", json={"status": "hold", "status_note": "no capacity"})
        biddable = [v["name"] for v in client.get("/vendors", params={"biddable_only": True}).json()]
        assert "T-Roster Distributor" in biddable and "T-Roster OEM" not in biddable

        c = client.post(f"/vendors/{ph['id']}/contacts", json={"name": "A. Turner", "title": "President"})
        assert c.status_code == 201
        assert client.get(f"/vendors/{ph['id']}").json()["contacts"][0]["name"] == "A. Turner"

        # a bid names a roster vendor, and one on hold is refused with the reason
        line = client.post("/demand-lines/batch", json={"lines": [{
            "project_id": "APIVEND", "qty": 12, "target_building": "C1", "rom_unit_price": 320000.0,
            "spec_attributes": {"type_query": "Padmount Transformer", "denominator": "$/kVA", "size": 5000},
        }]}).json()
        client.post("/freeze", json={"line_ids": [line[0]["id"]], "project_id": "APIVEND",
                                     "scope": "project", "actor": "t"})
        group = client.get("/packages/candidates", params={"project": "APIVEND"}).json()["groups"][0]
        pkg = client.post("/packages", json={"project_id": "APIVEND",
                                             "demand_line_ids": group["demand_line_ids"]}).json()["package"]
        r = client.post(f"/packages/{pkg['id']}/quotes", json={"vendor_id": ph["id"], "unit_price": 306074.0})
        assert r.status_code == 201
        row = r.json()["leveling"][0]
        assert row["vendor"] == "T-Roster Distributor" and row["vendor_id"] == ph["id"]
        assert client.get(f"/vendors/{ph['id']}").json()["bid_count"] == 1

        held = client.post(f"/packages/{pkg['id']}/quotes", json={"vendor_id": oem["id"], "unit_price": 1.0})
        assert held.status_code == 409 and "no capacity" in held.json()["detail"]
    finally:
        with SessionLocal() as s:
            for q in (
                "delete from viasel.scope_line where demand_line_id in (select id from viasel.demand_line where project_id='APIVEND')",
                "delete from viasel.quote where sourcing_package_id in (select id from viasel.sourcing_package where project_id='APIVEND')",
                "delete from viasel.package_line where sourcing_package_id in (select id from viasel.sourcing_package where project_id='APIVEND')",
                "delete from viasel.sourcing_package where project_id='APIVEND'",
                "delete from viasel.freeze_event where project_id='APIVEND'",
                "delete from viasel.demand_line where project_id='APIVEND'",
                "delete from viasel.vendor_contact where vendor_id in (select id from viasel.vendor where name like 'T-Roster%')",
                "delete from viasel.vendor where name like 'T-Roster%'",
            ):
                s.execute(text(q))
            s.commit()
