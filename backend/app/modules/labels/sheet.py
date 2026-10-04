"""Group active plants into a printable label sheet."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _emoji(plant: Any) -> str:
    attrs = getattr(plant, "custom_attributes", None) or {}
    raw = attrs.get("emoji") if isinstance(attrs, dict) else None
    if isinstance(raw, str) and raw.strip():
        return raw.strip()[:8]
    return "🪴"


def _common_name(taxon: Any) -> str | None:
    if taxon is None:
        return None
    names = getattr(taxon, "common_names", None) or []
    if not names:
        return None
    first = names[0]
    return first if isinstance(first, str) else str(first)


def plant_card(plant: Any) -> dict[str, Any]:
    taxon = getattr(plant, "taxon", None)
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": getattr(plant, "environment", None) or "indoor",
        "scientific_name": getattr(taxon, "scientific_name", None) if taxon else None,
        "common_name": _common_name(taxon),
    }


def build_label_sheet(
    plants: list[Any],
    *,
    timezone: str,
    now: datetime,
) -> dict[str, Any]:
    cards = [plant_card(p) for p in plants]
    total = len(cards)
    if total == 0:
        summary = "No plants to label yet."
    elif total == 1:
        summary = "1 plant label ready to print."
    else:
        summary = f"{total} plant labels ready to print."
    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "summary": summary,
        "cards": cards,
        "total": total,
    }
