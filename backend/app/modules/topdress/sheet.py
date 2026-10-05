"""Group active plants into a printable topdress list."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_SKIP_MARKERS = (
    "orchid",
    "phalaenopsis",
    "cactus",
    "succulent",
    "echeveria",
    "aloe",
    "air plant",
    "tillandsia",
    "bonsai",
    "venus",
)

_TOPDRESS_MARKERS = (
    "tomato",
    "pepper",
    "chilli",
    "chili",
    "rose",
    "blueberry",
    "raspberry",
    "basil",
    "mint",
    "herb",
    "courgette",
    "zucchini",
)

_THIN_MARKERS = (
    "seedling",
    "seed",
    "plug",
    "cutting",
    "starter",
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
        topdress = "skip"
        topdress_label = "Leave the mix. This one does not want a topdress."
        skip = True
    elif any(m in blob for m in _THIN_MARKERS):
        topdress = "thin"
        topdress_label = "A thin dusting only. Do not bury the stem."
        skip = False
    elif any(m in blob for m in _TOPDRESS_MARKERS):
        topdress = "topdress"
        topdress_label = "Fresh mix on top, leave the stem."
        skip = False
    else:
        topdress = "look"
        topdress_label = "Look at the mix. Topdress only if the surface is tired."
        skip = False
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "topdress": topdress,
        "topdress_label": topdress_label,
        "skip": skip,
    }


def build_topdress_list(
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
    look = sum(1 for r in rows if r["topdress"] == "look")
    thin = sum(1 for r in rows if r["topdress"] == "thin")
    topdress = sum(1 for r in rows if r["topdress"] == "topdress")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the topdress list at {home}."
    else:
        summary = f"{total} plants on the topdress list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "look": look,
        "thin": thin,
        "topdress": topdress,
        "skip": skip,
    }
