"""Unit tests for the printable sow list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.sow.sheet import build_sow_list


def test_empty_list():
    out = build_sow_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_look_sow_cover_and_skip():
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
            nickname="Cherry tomato",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Solanum lycopersicum", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="c",
            nickname="Climbing bean",
            environment="outdoor",
            taxon=SimpleNamespace(scientific_name="Phaseolus vulgaris", common_names=[]),
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
    out = build_sow_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the sow list at Loft" in out["summary"]
    mon = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert mon["skip"] is True
    tom = next(p for p in out["plants"] if p["nickname"] == "Cherry tomato")
    assert tom["sow"] == "sow"
    assert "Surface sow" in tom["sow_label"]
    bean = next(p for p in out["plants"] if p["nickname"] == "Climbing bean")
    assert bean["sow"] == "cover"
    assert "Cover the seed, then wait" in bean["sow_label"]
    mystery = next(p for p in out["plants"] if p["nickname"] == "Mystery plant")
    assert mystery["sow"] == "look"
    assert out["look"] == 1
    assert out["sow"] == 1
    assert out["cover"] == 1
    assert out["skip"] == 1
