"""Group active plants into a printable quarter-turn list."""

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
    "hanging",
    "trailing",
    "pothos",
    "epipremnum",
    "string of",
    "senecio",
)

_HALF_MARKERS = (
    "palm",
    "areca",
    "kentia",
    "chamaedorea",
    "dracaena",
    "yucca",
    "fiddle",
    "lyrata",
    "bird of paradise",
    "strelitzia",
    "schefflera",
    "umbrella",
    "ficus",
    "elastica",
    "rubber",
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
        rotate = "skip"
        rotate_label = "Leave it. Trailing, succulent, or outdoor — no turn."
    elif any(m in blob for m in _HALF_MARKERS):
        rotate = "half"
        rotate_label = "Half turn this week. Heavy pot: slide, do not lift."
    else:
        rotate = "quarter"
        rotate_label = "Quarter turn toward the glass. Mark the rim first."
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "rotate": rotate,
        "rotate_label": rotate_label,
        "skip": skip,
    }


def build_rotate_list(
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
    quarter = sum(1 for r in rows if r["rotate"] == "quarter")
    half = sum(1 for r in rows if r["rotate"] == "half")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the rotate list at {home}."
    else:
        summary = f"{total} plants on the rotate list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "quarter": quarter,
        "half": half,
        "skip": skip,
    }
