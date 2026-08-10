"""API tests via TestClient. Read-only endpoints + a create that cleans up after itself."""

import uuid

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import DemandLine

client = TestClient(app)


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
