"""Unit tests for the printable house-sitter away sheet."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.away.sheet import build_away_sheet


def test_empty_sheet():
    out = build_away_sheet(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"


def test_rows_include_notes_and_emoji():
    plants = [
        SimpleNamespace(
            id="a",
            nickname="Basil",
            environment="indoor",
            notes="  Keep soil just damp.  ",
            pot_size_liters=1.5,
            soil_type="herb mix",
            custom_attributes={"emoji": "🌿"},
        ),
        SimpleNamespace(
            id="b",
            nickname="Tomato",
            environment="outdoor",
            notes=None,
            pot_size_liters=None,
            soil_type=None,
            custom_attributes={},
        ),
    ]
    out = build_away_sheet(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 2
    assert out["plants"][0]["nickname"] == "Basil"
    assert out["plants"][0]["emoji"] == "🌿"
    assert out["plants"][0]["notes"] == "Keep soil just damp."
    assert out["plants"][0]["pot_size_liters"] == 1.5
    assert out["plants"][1]["environment"] == "outdoor"
    assert out["plants"][1]["notes"] is None
    assert "2 plants to look after at Loft" in out["summary"]
