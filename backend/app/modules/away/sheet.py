"""Group active plants into a printable house-sitter away sheet."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _emoji(plant: Any) -> str:
    attrs = getattr(plant, "custom_attributes", None) or {}
    raw = attrs.get("emoji") if isinstance(attrs, dict) else None
    if isinstance(raw, str) and raw.strip():
        return raw.strip()[:8]
    return "🪴"


def _clip(text: str | None, limit: int = 160) -> str | None:
    if not text or not str(text).strip():
        return None
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def plant_row(plant: Any) -> dict[str, Any]:
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": getattr(plant, "environment", None) or "indoor",
        "notes": _clip(getattr(plant, "notes", None)),
        "pot_size_liters": getattr(plant, "pot_size_liters", None),
        "soil_type": getattr(plant, "soil_type", None),
    }


def build_away_sheet(
    plants: list[Any],
    *,
    timezone: str,
    now: datetime,
    household_name: str | None = None,
) -> dict[str, Any]:
    rows = [plant_row(p) for p in plants]
    total = len(rows)
    home = (household_name or "this home").strip() or "this home"
    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant to look after at {home}."
    else:
        summary = f"{total} plants to look after at {home}."
    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
    }
