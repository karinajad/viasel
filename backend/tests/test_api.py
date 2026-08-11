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
