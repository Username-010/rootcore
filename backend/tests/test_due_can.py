"""Unit tests for the due-can grouping helper."""

from datetime import UTC, datetime
from types import SimpleNamespace

from app.modules.watering.due_can import build_due_can


def test_empty_can():
    out = build_due_can(
        [],
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
    )
    assert out["total"] == 0
    assert out["counts"]["overdue"] == 0
    assert "empty" in out["summary"].lower()


def test_groups_overdue_due_soon():
    plants = [
        SimpleNamespace(id="a", nickname="Basil", environment="indoor", custom_attributes={"emoji": "🌿"}),
        SimpleNamespace(id="b", nickname="Tomato", environment="outdoor", custom_attributes={}),
        SimpleNamespace(id="c", nickname="Fern", environment="indoor", custom_attributes=None),
    ]
    states = [
        SimpleNamespace(urgency="overdue", next_due_at=datetime(2026, 10, 4, tzinfo=UTC), recommended_amount="cup"),
        SimpleNamespace(urgency="due", next_due_at=datetime(2026, 10, 5, tzinfo=UTC), recommended_amount="deep"),
        SimpleNamespace(urgency="soon", next_due_at=None, recommended_amount=None),
    ]
    out = build_due_can(
        list(zip(plants, states, strict=True)),
        timezone="Europe/Amsterdam",
        now=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
    )
    assert out["total"] == 3
    assert out["groups"]["overdue"][0]["nickname"] == "Basil"
    assert out["groups"]["overdue"][0]["emoji"] == "🌿"
    assert out["groups"]["due"][0]["environment"] == "outdoor"
    assert out["groups"]["soon"][0]["next_due_at"] is None
    assert "1 overdue" in out["summary"]
    assert "1 due" in out["summary"]
