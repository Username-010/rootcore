"""Group watering-due rows into a printable can (overdue / due / soon)."""

from __future__ import annotations

from datetime import datetime
from typing import Any


URGENCY_ORDER = ("overdue", "due", "soon")


def _emoji(plant: Any) -> str:
    attrs = getattr(plant, "custom_attributes", None) or {}
    raw = attrs.get("emoji") if isinstance(attrs, dict) else None
    if isinstance(raw, str) and raw.strip():
        return raw.strip()[:8]
    return "🪴"


def plant_row(plant: Any, state: Any) -> dict[str, Any]:
    due = getattr(state, "next_due_at", None)
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": getattr(plant, "environment", None) or "indoor",
        "urgency": state.urgency,
        "next_due_at": due.isoformat() if due is not None else None,
        "recommended_amount": getattr(state, "recommended_amount", None),
    }


def build_due_can(
    rows: list[tuple[Any, Any]],
    *,
    timezone: str,
    now: datetime,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {k: [] for k in URGENCY_ORDER}
    for plant, state in rows:
        urgency = state.urgency if state.urgency in groups else "soon"
        groups[urgency].append(plant_row(plant, state))

    counts = {k: len(v) for k, v in groups.items()}
    total = sum(counts.values())
    if total == 0:
        summary = "Can is empty — nothing thirsty right now."
    else:
        bits = [f"{counts[k]} {k}" for k in URGENCY_ORDER if counts[k]]
        summary = "Water now: " + ", ".join(bits) + "."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "summary": summary,
        "groups": groups,
        "counts": counts,
        "total": total,
    }
