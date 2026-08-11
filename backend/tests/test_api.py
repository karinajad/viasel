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

        # bids name firms on the roster — a free-typed vendor is refused
        assert client.post(f"/packages/{pkg['id']}/quotes",
                           json={"vendor": "Nobody Ltd", "unit_price": 1.0}).status_code == 409
        eaton = client.post("/vendors", json={"name": "T-Cand Eaton", "code": "TCE"}).json()
        ph = client.post("/vendors", json={"name": "T-Cand PH", "code": "TCP"}).json()
        client.post(f"/packages/{pkg['id']}/quotes",
                    json={"vendor_id": eaton["id"], "unit_price": 507533.0, "lead_time_weeks": 52})
        d = client.post(f"/packages/{pkg['id']}/quotes",
                        json={"vendor_id": ph["id"], "unit_price": 306074.0, "lead_time_weeks": 34}).json()
        rows = d["leveling"]
        assert [x["vendor"] for x in rows] == ["T-Cand PH", "T-Cand Eaton"]  # leveled, cheapest first
        assert rows[0]["is_low"] and rows[0]["normalized"] == round(306074.0 / 5000, 2)
        assert rows[0]["extended"] == round(306074.0 * 20, 2)

        awarded = client.post(f"/packages/{pkg['id']}/award", json={"quote_id": rows[0]["quote_id"]})
        assert awarded.status_code == 200
        assert sorted(sl["qty"] for sl in awarded.json()) == [8, 12]  # one scope line per unit record

        after = client.get(f"/packages/{pkg['id']}").json()["package"]
        assert after["state"] == "awarded" and after["awarded_vendor"] == "T-Cand PH"
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
            s.execute(text("delete from viasel.vendor where name like 'T-Cand%'"))
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


def test_legend_freeze_locks_codes_not_capacity() -> None:
    """The freeze exists so codes can't drift. A building's MW is an attribute, not identity."""
    p = client.post("/projects", json={"name": "APIFROZEN"}).json()
    try:
        client.patch(f"/projects/{p['id']}", json={"mw_it": 40})
        for code in ("A", "B"):
            client.post(f"/projects/{p['id']}/locations", json={"code": code, "kind": "building"})
        client.post(f"/projects/{p['id']}/legend/freeze", json={"actor": "test"})
        locs = {loc["code"]: loc for loc in client.get(f"/projects/{p['id']}/locations").json()}

        # capacity and label are attributes — editable with the legend frozen
        for code, mw in (("A", 25), ("B", 15)):
            r = client.patch(f"/projects/{p['id']}/locations/{locs[code]['id']}", json={"mw_it": mw})
            assert r.status_code == 200, r.text
        assert client.get(f"/projects/{p['id']}/capacity").json()["reconciles"] is True
        assert client.patch(f"/projects/{p['id']}/locations/{locs['A']['id']}",
                            json={"label": "Compute 1"}).status_code == 200

        # the crosswalk keys stay locked
        for patch in ({"code": "A1"}, {"kind": "area"}):
            assert client.patch(f"/projects/{p['id']}/locations/{locs['A']['id']}",
                                json=patch).status_code == 409
        assert client.post(f"/projects/{p['id']}/locations",
                           json={"code": "C", "kind": "building"}).status_code == 409
        assert client.delete(f"/projects/{p['id']}/locations/{locs['B']['id']}").status_code == 409
    finally:
        with SessionLocal() as s:
            for table in ("project_location", "legend_event"):
                s.execute(text(f"delete from viasel.{table} where project_id = :i"), {"i": p["id"]})
            s.execute(text("delete from viasel.project where id = :i"), {"i": p["id"]})
            s.commit()


def test_agreement_generates_its_exhibits_from_the_record() -> None:
    """An exhibit is a view of the record — nothing is typed into a template."""
    P = "APIAGREE"
    _scrub_agreement_fixture(P)  # a previous failed run must not block this one
    pr = client.post("/projects", json={"name": P}).json()
    ven = client.post("/vendors", json={"name": "T-Agree OEM", "code": "TAO", "role": "oem"}).json()
    try:
        client.patch(f"/projects/{pr['id']}", json={
            "site_code": "DTW01", "buyer_entity": "RD Michigan Property Owner I LLC",
            "address": "11600 West Michigan Ave.", "city": "Saline", "state": "MI"})
        client.post(f"/projects/{pr['id']}/locations", json={"code": "C1", "label": "Compute 1", "kind": "building"})
        client.post(f"/vendors/{ven['id']}/contacts", json={"name": "A. Turner", "title": "President"})

        spec = {"type_query": "Padmount Transformer", "denominator": "$/kVA", "size": 5000, "sub": "5000kVA"}
        client.post("/demand-lines/batch", json={"lines": [
            {"project_id": P, "qty": 12, "spec_attributes": spec, "target_building": "C1", "rom_unit_price": 320000.0},
            {"project_id": P, "qty": 8, "spec_attributes": spec, "target_building": "C1", "rom_unit_price": 320000.0}]})
        client.post("/freeze", json={"project_id": P, "scope": "project", "actor": "test"})
        g = client.get("/packages/candidates", params={"project": P}).json()["groups"][0]
        pkg = client.post("/packages", json={"project_id": P, "demand_line_ids": g["demand_line_ids"]}).json()["package"]

        # an open lot isn't committable
        assert client.post("/agreements", json={"project_id": P, "package_ids": [pkg["id"]]}).status_code == 409

        q = client.post(f"/packages/{pkg['id']}/quotes", json={
            "vendor_id": ven["id"], "unit_price": 306074.0, "services_unit": 5000.0,
            "one_time_cost": 40000.0, "lead_time_weeks": 52}).json()["leveling"][0]
        client.post(f"/packages/{pkg['id']}/award", json={"quote_id": q["quote_id"]})

        ag = client.post("/agreements", json={"project_id": P, "package_ids": [pkg["id"]]}).json()
        assert ag["code"].endswith("-TAO-001") and ag["state"] == "drafted"
        assert ag["line_count"] == 2 and ag["total_qty"] == 20
        assert ag["package_codes"] == [pkg["code"]]
        # value is derived from the lines, so it cannot disagree with the exhibit
        assert ag["contract_value"] == round(q["effective_unit"] * 20, 2)
        # the same scope can't be committed twice
        assert client.post("/agreements", json={"project_id": P, "package_ids": [pkg["id"]]}).status_code == 409
        # a signed version can't be registered before the exhibit data is released
        assert client.post(f"/agreements/{ag['id']}/executed",
                           json={"source_system": "Procore"}).status_code == 409
        rel = client.post(f"/agreements/{ag['id']}/release", json={"released_date": "2026-08-11"}).json()
        assert rel["state"] == "released"  # Viasel has no "executed" state — signing happens elsewhere

        # the signed version comes back with a trimmed quantity and a retyped total
        ex = client.post(f"/agreements/{ag['id']}/executed", json={
            "source_system": "Procore", "external_document_ref": "MIT-EAT-002",
            "execution_date": "2026-08-14", "stated_po_number": ag["code"],
            "stated_vendor_name": "T-Agree OEM", "stated_total_qty": 18,
            "stated_contract_value": 5400000.0, "retrieved_by": "test"}).json()
        assert ex["reconciliation_status"] == "diverged"
        rc = client.get(f"/agreements/{ag['id']}/reconciliation").json()
        flagged = {d["field_name"]: (d["generated_value"], d["executed_value"]) for d in rc["divergences"]}
        assert flagged["total_qty"] == ("20.00", "18.00")
        assert "contract_value" in flagged
        # a field the document didn't state isn't a divergence — that's a different claim
        assert "buyer_entity" not in flagged
        # flagged, never applied: the record still holds what it committed
        assert client.get(f"/agreements/{ag['id']}").json()["total_qty"] == 20
        assert client.post(f"/agreements/{ag['id']}/executed",
                           json={"source_system": "X"}).status_code == 409

        ex = client.get(f"/agreements/{ag['id']}/exhibits").json()
        cover = ex["cover_sheet"]
        assert cover["po_number"] == ag["code"]
        assert cover["buyer_entity"] == "RD Michigan Property Owner I LLC"
        assert cover["site_code"] == "DTW01" and "Saline" in cover["project_address"]
        assert cover["vendor_code"] == "TAO" and "A. Turner" in cover["vendor_contacts"][0]

        rows = ex["equipment_list"]
        assert len(rows) == 2 and {r["qty"] for r in rows} == {12, 8}
        assert all(r["lead_time_weeks"] == 52 for r in rows)
        # the exhibit total is the contract value by construction, not by coincidence
        assert round(sum(r["extended_price"] for r in rows), 2) == ag["contract_value"]
        # the legend is the project's own codifiers, not a hand-kept list
        assert {(x["kind"], x["code"]) for x in ex["legend"]} == {("campus", "DTW01"), ("building", "C1")}
        # what exhibit content can attach to: the units allocated to this vendor at sourcing
        assert [c["qty"] for c in ex["committed_lines"]] == [12, 8]
        assert ex["equipment_types"][0]["unit_count"] == 20
        assert ex["roj_dates"] == []  # nothing scheduled yet

        # a delivery schedule cannot promise more units than were bought
        line = ex["committed_lines"][0]
        assert client.post(f"/agreements/{ag['id']}/exhibit-items", json={
            "exhibit": "delivery_schedule", "scope_line_id": line["scope_line_id"],
            "description": "tranche", "qty": line["qty"] + 1, "due_date": "2027-03-31"}).status_code == 409
        ok = client.post(f"/agreements/{ag['id']}/exhibit-items", json={
            "exhibit": "delivery_schedule", "scope_line_id": line["scope_line_id"],
            "description": "tranche", "qty": line["qty"], "due_date": "2027-03-31"})
        assert ok.status_code == 201

        # spares and BOM name the units they belong to
        assert client.post(f"/agreements/{ag['id']}/exhibit-items", json={
            "exhibit": "spare_parts", "description": "floating", "qty": 1}).status_code == 409
        # a required document needs the gate that gives it teeth
        assert client.post(f"/agreements/{ag['id']}/exhibit-items", json={
            "exhibit": "required_documents", "description": "manuals"}).status_code == 409
        # capacity is per type, per place, and locked to a confirmed ROJ date
        cap = {"exhibit": "shipping_capacity", "description": "4/month", "qty": 4}
        assert client.post(f"/agreements/{ag['id']}/exhibit-items", json=cap).status_code == 409
        etype = ex["equipment_types"][0]["equipment_type_id"]
        assert client.post(f"/agreements/{ag['id']}/exhibit-items", json={
            **cap, "equipment_type_id": etype, "building": "C1",
            "due_date": "2028-01-31"}).status_code == 409

        after = client.get(f"/agreements/{ag['id']}/exhibits").json()
        assert after["roj_dates"] == ["2027-03-31"]
        covered = {c["scope_line_id"]: c for c in after["delivery_coverage"]}
        assert covered[line["scope_line_id"]]["remaining_qty"] == 0
    finally:
        _scrub_agreement_fixture(P)


def _scrub_agreement_fixture(P: str) -> None:
    """Tear the whole fixture down, in dependency order, whether or not the test got far."""
    with SessionLocal() as s:
        for q in (
                f"delete from viasel.exhibit_item where agreement_id in (select id from viasel.agreement where project_id = '{P}')",
                f"delete from viasel.field_divergence where executed_agreement_id in (select id from viasel.executed_agreement where agreement_id in (select id from viasel.agreement where project_id = '{P}'))",
                f"delete from viasel.executed_agreement where agreement_id in (select id from viasel.agreement where project_id = '{P}')",
                f"update viasel.scope_line set agreement_id = null where demand_line_id in (select id from viasel.demand_line where project_id = '{P}')",
                f"delete from viasel.agreement where project_id = '{P}'",
                f"delete from viasel.scope_line where demand_line_id in (select id from viasel.demand_line where project_id = '{P}')",
                f"delete from viasel.quote where sourcing_package_id in (select id from viasel.sourcing_package where project_id = '{P}')",
                f"delete from viasel.package_line where sourcing_package_id in (select id from viasel.sourcing_package where project_id = '{P}')",
                f"delete from viasel.sourcing_package where project_id = '{P}'",
                f"delete from viasel.freeze_event where project_id = '{P}'",
                f"delete from viasel.demand_line where project_id = '{P}'",
                "delete from viasel.vendor_contact where vendor_id in (select id from viasel.vendor where name like 'T-Agree%')",
                "delete from viasel.vendor where name like 'T-Agree%'",
                "delete from viasel.project_location where project_id in (select id from viasel.project where name = :p)",
                "delete from viasel.legend_event where project_id in (select id from viasel.project where name = :p)",
                "delete from viasel.project where name = :p",
        ):
            s.execute(text(q), {"p": P})
        s.commit()
