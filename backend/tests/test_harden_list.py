"""Unit tests for the printable harden-off list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.harden.sheet import build_harden_list


def test_empty_list():
    out = build_harden_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_look_shade_wind_and_skip():
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
            nickname="Basil seedling",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Ocimum basilicum", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="c",
            nickname="Cherry tomato",
            environment="indoor",
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
    out = build_harden_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the harden list at Loft" in out["summary"]
    mon = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert mon["skip"] is True
    basil = next(p for p in out["plants"] if p["nickname"] == "Basil seedling")
    assert basil["harden"] == "shade"
    assert "hour in shade" in basil["harden_label"]
    tom = next(p for p in out["plants"] if p["nickname"] == "Cherry tomato")
    assert tom["harden"] == "wind"
    assert "Shade first, then a little wind" in tom["harden_label"]
    mystery = next(p for p in out["plants"] if p["nickname"] == "Mystery plant")
    assert mystery["harden"] == "look"
    assert out["look"] == 1
    assert out["shade"] == 1
    assert out["wind"] == 1
    assert out["skip"] == 1
