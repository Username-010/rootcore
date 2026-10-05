"""Group active plants into a printable pest-walk list."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_SKIP_MARKERS = (
    "outdoor",
    "patio",
    "balcony tomato",
)

_ISOLATE_MARKERS = (
    "new ",
    "new-",
    "quarantine",
    "gift",
    "nursery",
    "cutting",
    "just in",
)

_STICKY_MARKERS = (
    "citrus",
    "lemon",
    "lime",
    "orange",
    "hibiscus",
    "rose",
    "pepper",
    "capsicum",
    "tomato",
    "basil",
    "ficus",
    "elastica",
    "oleander",
    "milkweed",
    "asclepias",
    "aphid",
    "calamondin",
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
    skip = any(m in blob for m in _SKIP_MARKERS) or str(env).lower() == "outdoor"
    if skip:
        pest = "skip"
        pest_label = "Garden walk, not this sheet. Outdoor pests stay outside."
    elif any(m in blob for m in _ISOLATE_MARKERS):
        pest = "isolate"
        pest_label = "New or gift plant. Check, then keep it apart for a week."
    elif any(m in blob for m in _STICKY_MARKERS):
        pest = "sticky"
        pest_label = "Aphid magnet. Sticky trap nearby, then wipe the stems."
    else:
        pest = "look"
        pest_label = "Check the underside, then isolate if anything moves."
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "pest": pest,
        "pest_label": pest_label,
        "skip": skip,
    }


def build_pest_walk(
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
    look = sum(1 for r in rows if r["pest"] == "look")
    sticky = sum(1 for r in rows if r["pest"] == "sticky")
    isolate = sum(1 for r in rows if r["pest"] == "isolate")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the pest walk at {home}."
    else:
        summary = f"{total} plants on the pest walk at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "look": look,
        "sticky": sticky,
        "isolate": isolate,
        "skip": skip,
    }
