"""Group active plants into a printable groom list."""

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
    "mushroom",
    "fungus",
    "aquatic",
    "pond",
    "aquarium",
)

_BLOOM_MARKERS = (
    "orchid",
    "phalaenopsis",
    "african violet",
    "saintpaulia",
    "rose",
    "rosa",
    "geranium",
    "pelargonium",
    "hibiscus",
    "jasmine",
    "begonia",
    "fuchsia",
    "camellia",
    "azalea",
)

_FERN_MARKERS = (
    "fern",
    "nephrolepis",
    "maidenhair",
    "adiantum",
    "asplenium",
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
        groom = "skip"
        groom_label = "No grooming. Leave the spines."
        skip = True
    elif any(m in blob for m in _FERN_MARKERS):
        groom = "yellow"
        groom_label = "Brown frond only, leave the green."
        skip = False
    elif any(m in blob for m in _BLOOM_MARKERS):
        groom = "bloom"
        groom_label = "Snip spent blooms, leave the bud."
        skip = False
    else:
        groom = "yellow"
        groom_label = "Yellow leaf, then the spent bloom."
        skip = False
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "groom": groom,
        "groom_label": groom_label,
        "skip": skip,
    }


def build_groom_list(
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
    yellow = sum(1 for r in rows if r["groom"] == "yellow")
    bloom = sum(1 for r in rows if r["groom"] == "bloom")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the groom list at {home}."
    else:
        summary = f"{total} plants on the groom list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "yellow": yellow,
        "bloom": bloom,
        "skip": skip,
    }
