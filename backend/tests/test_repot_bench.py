"""Unit tests for the printable repot bench."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.repot.sheet import build_repot_bench


def test_empty_bench():
    out = build_repot_bench(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["needs_measure"] == 0


def test_next_size_and_measure():
    plants = [
        SimpleNamespace(
            id="a",
            nickname="Monstera",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Monstera deliciosa", common_names=[]),
            custom_attributes={"emoji": "🌿"},
            pot_size_liters=5,
            pot_material="plastic",
        ),
        SimpleNamespace(
            id="b",
            nickname="Olive",
            environment="outdoor",
            taxon=None,
            custom_attributes={},
            pot_size_liters=None,
            pot_material=None,
        ),
    ]
    out = build_repot_bench(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 2
    assert "2 plants you can pot on at Loft" in out["summary"]
    monstera = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert monstera["next_pot_liters"] == 7.0
    assert monstera["next_label"] == "7 L pot"
    assert monstera["scientific_name"] == "Monstera deliciosa"
    olive = next(p for p in out["plants"] if p["nickname"] == "Olive")
    assert olive["needs_measure"] is True
    assert "measure" in olive["next_label"]
    assert out["sized"] == 1
    assert out["needs_measure"] == 1
