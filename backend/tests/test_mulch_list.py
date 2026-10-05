"""Unit tests for the printable mulch list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.mulch.sheet import build_mulch_list


def test_empty_list():
    out = build_mulch_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_look_crown_mulch_and_skip():
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
            nickname="Hosta",
            environment="outdoor",
            taxon=SimpleNamespace(scientific_name="Hosta fortunei", common_names=[]),
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
    out = build_mulch_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the mulch list at Loft" in out["summary"]
    aloe = next(p for p in out["plants"] if p["nickname"] == "Aloe")
    assert aloe["skip"] is True
    hosta = next(p for p in out["plants"] if p["nickname"] == "Hosta")
    assert hosta["mulch"] == "crown"
    assert "thin ring" in hosta["mulch_label"]
    tom = next(p for p in out["plants"] if p["nickname"] == "Cherry tomato")
    assert tom["mulch"] == "mulch"
    assert "Cover the soil, leave the crown" in tom["mulch_label"]
    mystery = next(p for p in out["plants"] if p["nickname"] == "Mystery plant")
    assert mystery["mulch"] == "look"
    assert out["look"] == 1
    assert out["crown"] == 1
    assert out["mulch"] == 1
    assert out["skip"] == 1
