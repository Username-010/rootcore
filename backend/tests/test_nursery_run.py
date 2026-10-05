"""Unit tests for the printable nursery-run shopping list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.shop.sheet import build_nursery_run


def test_empty_sheet():
    out = build_nursery_run(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["soils"] == []


def test_groups_soil_and_flags_missing_pot():
    plants = [
        SimpleNamespace(
            id="a",
            nickname="Basil",
            environment="indoor",
            pot_size_liters=1.5,
            soil_type="herb mix",
            custom_attributes={"emoji": "🌿"},
        ),
        SimpleNamespace(
            id="b",
            nickname="Tomato",
            environment="outdoor",
            pot_size_liters=None,
            soil_type="herb mix",
            custom_attributes={},
        ),
        SimpleNamespace(
            id="c",
            nickname="Fern",
            environment="indoor",
            pot_size_liters=3,
            soil_type=None,
            custom_attributes={},
        ),
    ]
    out = build_nursery_run(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 3
    assert "3 plants to shop for at Loft" in out["summary"]
    soils = {s["soil_type"]: s for s in out["soils"]}
    assert soils["herb mix"]["plants"] == 2
    assert soils["unspecified mix"]["plants"] == 1
    tomato = next(p for p in out["plants"] if p["nickname"] == "Tomato")
    assert tomato["need_pot"] is True
    basil = next(p for p in out["plants"] if p["nickname"] == "Basil")
    assert basil["need_pot"] is False
    assert basil["emoji"] == "🌿"
