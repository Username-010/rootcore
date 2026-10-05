"""Group active plants into a printable harden-off list."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_SKIP_MARKERS = (
    "orchid",
    "phalaenopsis",
    "bonsai",
    "monstera",
    "fiddle",
    "ficus lyrata",
    "snake plant",
    "sansevieria",
    "zz plant",
    "zamioculcas",
    "peace lily",
    "spathiphyllum",
)

_WIND_MARKERS = (
    "tomato",
    "pepper",
    "chilli",
    "chili",
    "bean",
    "pea",
    "squash",
    "pumpkin",
    "courgette",
    "zucchini",
    "sunflower",
    "sweet pea",
    "broad bean",
)

_SHADE_MARKERS = (
    "basil",
    "lettuce",
    "parsley",
    "coriander",
    "cilantro",
    "herb",
    "seed",
    "seedling",
    "marigold",
    "cosmos",
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
        harden = "skip"
        harden_label = "Stay inside. This one does not harden off."
        skip = True
    elif any(m in blob for m in _WIND_MARKERS):
        harden = "wind"
        harden_label = "Shade first, then a little wind."
        skip = False
    elif any(m in blob for m in _SHADE_MARKERS):
        harden = "shade"
        harden_label = "An hour in shade, then back in."
        skip = False
    else:
        harden = "look"
        harden_label = "Look at the stem. Harden only if it lived indoors."
        skip = False
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "harden": harden,
        "harden_label": harden_label,
        "skip": skip,
    }


def build_harden_list(
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
    look = sum(1 for r in rows if r["harden"] == "look")
    shade = sum(1 for r in rows if r["harden"] == "shade")
    wind = sum(1 for r in rows if r["harden"] == "wind")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the harden list at {home}."
    else:
        summary = f"{total} plants on the harden list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "look": look,
        "shade": shade,
        "wind": wind,
        "skip": skip,
    }
