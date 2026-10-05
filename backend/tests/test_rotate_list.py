"""Unit tests for the printable rotate list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.rotate.sheet import build_rotate_list


def test_empty_list():
    out = build_rotate_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_quarter_half_and_skip():
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
            nickname="Fiddle",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Ficus lyrata", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="c",
            nickname="Pothos",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Epipremnum aureum", common_names=[]),
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
    out = build_rotate_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the rotate list at Loft" in out["summary"]
    monstera = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert monstera["rotate"] == "quarter"
    fiddle = next(p for p in out["plants"] if p["nickname"] == "Fiddle")
    assert fiddle["rotate"] == "half"
    pothos = next(p for p in out["plants"] if p["nickname"] == "Pothos")
    assert pothos["skip"] is True
    tomato = next(p for p in out["plants"] if p["nickname"] == "Patio tomato")
    assert tomato["skip"] is True
    assert out["quarter"] == 1
    assert out["half"] == 1
    assert out["skip"] == 2
