"""Group active plants into a printable nursery-run shopping list."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


def _emoji(plant: Any) -> str:
    attrs = getattr(plant, "custom_attributes", None) or {}
    raw = attrs.get("emoji") if isinstance(attrs, dict) else None
    if isinstance(raw, str) and raw.strip():
        return raw.strip()[:8]
    return "🪴"


def _soil(plant: Any) -> str:
    raw = getattr(plant, "soil_type", None)
    if raw and str(raw).strip():
        return str(raw).strip()
    return "unspecified mix"


def plant_row(plant: Any) -> dict[str, Any]:
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": getattr(plant, "environment", None) or "indoor",
        "pot_size_liters": getattr(plant, "pot_size_liters", None),
        "soil_type": _soil(plant),
        "need_soil": True,
        "need_pot": getattr(plant, "pot_size_liters", None) is None,
        "need_feed": True,
    }


def build_nursery_run(
    plants: list[Any],
    *,
    timezone: str,
    now: datetime,
    household_name: str | None = None,
) -> dict[str, Any]:
    rows = [plant_row(p) for p in plants]
    total = len(rows)
    home = (household_name or "this home").strip() or "this home"

    soils: dict[str, int] = defaultdict(int)
    for row in rows:
        soils[row["soil_type"]] += 1
    soil_bags = [
        {"soil_type": name, "plants": count, "bags": max(1, (count + 2) // 3)}
        for name, count in sorted(soils.items(), key=lambda kv: kv[0].lower())
    ]

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant to shop for at {home}."
    else:
        summary = f"{total} plants to shop for at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "soils": soil_bags,
        "total": total,
        "soil_kinds": len(soil_bags),
    }
