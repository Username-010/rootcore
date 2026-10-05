"""Unit tests for the printable flush list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.flush.sheet import build_flush_list


def test_empty_list():
    out = build_flush_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_soak_drain_dump_and_skip():
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
            nickname="Orchid",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Phalaenopsis amabilis", common_names=[]),
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
            nickname="Boston fern",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Nephrolepis exaltata", common_names=[]),
            custom_attributes={},
        ),
    ]
    out = build_flush_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the flush list at Loft" in out["summary"]
    mon = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert mon["flush"] == "dump"
    assert "Water through, then dump the saucer" in mon["flush_label"]
    orch = next(p for p in out["plants"] if p["nickname"] == "Orchid")
    assert orch["flush"] == "soak"
    aloe = next(p for p in out["plants"] if p["nickname"] == "Aloe")
    assert aloe["skip"] is True
    fern = next(p for p in out["plants"] if p["nickname"] == "Boston fern")
    assert fern["flush"] == "drain"
    assert out["dump"] == 1
    assert out["soak"] == 1
    assert out["drain"] == 1
    assert out["skip"] == 1
