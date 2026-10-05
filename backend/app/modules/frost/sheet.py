"""Group active plants into a printable frost list."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_SKIP_MARKERS = (
    "mushroom",
    "fungus",
    "aquatic",
    "pond",
    "aquarium",
)

_HARDY_MARKERS = (
    "boxwood",
    "buxus",
    "ivy",
    "hedera",
    "lavender",
    "lavendel",
    "rosemary",
    "rozemarijn",
    "heuchera",
    "helleborus",
    "holly",
    "ilex",
    "conifer",
    "pine",
    "spruce",
)

_DRY_MARKERS = (
    "succulent",
    "cactus",
    "aloe",
    "haworthia",
    "echeveria",
    "sedum",
    "lithops",
    "agave",
    "jade",
    "crassula",
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
    skip = any(m in blob for m in _SKIP_MARKERS) or str(env).lower() == "indoor"
    if skip:
        frost = "skip"
        frost_label = "Already indoors. Leave the window shut."
        if any(m in blob for m in _SKIP_MARKERS):
            frost_label = "Not a frost plant. Leave the tank alone."
    elif any(m in blob for m in _HARDY_MARKERS):
        frost = "cover"
        frost_label = "Fleece overnight. Do not soak the crown."
    elif any(m in blob for m in _DRY_MARKERS):
        frost = "dry"
        frost_label = "Keep the mix dry, then a porch or garage."
    else:
        frost = "bring"
        frost_label = "Bring in before frost, then wait."
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "frost": frost,
        "frost_label": frost_label,
        "skip": skip,
    }


def build_frost_list(
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
    bring = sum(1 for r in rows if r["frost"] == "bring")
    cover = sum(1 for r in rows if r["frost"] == "cover")
    dry = sum(1 for r in rows if r["frost"] == "dry")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the frost list at {home}."
    else:
        summary = f"{total} plants on the frost list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "bring": bring,
        "cover": cover,
        "dry": dry,
        "skip": skip,
    }
