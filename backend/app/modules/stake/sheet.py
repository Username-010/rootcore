"""Group active plants into a printable stake / support list."""

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
    "outdoor",
    "patio",
    "lawn",
)

_MOSS_MARKERS = (
    "orchid",
    "phalaenopsis",
    "anthurium",
    "philodendron",
    "pothos",
    "epipremnum",
    "monstera",
    "scindapsus",
    "hoya",
    "syngonium",
    "epiphyte",
)

_CANE_MARKERS = (
    "tomato",
    "hibiscus",
    "sunflower",
    "dahlia",
    "pepper",
    "capsicum",
    "bean",
    "pea",
    "cucumber",
    "clematis",
    "rose",
    "fiddle",
    "lyrata",
    "dracaena",
    "yucca",
    "strelitzia",
    "bird of paradise",
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
        stake = "skip"
        stake_label = "No pole. Succulent, cactus, or outdoor — skip this sheet."
    elif any(m in blob for m in _MOSS_MARKERS):
        stake = "moss"
        stake_label = "Moss pole or board. Tie loosely, then check the stem."
    elif any(m in blob for m in _CANE_MARKERS):
        stake = "cane"
        stake_label = "Cane or hoop. One stake, soft tie, slack for growth."
    else:
        stake = "check"
        stake_label = "Look once. Only stake if the stem leans."
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "stake": stake,
        "stake_label": stake_label,
        "skip": skip,
    }


def build_stake_list(
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
    moss = sum(1 for r in rows if r["stake"] == "moss")
    cane = sum(1 for r in rows if r["stake"] == "cane")
    check = sum(1 for r in rows if r["stake"] == "check")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the stake list at {home}."
    else:
        summary = f"{total} plants on the stake list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "moss": moss,
        "cane": cane,
        "check": check,
        "skip": skip,
    }
