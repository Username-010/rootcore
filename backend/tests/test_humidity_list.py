"""Unit tests for the printable humidity list."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.humidity.sheet import build_humidity_list


def test_empty_list():
    out = build_humidity_list(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_look_pebble_humid_and_skip():
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
            nickname="Calathea",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Calathea orbifolia", common_names=[]),
            custom_attributes={},
        ),
        SimpleNamespace(
            id="c",
            nickname="Moth orchid",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Phalaenopsis amabilis", common_names=[]),
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
    out = build_humidity_list(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 4
    assert "4 plants on the humidity list at Loft" in out["summary"]
    aloe = next(p for p in out["plants"] if p["nickname"] == "Aloe")
    assert aloe["skip"] is True
    cal = next(p for p in out["plants"] if p["nickname"] == "Calathea")
    assert cal["humidity"] == "pebble"
    assert "Pebble tray, skip the soak" in cal["humidity_label"]
    orch = next(p for p in out["plants"] if p["nickname"] == "Moth orchid")
    assert orch["humidity"] == "humid"
    mystery = next(p for p in out["plants"] if p["nickname"] == "Mystery plant")
    assert mystery["humidity"] == "look"
    assert out["look"] == 1
    assert out["pebble"] == 1
    assert out["humid"] == 1
    assert out["skip"] == 1
