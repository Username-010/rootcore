"""Unit tests for the printable harvest list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.harvest.sheet import build_harvest_list


def test_empty_list():
    out = build_harvest_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_leaf_fruit_look_and_skip():
    plants = [
        SimpleNamespace(
            id="a",
            nickname="Basil",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Ocimum basilicum", common_names=[]),
            custom_attributes={"emoji": "🌿"},
        ),
        SimpleNamespace(
            id="b",
            nickname="Tomato",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Solanum lycopersicum", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="c",
            nickname="Peace lily",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Spathiphyllum wallisii", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="d",
            nickname="Monstera",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Monstera deliciosa", common_names=[]),
            custom_attributes={},
        ),
    ]
    out = build_harvest_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the harvest list at Loft" in out["summary"]
    basil = next(p for p in out["plants"] if p["nickname"] == "Basil")
    assert basil["harvest"] == "leaf"
    tomato = next(p for p in out["plants"] if p["nickname"] == "Tomato")
    assert tomato["harvest"] == "fruit"
    lily = next(p for p in out["plants"] if p["nickname"] == "Peace lily")
    assert lily["harvest"] == "look"
    monstera = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert monstera["skip"] is True
    assert out["leaf"] == 1
    assert out["fruit"] == 1
    assert out["look"] == 1
    assert out["skip"] == 1
