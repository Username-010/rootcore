"""Unit tests for the printable topdress list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.topdress.sheet import build_topdress_list


def test_empty_list():
    out = build_topdress_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_look_thin_topdress_and_skip():
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
            nickname="Tomato seedling",
            environment="outdoor",
            taxon=SimpleNamespace(scientific_name="Solanum lycopersicum", common_names=[]),
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
    out = build_topdress_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the topdress list at Loft" in out["summary"]
    aloe = next(p for p in out["plants"] if p["nickname"] == "Aloe")
    assert aloe["skip"] is True
    seedling = next(p for p in out["plants"] if p["nickname"] == "Tomato seedling")
    assert seedling["topdress"] == "thin"
    assert "thin dusting" in seedling["topdress_label"]
    tom = next(p for p in out["plants"] if p["nickname"] == "Cherry tomato")
    assert tom["topdress"] == "topdress"
    assert "Fresh mix on top, leave the stem" in tom["topdress_label"]
    mystery = next(p for p in out["plants"] if p["nickname"] == "Mystery plant")
    assert mystery["topdress"] == "look"
    assert out["look"] == 1
    assert out["thin"] == 1
    assert out["topdress"] == 1
    assert out["skip"] == 1
