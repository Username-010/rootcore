"""Unit tests for the printable split list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.split.sheet import build_split_list


def test_empty_list():
    out = build_split_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_look_divide_pot_and_skip():
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
            nickname="Spider plant",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Chlorophytum comosum", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="c",
            nickname="Orchid",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Phalaenopsis amabilis", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="d",
            nickname="Crowded clump",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Unknown", common_names=[]),
            custom_attributes={},
        ),
    ]
    out = build_split_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the split list at Loft" in out["summary"]
    mon = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert mon["split"] == "look"
    assert "Look at the roots" in mon["split_label"]
    spi = next(p for p in out["plants"] if p["nickname"] == "Spider plant")
    assert spi["split"] == "divide"
    assert "Two pots, then one plant" in spi["split_label"]
    orch = next(p for p in out["plants"] if p["nickname"] == "Orchid")
    assert orch["skip"] is True
    clump = next(p for p in out["plants"] if p["nickname"] == "Crowded clump")
    assert clump["split"] == "pot"
    assert out["look"] == 1
    assert out["divide"] == 1
    assert out["pot"] == 1
    assert out["skip"] == 1
