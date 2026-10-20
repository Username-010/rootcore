"""Sensor selector must not mutate cover photos while listing plants."""

from unittest.mock import AsyncMock

import pytest

from tests.conftest import auth_header, setup_instance


@pytest.mark.usefixtures("clean_db")
async def test_sensor_plant_options_do_not_backfill_covers(client, monkeypatch):
    admin = await setup_instance(client)
    from app.modules.plants import service

    fill = AsyncMock(side_effect=AssertionError("Sensor selector must not fetch or mutate covers"))
    monkeypatch.setattr(service, "fill_missing_covers", fill)
    response = await client.get(
        f"/api/v1/households/{admin['household_id']}/plants?limit=200&backfill_covers=false",
        headers=auth_header(admin["access_token"]),
    )
    assert response.status_code == 200
    assert fill.call_count == 0
