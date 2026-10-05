"""Group active plants into a printable flush list."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_SKIP_MARKERS = (
    "cactus",
    "succulent",
    "lithops",
    "haworthia",
    "echeveria",
    "agave",
    "aloe",
    "jade",
    "crassula",
    "sansevieria",
    "snake plant",
    "zz plant",
    "zamioculcas",
    "mushroom",
    "fungus",
    "aquatic",
    "pond",
    "aquarium",
)

_SOAK_MARKERS = (
    "orchid",
    "phalaenopsis",
    "dendrobium",
    "cattleya",
    "oncidium",
    "tillandsia",
    "air plant",
    "epiphyte",
    "staghorn",
    "platycerium",
)

_DRAIN_MARKERS = (
    "fern",
    "nephrolepis",
    "maidenhair",
    "adiantum",
    "asplenium",
    "calathea",
    "maranta",
    "prayer plant",
    "peace lily",
    "spathiphyllum",
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
        flush = "skip"
        flush_label = "Do not flush. Leave the roots dry."
        skip = True
    elif any(m in blob for m in _SOAK_MARKERS):
        flush = "soak"
        flush_label = "Water through the bark, no saucer."
        skip = False
    elif any(m in blob for m in _DRAIN_MARKERS):
        flush = "drain"
        flush_label = "Flush, then dump the saucer now."
        skip = False
    else:
        flush = "dump"
        flush_label = "Water through, then dump the saucer."
        skip = False
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "flush": flush,
        "flush_label": flush_label,
        "skip": skip,
    }


def build_flush_list(
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
    soak = sum(1 for r in rows if r["flush"] == "soak")
    drain = sum(1 for r in rows if r["flush"] == "drain")
    dump = sum(1 for r in rows if r["flush"] == "dump")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the flush list at {home}."
    else:
        summary = f"{total} plants on the flush list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "soak": soak,
        "drain": drain,
        "dump": dump,
        "skip": skip,
    }
