"""Group active plants into a printable light map."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_SKIP_MARKERS = (
    "mushroom",
    "fungus",
    "aquatic",
    "pond",
    "aquarium",
)

_SHADE_MARKERS = (
    "fern",
    "varen",
    "calathea",
    "maranta",
    "prayer",
    "peace lily",
    "spathiphyllum",
    "aglaonema",
    "aspidistra",
    "cast iron",
)

_DIRECT_MARKERS = (
    "succulent",
    "cactus",
    "aloe",
    "haworthia",
    "echeveria",
    "sedum",
    "lithops",
    "tomato",
    "tomaat",
    "basil",
    "basilicum",
    "rosemary",
    "rozemarijn",
    "lavender",
    "lavendel",
)


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


def _blob(plant: Any) -> str:
    nick = str(getattr(plant, "nickname", "") or "")
    sci = _taxon_name(plant) or ""
    return f"{nick} {sci}".lower()


def plant_row(plant: Any) -> dict[str, Any]:
    env = getattr(plant, "environment", None) or "indoor"
    blob = _blob(plant)
    skip = any(m in blob for m in _SKIP_MARKERS)
    if skip:
        light = "skip"
        light_label = "Not a windowsill plant. Leave it where it is."
    elif any(m in blob for m in _SHADE_MARKERS):
        light = "shade"
        light_label = "North or a room back. No noon sun."
    elif any(m in blob for m in _DIRECT_MARKERS):
        light = "direct"
        light_label = "South or west glass. Sheer only if it scorches."
    else:
        light = "bright"
        light_label = "Bright window, skip the scorch. East glass is enough."
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "light": light,
        "light_label": light_label,
        "skip": skip,
    }


def build_light_map(
    plants: list[Any],
    *,
    timezone: str,
    now: datetime,
    household_name: str | None = None,
) -> dict[str, Any]:
    rows = [plant_row(p) for p in plants]
    total = len(rows)
    home = (household_name or "this home").strip() or "this home"
    skip = sum(1 for r in rows if r["skip"])
    shade = sum(1 for r in rows if r["light"] == "shade")
    bright = sum(1 for r in rows if r["light"] == "bright")
    direct = sum(1 for r in rows if r["light"] == "direct")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the light map at {home}."
    else:
        summary = f"{total} plants on the light map at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "shade": shade,
        "bright": bright,
        "direct": direct,
        "skip": skip,
    }
