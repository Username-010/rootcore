"""Group active plants into a printable mulch list."""

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

_MULCH_MARKERS = (
    "tomato",
    "pepper",
    "chilli",
    "chili",
    "rose",
    "shrub",
    "blueberry",
    "raspberry",
    "courgette",
    "zucchini",
    "squash",
    "pumpkin",
    "bean",
    "pea",
)

_CROWN_MARKERS = (
    "hosta",
    "strawberry",
    "lettuce",
    "strawberry",
    "heuchera",
    "primrose",
    "primula",
    "violet",
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
        mulch = "skip"
        mulch_label = "Leave the mix bare. This one does not want mulch."
        skip = True
    elif any(m in blob for m in _MULCH_MARKERS):
        mulch = "mulch"
        mulch_label = "Cover the soil, leave the crown."
        skip = False
    elif any(m in blob for m in _CROWN_MARKERS):
        mulch = "crown"
        mulch_label = "A thin ring only. Keep the crown dry."
        skip = False
    else:
        mulch = "look"
        mulch_label = "Look at the soil. Mulch only if it dries too fast."
        skip = False
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "mulch": mulch,
        "mulch_label": mulch_label,
        "skip": skip,
    }


def build_mulch_list(
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
    look = sum(1 for r in rows if r["mulch"] == "look")
    crown = sum(1 for r in rows if r["mulch"] == "crown")
    mulch = sum(1 for r in rows if r["mulch"] == "mulch")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the mulch list at {home}."
    else:
        summary = f"{total} plants on the mulch list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "look": look,
        "crown": crown,
        "mulch": mulch,
        "skip": skip,
    }
