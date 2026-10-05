"""Unit tests for the printable light map."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.light.sheet import build_light_map


def test_empty_list():
    out = build_light_map(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_shade_bright_direct_and_skip():
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
            nickname="Pond moss",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Aquatic fungus", common_names=[]),
            custom_attributes={},
        ),
    ]
    out = build_light_map(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the light map at Loft" in out["summary"]
    cal = next(p for p in out["plants"] if p["nickname"] == "Calathea")
    assert cal["light"] == "shade"
    mon = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert mon["light"] == "bright"
    aloe = next(p for p in out["plants"] if p["nickname"] == "Aloe")
    assert aloe["light"] == "direct"
    moss = next(p for p in out["plants"] if p["nickname"] == "Pond moss")
    assert moss["skip"] is True
    assert out["shade"] == 1
    assert out["bright"] == 1
    assert out["direct"] == 1
    assert out["skip"] == 1
