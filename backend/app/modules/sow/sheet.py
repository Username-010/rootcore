"""Group active plants into a printable sow list."""

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

_COVER_MARKERS = (
    "bean",
    "pea",
    "squash",
    "pumpkin",
    "courgette",
    "zucchini",
    "sunflower",
    "nasturtium",
    "sweet pea",
    "broad bean",
)

_SOW_MARKERS = (
    "tomato",
    "pepper",
    "chilli",
    "chili",
    "basil",
    "lettuce",
    "parsley",
    "coriander",
    "cilantro",
    "marigold",
    "cosmos",
    "herb",
    "seed",
    "seedling",
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
        sow = "skip"
        sow_label = "Do not sow. This one is already a plant."
        skip = True
    elif any(m in blob for m in _COVER_MARKERS):
        sow = "cover"
        sow_label = "Cover the seed, then wait."
        skip = False
    elif any(m in blob for m in _SOW_MARKERS):
        sow = "sow"
        sow_label = "Surface sow, then a fine mist."
        skip = False
    else:
        sow = "look"
        sow_label = "Look at the packet. Sow only if you want more."
        skip = False
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "sow": sow,
        "sow_label": sow_label,
        "skip": skip,
    }


def build_sow_list(
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
    look = sum(1 for r in rows if r["sow"] == "look")
    sow = sum(1 for r in rows if r["sow"] == "sow")
    cover = sum(1 for r in rows if r["sow"] == "cover")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the sow list at {home}."
    else:
        summary = f"{total} plants on the sow list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "look": look,
        "sow": sow,
        "cover": cover,
        "skip": skip,
    }
