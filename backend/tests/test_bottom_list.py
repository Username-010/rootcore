"""Unit tests for the printable bottom-water list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.bottom.sheet import build_bottom_list


def test_empty_list():
    out = build_bottom_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_look_soak_drain_and_skip():
    plants = [
        SimpleNamespace(
            id="a",
            nickname="Aloe",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Aloe vera", common_names=[]),
            custom_attributes={"emoji": "🌵"},
        ),
        SimpleNamespace(
            id="b",
            nickname="Boston fern",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Nephrolepis exaltata", common_names=[]),
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
    out = build_bottom_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the bottom-water list at Loft" in out["summary"]
    aloe = next(p for p in out["plants"] if p["nickname"] == "Aloe")
    assert aloe["skip"] is True
    fern = next(p for p in out["plants"] if p["nickname"] == "Boston fern")
    assert fern["bottom"] == "soak"
    assert "Soak from below, then drain" in fern["bottom_label"]
    tom = next(p for p in out["plants"] if p["nickname"] == "Cherry tomato")
    assert tom["bottom"] == "drain"
    mystery = next(p for p in out["plants"] if p["nickname"] == "Mystery plant")
    assert mystery["bottom"] == "look"
    assert out["look"] == 1
    assert out["soak"] == 1
    assert out["drain"] == 1
    assert out["skip"] == 1
