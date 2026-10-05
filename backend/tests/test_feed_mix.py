"""Unit tests for the printable feed mix."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.feed.sheet import build_feed_mix


def test_empty_mix():
    out = build_feed_mix(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["skip"] == 0


def test_half_full_and_skip():
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
            nickname="Olive",
            environment="outdoor",
            taxon=None,
            custom_attributes={},
        ),
        SimpleNamespace(
            id="c",
            nickname="Aloe",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Aloe vera", common_names=[]),
            custom_attributes={},
        ),
    ]
    out = build_feed_mix(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 3
    assert "3 plants on the feed mix at Loft" in out["summary"]
    monstera = next(p for p in out["plants"] if p["nickname"] == "Monstera")
    assert monstera["strength"] == "half"
    assert "Half strength" in monstera["mix_label"]
    olive = next(p for p in out["plants"] if p["nickname"] == "Olive")
    assert olive["strength"] == "full"
    aloe = next(p for p in out["plants"] if p["nickname"] == "Aloe")
    assert aloe["skip"] is True
    assert aloe["strength"] == "skip"
    assert out["half"] == 1
    assert out["full"] == 1
    assert out["skip"] == 1
