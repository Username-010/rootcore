"""Unit tests for the printable frost list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.frost.sheet import build_frost_list


def test_empty_list():
    out = build_frost_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_bring_cover_dry_and_skip():
    plants = [
        SimpleNamespace(
            id="a",
            nickname="Tomato",
            environment="outdoor",
            taxon=SimpleNamespace(scientific_name="Solanum lycopersicum", common_names=[]),
            custom_attributes={"emoji": "🍅"},
        ),
        SimpleNamespace(
            id="b",
            nickname="Lavender",
            environment="outdoor",
            taxon=SimpleNamespace(scientific_name="Lavandula angustifolia", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="c",
            nickname="Aloe",
            environment="outdoor",
            taxon=SimpleNamespace(scientific_name="Aloe vera", common_names=[]),
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
    out = build_frost_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the frost list at Loft" in out["summary"]
    tomato = next(p for p in out["plants"] if p["nickname"] == "Tomato")
    assert tomato["frost"] == "bring"
    lav = next(p for p in out["plants"] if p["nickname"] == "Lavender")
    assert lav["frost"] == "cover"
    aloe = next(p for p in out["plants"] if p["nickname"] == "Aloe")
    assert aloe["frost"] == "dry"
    mon = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert mon["skip"] is True
    assert out["bring"] == 1
    assert out["cover"] == 1
    assert out["dry"] == 1
    assert out["skip"] == 1
