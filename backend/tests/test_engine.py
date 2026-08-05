"""Unit tests for watering engine (no DB)."""

from datetime import UTC, datetime

from app.modules.watering.engine import compute_baseline


def test_winter_lengthens_interval():
    last = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    winter = compute_baseline(
        now=datetime(2026, 1, 5, 12, 0, tzinfo=UTC),
        last_watered_at=last,
        baseline_min_days=7,
        baseline_max_days=7,
        pot_size_liters=5,
        pot_material=None,
        soil_type=None,
        environment="indoor",
        growth_stage=None,
    )
    summer = compute_baseline(
        now=datetime(2026, 7, 5, 12, 0, tzinfo=UTC),
        last_watered_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        baseline_min_days=7,
        baseline_max_days=7,
        pot_size_liters=5,
        pot_material=None,
        soil_type=None,
        environment="indoor",
        growth_stage=None,
    )
    # Compare interval length via due - last
    w_days = (winter.next_due_at - last).total_seconds()
    s_days = (summer.next_due_at - datetime(2026, 7, 1, 12, 0, tzinfo=UTC)).total_seconds()
    assert w_days > s_days


def test_manual_override():
    manual = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
    rec = compute_baseline(
        now=datetime(2026, 7, 20, 9, 0, tzinfo=UTC),
        last_watered_at=datetime(2026, 7, 10, 9, 0, tzinfo=UTC),
        baseline_min_days=7,
        baseline_max_days=7,
        pot_size_liters=None,
        pot_material=None,
        soil_type=None,
        environment="indoor",
        growth_stage=None,
        manual_next_due_at=manual,
    )
    assert rec.next_due_at == manual
    assert any(f["key"] == "manual_override" for f in rec.factor_breakdown)


def test_hot_weather_shortens_and_gives_care_card():
    last = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)
    cool = compute_baseline(
        now=datetime(2026, 7, 3, 8, 0, tzinfo=UTC),
        last_watered_at=last,
        baseline_min_days=7,
        baseline_max_days=7,
        pot_size_liters=5,
        pot_material=None,
        soil_type=None,
        environment="outdoor",
        growth_stage=None,
        weather_temp_c=18,
        weather_humidity=60,
        weather_precip_24h_mm=0,
        timezone="Europe/Amsterdam",
    )
    hot = compute_baseline(
        now=datetime(2026, 7, 3, 8, 0, tzinfo=UTC),
        last_watered_at=last,
        baseline_min_days=7,
        baseline_max_days=7,
        pot_size_liters=5,
        pot_material=None,
        soil_type=None,
        environment="outdoor",
        growth_stage=None,
        weather_temp_c=34,
        weather_humidity=25,
        weather_precip_24h_mm=0,
        timezone="Europe/Amsterdam",
    )
    assert hot.interval_days < cool.interval_days
    assert hot.amount_ml is not None and hot.amount_ml > 0
    assert hot.amount_howto
    assert hot.best_time_of_day == "morning"
    assert "Water" in hot.schedule_plain or "water" in hot.schedule_plain.lower()
