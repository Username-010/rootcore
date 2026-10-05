"""Unit tests for the printable pest walk."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.pest.sheet import build_pest_walk


def test_empty_list():
    out = build_pest_walk(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_look_sticky_isolate_and_skip():
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
            nickname="Lemon",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Citrus limon", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="c",
            nickname="New fern gift",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Nephrolepis exaltata", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="d",
            nickname="Patio tomato",
            environment="outdoor",
            taxon=SimpleNamespace(scientific_name="Solanum lycopersicum", common_names=[]),
            custom_attributes={},
        ),
    ]
    out = build_pest_walk(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the pest walk at Loft" in out["summary"]
    monstera = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert monstera["pest"] == "look"
    lemon = next(p for p in out["plants"] if p["nickname"] == "Lemon")
    assert lemon["pest"] == "sticky"
    fern = next(p for p in out["plants"] if p["nickname"] == "New fern gift")
    assert fern["pest"] == "isolate"
    tomato = next(p for p in out["plants"] if p["nickname"] == "Patio tomato")
    assert tomato["skip"] is True
    assert out["look"] == 1
    assert out["sticky"] == 1
    assert out["isolate"] == 1
    assert out["skip"] == 1
