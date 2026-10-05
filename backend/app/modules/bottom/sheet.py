"""Group active plants into a printable bottom-water list."""

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
)

_SOAK_MARKERS = (
    "fern",
    "calathea",
    "maranta",
    "peace lily",
    "spathiphyllum",
    "african violet",
    "saintpaulia",
    "peperomia",
    "pilea",
)

_DRAIN_MARKERS = (
    "tomato",
    "pepper",
    "chilli",
    "chili",
    "herb",
    "basil",
    "mint",
    "seedling",
    "seed",
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
        bottom = "skip"
        bottom_label = "Leave the saucer dry. This one does not want a soak from below."
        skip = True
    elif any(m in blob for m in _SOAK_MARKERS):
        bottom = "soak"
        bottom_label = "Soak from below, then drain."
        skip = False
    elif any(m in blob for m in _DRAIN_MARKERS):
        bottom = "drain"
        bottom_label = "A short sit in the saucer, then dump it. Do not leave it wet."
        skip = False
    else:
        bottom = "look"
        bottom_label = "Look at the mix. Bottom-water only if the top is still dry."
        skip = False
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "bottom": bottom,
        "bottom_label": bottom_label,
        "skip": skip,
    }


def build_bottom_list(
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
    look = sum(1 for r in rows if r["bottom"] == "look")
    soak = sum(1 for r in rows if r["bottom"] == "soak")
    drain = sum(1 for r in rows if r["bottom"] == "drain")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the bottom-water list at {home}."
    else:
        summary = f"{total} plants on the bottom-water list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "look": look,
        "soak": soak,
        "drain": drain,
        "skip": skip,
    }
