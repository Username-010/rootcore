"""Unit tests for the printable mist list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.mist.sheet import build_mist_list


def test_empty_list():
    out = build_mist_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_fine_light_pebble_and_skip():
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
            nickname="Aloe",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Aloe vera", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="d",
            nickname="Peace lily",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Spathiphyllum", common_names=[]),
            custom_attributes={},
        ),
    ]
    out = build_mist_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the mist list at Loft" in out["summary"]
    calathea = next(p for p in out["plants"] if p["nickname"] == "Calathea")
    assert calathea["mist"] == "fine"
    monstera = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert monstera["mist"] == "light"
    aloe = next(p for p in out["plants"] if p["nickname"] == "Aloe")
    assert aloe["skip"] is True
    lily = next(p for p in out["plants"] if p["nickname"] == "Peace lily")
    assert lily["mist"] == "pebble"
    assert out["fine"] == 1
    assert out["light"] == 1
    assert out["skip"] == 1
    assert out["pebble"] == 1
