"""Unit tests for the printable airflow list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.air.sheet import build_air_list


def test_empty_list():
    out = build_air_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_look_draft_fan_and_skip():
    plants = [
        SimpleNamespace(
            id="a",
            nickname="Calathea",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Calathea orbifolia", common_names=[]),
            custom_attributes={"emoji": "🌿"},
        ),
        SimpleNamespace(
            id="b",
            nickname="Monstera",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Monstera deliciosa", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="c",
            nickname="Cherry tomato",
            environment="outdoor",
            taxon=SimpleNamespace(scientific_name="Solanum lycopersicum", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="d",
            nickname="Mystery plant",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Unknown", common_names=[]),
            custom_attributes={},
        ),
    ]
    out = build_air_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the airflow list at Loft" in out["summary"]
    cal = next(p for p in out["plants"] if p["nickname"] == "Calathea")
    assert cal["skip"] is True
    mon = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert mon["air"] == "draft"
    assert "Open a gap, skip the blast" in mon["air_label"]
    tom = next(p for p in out["plants"] if p["nickname"] == "Cherry tomato")
    assert tom["air"] == "fan"
    mystery = next(p for p in out["plants"] if p["nickname"] == "Mystery plant")
    assert mystery["air"] == "look"
    assert out["look"] == 1
    assert out["draft"] == 1
    assert out["fan"] == 1
    assert out["skip"] == 1
