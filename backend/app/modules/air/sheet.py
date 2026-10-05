"""Group active plants into a printable airflow list."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_SKIP_MARKERS = (
    "calathea",
    "maranta",
    "prayer plant",
    "african violet",
    "saintpaulia",
    "orchid",
    "phalaenopsis",
)

_FAN_MARKERS = (
    "tomato",
    "pepper",
    "chilli",
    "chili",
    "seedling",
    "seed",
    "herb",
    "basil",
    "mint",
)

_DRAFT_MARKERS = (
    "monstera",
    "pothos",
    "epipremnum",
    "ficus",
    "rubber",
    "philodendron",
    "zz plant",
    "zamioculcas",
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
    if any(m in blob for m in _SKIP_MARKERS):
        air = "skip"
        air_label = "Skip the blast. This one hates a cold draught."
        skip = True
    elif any(m in blob for m in _FAN_MARKERS):
        air = "fan"
        air_label = "A little fan, then wait. Keep mould off the leaves."
        skip = False
    elif any(m in blob for m in _DRAFT_MARKERS):
        air = "draft"
        air_label = "Open a gap, skip the blast."
        skip = False
    else:
        air = "look"
        air_label = "Look at the room. Open a gap only if the air is still."
        skip = False
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "air": air,
        "air_label": air_label,
        "skip": skip,
    }


def build_air_list(
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
    look = sum(1 for r in rows if r["air"] == "look")
    draft = sum(1 for r in rows if r["air"] == "draft")
    fan = sum(1 for r in rows if r["air"] == "fan")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the airflow list at {home}."
    else:
        summary = f"{total} plants on the airflow list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "look": look,
        "draft": draft,
        "fan": fan,
        "skip": skip,
    }
