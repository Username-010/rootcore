"""Unit tests for the printable label sheet helper."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.labels.sheet import build_label_sheet


def test_empty_sheet():
    out = build_label_sheet(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()


def test_cards_include_names_and_emoji():
    plants = [
        SimpleNamespace(
            id="a",
            nickname="Basil",
            environment="indoor",
            custom_attributes={"emoji": "🌿"},
            taxon=SimpleNamespace(scientific_name="Ocimum basilicum", common_names=["Sweet basil"]),
        ),
        SimpleNamespace(
            id="b",
            nickname="Tomato",
            environment="outdoor",
            custom_attributes={},
            taxon=None,
        ),
    ]
    out = build_label_sheet(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
    )
    assert out["total"] == 2
    assert out["cards"][0]["nickname"] == "Basil"
    assert out["cards"][0]["emoji"] == "🌿"
    assert out["cards"][0]["scientific_name"] == "Ocimum basilicum"
    assert out["cards"][0]["common_name"] == "Sweet basil"
    assert out["cards"][1]["environment"] == "outdoor"
    assert out["cards"][1]["scientific_name"] is None
    assert "2 plant labels" in out["summary"]
