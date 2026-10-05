"""Group active plants into a printable cuttings / propagation tray."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _emoji(plant: Any) -> str:
    attrs = getattr(plant, "custom_attributes", None) or {}
    raw = attrs.get("emoji") if isinstance(attrs, dict) else None
    if isinstance(raw, str) and raw.strip():
        return raw.strip()[:8]
    return "🪴"


def _taxon_name(plant: Any) -> str | None:
    taxon = getattr(plant, "taxon", None)
    if taxon is None:
        return None
    sci = getattr(taxon, "scientific_name", None)
    if sci and str(sci).strip():
        return str(sci).strip()
    names = getattr(taxon, "common_names", None) or []
    if names:
        return str(names[0]).strip()
    return None


def _method(plant: Any) -> str:
    env = (getattr(plant, "environment", None) or "indoor").lower()
    if env == "outdoor":
        return "soil"
    return "water"


def plant_row(plant: Any) -> dict[str, Any]:
    method = _method(plant)
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": getattr(plant, "environment", None) or "indoor",
        "scientific_name": _taxon_name(plant),
        "method": method,
        "method_label": "water jar" if method == "water" else "soil / division",
        "already_child": getattr(plant, "propagated_from_plant_id", None) is not None,
    }


def build_cuttings_tray(
    plants: list[Any],
    *,
    timezone: str,
    now: datetime,
    household_name: str | None = None,
) -> dict[str, Any]:
    rows = [plant_row(p) for p in plants]
    total = len(rows)
    home = (household_name or "this home").strip() or "this home"
    water = sum(1 for r in rows if r["method"] == "water")
    soil = total - water

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant you can take a cutting from at {home}."
    else:
        summary = f"{total} plants you can take a cutting from at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "water_jars": water,
        "soil_pots": soil,
    }
