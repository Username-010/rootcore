"""Group active plants into a printable split list."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_SKIP_MARKERS = (
    "orchid",
    "phalaenopsis",
    "dendrobium",
    "cattleya",
    "oncidium",
    "tillandsia",
    "air plant",
    "bonsai",
    "cactus",
    "lithops",
    "mushroom",
    "fungus",
    "aquatic",
    "pond",
    "aquarium",
)

_DIVIDE_MARKERS = (
    "spider plant",
    "chlorophytum",
    "snake plant",
    "sansevieria",
    "dracaena trifasciata",
    "peace lily",
    "spathiphyllum",
    "aloe",
    "agave",
    "hosta",
    "aspidistra",
    "cast iron",
    "fern",
    "nephrolepis",
    "calathea",
    "maranta",
    "prayer plant",
    "zz plant",
    "zamioculcas",
)

_POT_MARKERS = (
    "clump",
    "crowded",
    "rootbound",
    "root bound",
    "pups",
    "offsets",
    "division",
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
        split = "skip"
        split_label = "Do not split. Leave it as one plant."
        skip = True
    elif any(m in blob for m in _DIVIDE_MARKERS):
        split = "divide"
        split_label = "Two pots, then one plant."
        skip = False
    elif any(m in blob for m in _POT_MARKERS):
        split = "pot"
        split_label = "Tease the clump, then pot each piece."
        skip = False
    else:
        split = "look"
        split_label = "Look at the roots. Split only if packed."
        skip = False
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "split": split,
        "split_label": split_label,
        "skip": skip,
    }


def build_split_list(
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
    look = sum(1 for r in rows if r["split"] == "look")
    divide = sum(1 for r in rows if r["split"] == "divide")
    pot = sum(1 for r in rows if r["split"] == "pot")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the split list at {home}."
    else:
        summary = f"{total} plants on the split list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "look": look,
        "divide": divide,
        "pot": pot,
        "skip": skip,
    }
