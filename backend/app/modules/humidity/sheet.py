"""Group active plants into a printable humidity list."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_SKIP_MARKERS = (
    "cactus",
    "succulent",
    "sansevieria",
    "snake plant",
    "zz plant",
    "zamioculcas",
    "aloe",
    "jade",
    "echeveria",
    "haworthia",
)

_PEBBLE_MARKERS = (
    "fern",
    "nephrolepis",
    "calathea",
    "maranta",
    "prayer plant",
    "boston",
    "maidenhair",
    "adiantum",
)

_HUMID_MARKERS = (
    "orchid",
    "phalaenopsis",
    "anthurium",
    "fittonia",
    "nerve plant",
    "alocasia",
    "caladium",
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
        humidity = "skip"
        humidity_label = "Skip the soak. Dry air is fine for this one."
        skip = True
    elif any(m in blob for m in _PEBBLE_MARKERS):
        humidity = "pebble"
        humidity_label = "Pebble tray, skip the soak."
        skip = False
    elif any(m in blob for m in _HUMID_MARKERS):
        humidity = "humid"
        humidity_label = "Group it, then a pebble tray. Keep the crown dry."
        skip = False
    else:
        humidity = "look"
        humidity_label = "Look at the room. Add a tray only if the air is dry."
        skip = False
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "humidity": humidity,
        "humidity_label": humidity_label,
        "skip": skip,
    }


def build_humidity_list(
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
    look = sum(1 for r in rows if r["humidity"] == "look")
    pebble = sum(1 for r in rows if r["humidity"] == "pebble")
    humid = sum(1 for r in rows if r["humidity"] == "humid")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the humidity list at {home}."
    else:
        summary = f"{total} plants on the humidity list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "look": look,
        "pebble": pebble,
        "humid": humid,
        "skip": skip,
    }
