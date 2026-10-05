"""Group active plants into a printable fertiliser mix sheet."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_SKIP_MARKERS = (
    "cactus",
    "succulent",
    "aloe",
    "haworthia",
    "echeveria",
    "sedum",
    "sansevieria",
    "snake plant",
    "zz plant",
    "zamioculcas",
    "orchid",
    "phalaenopsis",
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
        strength = "skip"
        mix_label = "Skip feed. Water only this round."
    elif str(env).lower() == "outdoor":
        strength = "full"
        mix_label = "Full strength outdoors, then rinse leaves"
    else:
        strength = "half"
        mix_label = "Half strength in the can, then wait a week"
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "strength": strength,
        "mix_label": mix_label,
        "skip": skip,
    }


def build_feed_mix(
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
    half = sum(1 for r in rows if r["strength"] == "half")
    full = sum(1 for r in rows if r["strength"] == "full")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the feed mix at {home}."
    else:
        summary = f"{total} plants on the feed mix at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "half": half,
        "full": full,
        "skip": skip,
    }
