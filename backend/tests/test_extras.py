"""Layout, stats, labels, weather engine unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.watering.engine import compute_baseline
from app.modules.weather.client import WeatherSnapshot
from tests.conftest import auth_header, setup_instance


def test_outdoor_rain_lengthens_interval():
    last = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    dry = compute_baseline(
        now=datetime(2026, 7, 5, 12, 0, tzinfo=UTC),
        last_watered_at=last,
        baseline_min_days=7,
        baseline_max_days=7,
        pot_size_liters=5,
        pot_material=None,
        soil_type=None,
        environment="outdoor",
        growth_stage=None,
        weather_temp_c=28,
        weather_humidity=40,
        weather_precip_24h_mm=0,
    )
    wet = compute_baseline(
        now=datetime(2026, 7, 5, 12, 0, tzinfo=UTC),
        last_watered_at=last,
        baseline_min_days=7,
        baseline_max_days=7,
        pot_size_liters=5,
        pot_material=None,
        soil_type=None,
        environment="outdoor",
        growth_stage=None,
        weather_temp_c=28,
        weather_humidity=40,
        weather_precip_24h_mm=12,
    )
    assert wet.next_due_at > dry.next_due_at
    assert any(f["key"] == "weather_precip" for f in wet.factor_breakdown)


@pytest.mark.usefixtures("clean_db")
async def test_layout_and_placement(client):
    admin = await setup_instance(client)
    headers = auth_header(admin["access_token"])
    hid = admin["household_id"]

    site = await client.post(
        f"/api/v1/households/{hid}/sites",
        headers=headers,
        json={"name": "Home"},
    )
    assert site.status_code == 201, site.text
    sid = site.json()["id"]
    # Prefer default room created with the site
    spid = site.json().get("space_id")
    if not spid:
        space = await client.post(
            f"/api/v1/households/{hid}/sites/{sid}/spaces",
            headers=headers,
            json={"name": "Living Room", "kind": "room"},
        )
        assert space.status_code == 201
        spid = space.json()["id"]
    # Find the space that received the placement later via list

    plant = await client.post(
        f"/api/v1/households/{hid}/plants",
        headers=headers,
        json={"nickname": "Shelf plant"},
    )
    pid = plant.json()["id"]

    place = await client.put(
        f"/api/v1/households/{hid}/plants/{pid}/placement",
        headers=headers,
        json={"space_id": spid, "x": 100, "y": 50},
    )
    assert place.status_code == 200, place.text

    tree = await client.get(f"/api/v1/households/{hid}/sites", headers=headers)
    assert tree.status_code == 200
    assert tree.json()[0]["spaces"][0]["placements"][0]["plant_id"] == pid

    unassigned = await client.get(
        f"/api/v1/households/{hid}/layout/unassigned",
        headers=headers,
    )
    assert unassigned.status_code == 200
    assert all(p["id"] != pid for p in unassigned.json())


@pytest.mark.usefixtures("clean_db")
async def test_stats_and_label_pdf(client):
    admin = await setup_instance(client)
    headers = auth_header(admin["access_token"])
    hid = admin["household_id"]

    plant = await client.post(
        f"/api/v1/households/{hid}/plants",
        headers=headers,
        json={"nickname": "Label Me", "estimated_value": 25},
    )
    pid = plant.json()["id"]
    await client.post(
        f"/api/v1/households/{hid}/plants/{pid}/water",
        headers=headers,
        json={"amount": "normal"},
    )

    stats = await client.get(f"/api/v1/households/{hid}/stats/summary", headers=headers)
    assert stats.status_code == 200
    body = stats.json()
    assert body["plants_active"] >= 1
    assert body["waterings_30d"] >= 1

    label = await client.get(
        f"/api/v1/households/{hid}/plants/{pid}/label.pdf",
        headers=headers,
    )
    assert label.status_code == 200
    assert label.headers["content-type"].startswith("application/pdf")
    assert label.content[:4] == b"%PDF"


@pytest.mark.usefixtures("clean_db")
async def test_weather_endpoint_without_coords(client):
    admin = await setup_instance(client)
    headers = auth_header(admin["access_token"])
    hid = admin["household_id"]
    wx = await client.get(f"/api/v1/households/{hid}/weather", headers=headers)
    assert wx.status_code == 200
    assert wx.json()["configured"] is False


@pytest.mark.usefixtures("clean_db")
async def test_weather_with_mock(client):
    admin = await setup_instance(client)
    headers = auth_header(admin["access_token"])
    hid = admin["household_id"]

    # Set coordinates
    await client.patch(
        f"/api/v1/households/{hid}",
        headers=headers,
        json={"latitude": 52.52, "longitude": 13.405},
    )

    snap = WeatherSnapshot(
        latitude=52.52,
        longitude=13.405,
        current_temp_c=22.0,
        current_humidity=55.0,
        precip_next_24h_mm=1.0,
        raw={"mock": True},
    )
    with patch(
        "app.modules.weather.service.fetch_open_meteo",
        new=AsyncMock(return_value=snap),
    ):
        wx = await client.post(
            f"/api/v1/households/{hid}/weather/refresh",
            headers=headers,
        )
    assert wx.status_code == 200, wx.text
    assert wx.json()["configured"] is True
    assert wx.json()["temperature_c"] == 22.0
