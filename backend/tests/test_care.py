"""Timeline, tasks, watering, dashboard tests."""

from __future__ import annotations

import pytest

from app.db.session import AsyncSessionLocal
from app.modules.taxonomy.service import seed_global_taxa
from tests.conftest import auth_header, setup_instance


async def _seed():
    async with AsyncSessionLocal() as session:
        await seed_global_taxa(session)
        await session.commit()


@pytest.mark.usefixtures("clean_db")
async def test_water_creates_event_and_updates_due(client):
    await _seed()
    admin = await setup_instance(client)
    headers = auth_header(admin["access_token"])
    hid = admin["household_id"]

    taxa = await client.get("/api/v1/taxa", params={"q": "Monstera"}, headers=headers)
    taxon_id = taxa.json()[0]["id"]

    plant = await client.post(
        f"/api/v1/households/{hid}/plants",
        headers=headers,
        json={
            "nickname": "Monstera",
            "taxon_id": taxon_id,
            "pot_size_liters": 2,
            "pot_material": "terracotta",
            "environment": "indoor",
        },
    )
    assert plant.status_code == 201, plant.text
    pid = plant.json()["id"]

    watering = await client.get(
        f"/api/v1/households/{hid}/plants/{pid}/watering",
        headers=headers,
    )
    assert watering.status_code == 200
    assert watering.json()["next_due_at"] is not None
    assert watering.json()["factors"]

    watered = await client.post(
        f"/api/v1/households/{hid}/plants/{pid}/water",
        headers=headers,
        json={"amount": "normal"},
    )
    assert watered.status_code == 200, watered.text
    body = watered.json()
    assert body["event"]["type"] == "watered"
    assert body["watering"]["last_watered_at"] is not None
    assert body["watering"]["urgency"] in {"ok", "soon", "due", "overdue"}

    events = await client.get(
        f"/api/v1/households/{hid}/plants/{pid}/events",
        headers=headers,
    )
    assert events.status_code == 200
    assert any(e["type"] == "watered" for e in events.json())


@pytest.mark.usefixtures("clean_db")
async def test_task_complete_emits_event(client):
    admin = await setup_instance(client)
    headers = auth_header(admin["access_token"])
    hid = admin["household_id"]

    plant = await client.post(
        f"/api/v1/households/{hid}/plants",
        headers=headers,
        json={"nickname": "Fern"},
    )
    pid = plant.json()["id"]

    task = await client.post(
        f"/api/v1/households/{hid}/tasks",
        headers=headers,
        json={
            "title": "Prune Fern",
            "type": "prune",
            "plant_ids": [pid],
        },
    )
    assert task.status_code == 201, task.text
    tid = task.json()["id"]

    done = await client.post(
        f"/api/v1/households/{hid}/tasks/{tid}/complete",
        headers=headers,
        json={},
    )
    assert done.status_code == 200
    assert done.json()["status"] == "done"

    events = await client.get(
        f"/api/v1/households/{hid}/events",
        headers=headers,
    )
    types = [e["type"] for e in events.json()]
    assert "pruned" in types


@pytest.mark.usefixtures("clean_db")
async def test_dashboard_and_feedback(client):
    await _seed()
    admin = await setup_instance(client)
    headers = auth_header(admin["access_token"])
    hid = admin["household_id"]

    plant = await client.post(
        f"/api/v1/households/{hid}/plants",
        headers=headers,
        json={"nickname": "Pothos", "environment": "indoor"},
    )
    pid = plant.json()["id"]

    await client.post(
        f"/api/v1/households/{hid}/plants/{pid}/water",
        headers=headers,
        json={"amount": "light"},
    )

    fb = await client.post(
        f"/api/v1/households/{hid}/plants/{pid}/watering-feedback",
        headers=headers,
        json={"rating": "too_wet"},
    )
    assert fb.status_code == 200
    # bias should push later intervals
    assert isinstance(fb.json()["factors"], list)

    dash = await client.get(f"/api/v1/households/{hid}/dashboard", headers=headers)
    assert dash.status_code == 200
    data = dash.json()
    assert "counts" in data
    assert data["counts"]["plants_active"] >= 1
    assert "tasks_today" in data
    assert "recent_events" in data


@pytest.mark.usefixtures("clean_db")
async def test_engine_unit_baseline_differs_by_pot():
    from datetime import UTC, datetime

    from app.modules.watering.engine import compute_baseline

    now = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    last = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
    small = compute_baseline(
        now=now,
        last_watered_at=last,
        baseline_min_days=7,
        baseline_max_days=10,
        pot_size_liters=1.0,
        pot_material="terracotta",
        soil_type="free_draining",
        environment="indoor",
        growth_stage="mature",
    )
    large = compute_baseline(
        now=now,
        last_watered_at=last,
        baseline_min_days=7,
        baseline_max_days=10,
        pot_size_liters=12.0,
        pot_material="plastic",
        soil_type="moisture_retentive",
        environment="indoor",
        growth_stage="mature",
    )
    assert small.next_due_at < large.next_due_at
