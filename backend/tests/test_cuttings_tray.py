"""Unit tests for the printable cuttings tray."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.cuttings.sheet import build_cuttings_tray


def test_empty_tray():
    out = build_cuttings_tray(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 0
    assert "no plants" in out["summary"].lower()
    assert out["household_name"] == "Loft"
    assert out["water_jars"] == 0


def test_indoor_water_outdoor_soil():
    plants = [
        SimpleNamespace(
            id="a",
            nickname="Basil",
            environment="indoor",
            taxon=SimpleNamespace(scientific_name="Ocimum basilicum", common_names=[]),
            custom_attributes={"emoji": "🌿"},
            propagated_from_plant_id=None,
        ),
        SimpleNamespace(
            id="b",
            nickname="Tomato",
            environment="outdoor",
            taxon=None,
            custom_attributes={},
            propagated_from_plant_id="parent",
        ),
    ]
    out = build_cuttings_tray(
        plants,
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        household_name="Loft",
    )
    assert out["total"] == 2
    assert "2 plants you can take a cutting from at Loft" in out["summary"]
    basil = next(p for p in out["plants"] if p["nickname"] == "Basil")
    assert basil["method"] == "water"
    assert basil["method_label"] == "water jar"
    assert basil["scientific_name"] == "Ocimum basilicum"
    tomato = next(p for p in out["plants"] if p["nickname"] == "Tomato")
    assert tomato["method"] == "soil"
    assert tomato["already_child"] is True
    assert out["water_jars"] == 1
    assert out["soil_pots"] == 1
