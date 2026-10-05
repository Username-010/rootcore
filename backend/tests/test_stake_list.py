"""Unit tests for the printable stake list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.stake.sheet import build_stake_list


def test_empty_list():
    out = build_stake_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_moss_cane_check_and_skip():
    plants = [
        SimpleNamespace(
            id="a",
            nickname="Monstera",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Monstera deliciosa", common_names=[]),
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
            nickname="Aloe",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Aloe vera", common_names=[]),
            custom_attributes={},
        ),
    ]
    out = build_stake_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the stake list at Loft" in out["summary"]
    monstera = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert monstera["stake"] == "moss"
    tomato = next(p for p in out["plants"] if p["nickname"] == "Tomato")
    assert tomato["stake"] == "cane"
    lily = next(p for p in out["plants"] if p["nickname"] == "Peace lily")
    assert lily["stake"] == "check"
    aloe = next(p for p in out["plants"] if p["nickname"] == "Aloe")
    assert aloe["skip"] is True
    assert out["moss"] == 1
    assert out["cane"] == 1
    assert out["check"] == 1
    assert out["skip"] == 1
