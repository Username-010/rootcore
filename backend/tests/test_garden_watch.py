"""Unit tests for garden watch frost / rain flags."""

from datetime import UTC, datetime

from app.modules.weather.client import DailyForecast, WeatherSnapshot
from app.modules.weather.watch import build_garden_watch, is_outdoor_kind


def test_indoor_kinds_are_not_outdoor():
    assert is_outdoor_kind("room") is False
    assert is_outdoor_kind("kitchen") is False
    assert is_outdoor_kind("garden") is True
    assert is_outdoor_kind("balcony") is True


def test_frost_and_rain_alerts():
    snap = WeatherSnapshot(
        latitude=51.92,
        longitude=4.48,
        current_temp_c=8.0,
        current_humidity=70.0,
        precip_next_24h_mm=1.0,
        raw={},
        daily=[
            DailyForecast("2026-10-05", 12.0, 1.5, 0.0, 1),
            DailyForecast("2026-10-06", 10.0, -2.0, 8.0, 71),
            DailyForecast("2026-10-07", 14.0, 8.0, 0.2, 1),
        ],
    )
    plants = [{"plant_id": "1", "nickname": "Tomato", "emoji": "🍅", "space_name": "Balcony"}]
    out = build_garden_watch(
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
        snap=snap,
        outdoor_plants=plants,
        configured=True,
    )
    assert out["counts"]["frost_nights"] == 2
    assert out["counts"]["rain_days"] == 1
    kinds = {a["kind"] for a in out["alerts"]}
    assert "frost" in kinds
    assert "rain" in kinds
    assert "Protect 1 outdoor plant" in out["summary"]
