"""Group active plants into a printable harvest list."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_SKIP_MARKERS = (
    "succulent",
    "cactus",
    "aloe",
    "haworthia",
    "echeveria",
    "sedum",
    "lithops",
    "orchid",
    "phalaenopsis",
    "monstera",
    "pothos",
    "epipremnum",
    "ficus",
    "lyrata",
    "rubber",
)

_LEAF_MARKERS = (
    "basil",
    "basilicum",
    "mint",
    "munt",
    "parsley",
    "peterselie",
    "cilantro",
    "koriander",
    "chive",
    "bieslook",
    "oregano",
    "thyme",
    "tijm",
    "sage",
    "salie",
    "rosemary",
    "rozemarijn",
    "lettuce",
    "sla",
    "spinach",
    "spinazie",
    "kale",
    "boerenkool",
)

_FRUIT_MARKERS = (
    "tomato",
    "tomaat",
    "pepper",
    "paprika",
    "chili",
    "chilli",
    "capsicum",
    "strawberry",
    "aardbei",
    "cucumber",
    "komkommer",
    "bean",
    "boon",
    "pea",
    "erwt",
    "courgette",
    "zucchini",
    "aubergine",
    "eggplant",
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
        harvest = "skip"
        harvest_label = "Houseplant, not food. Leave it on the shelf."
    elif any(m in blob for m in _LEAF_MARKERS):
        harvest = "leaf"
        harvest_label = "Snip a little, leave the plant. Rinse, then bag."
    elif any(m in blob for m in _FRUIT_MARKERS):
        harvest = "fruit"
        harvest_label = "Pick ripe only. Twist, don't yank. Leave green ones."
    else:
        harvest = "look"
        harvest_label = "Look once. Only pick if it is clearly edible and ready."
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "harvest": harvest,
        "harvest_label": harvest_label,
        "skip": skip,
    }


def build_harvest_list(
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
    leaf = sum(1 for r in rows if r["harvest"] == "leaf")
    fruit = sum(1 for r in rows if r["harvest"] == "fruit")
    look = sum(1 for r in rows if r["harvest"] == "look")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the harvest list at {home}."
    else:
        summary = f"{total} plants on the harvest list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "leaf": leaf,
        "fruit": fruit,
        "look": look,
        "skip": skip,
    }
