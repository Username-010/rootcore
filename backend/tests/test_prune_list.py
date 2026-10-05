"""Unit tests for the printable prune list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.prune.sheet import build_prune_list


def test_empty_list():
    out = build_prune_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_hard_pinch_light_and_skip():
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
            nickname="Olive",
            environment="outdoor",
            taxon=None,
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
    out = build_prune_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the prune list at Loft" in out["summary"]
    monstera = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert monstera["cut"] == "pinch"
    olive = next(p for p in out["plants"] if p["nickname"] == "Olive")
    assert olive["cut"] == "hard"
    aloe = next(p for p in out["plants"] if p["nickname"] == "Aloe")
    assert aloe["skip"] is True
    lily = next(p for p in out["plants"] if p["nickname"] == "Peace lily")
    assert lily["cut"] == "light"
    assert out["pinch"] == 1
    assert out["hard"] == 1
    assert out["skip"] == 1
    assert out["light"] == 1
