"""Group active plants into a printable potting-on bench."""

from __future__ import annotations

from datetime import datetime
from typing import Any


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


def _next_pot_liters(current: float | None) -> float | None:
    if current is None:
        return None
    try:
        value = float(current)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return 2.0
    bump = 2.0 if value < 10 else 5.0
    return round(value + bump, 1)


def plant_row(plant: Any) -> dict[str, Any]:
    current = getattr(plant, "pot_size_liters", None)
    try:
        current_f = float(current) if current is not None else None
    except (TypeError, ValueError):
        current_f = None
    nxt = _next_pot_liters(current_f)
    if nxt is None:
        next_label = "measure the pot, then go one size up"
    else:
        next_label = f"{nxt:g} L pot"
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": getattr(plant, "environment", None) or "indoor",
        "scientific_name": _taxon_name(plant),
        "pot_size_liters": current_f,
        "pot_material": getattr(plant, "pot_material", None),
        "next_pot_liters": nxt,
        "next_label": next_label,
        "needs_measure": nxt is None,
    }


def build_repot_bench(
    plants: list[Any],
    *,
    timezone: str,
    now: datetime,
    household_name: str | None = None,
) -> dict[str, Any]:
    rows = [plant_row(p) for p in plants]
    total = len(rows)
    home = (household_name or "this home").strip() or "this home"
    measure = sum(1 for r in rows if r["needs_measure"])
    sized = total - measure

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant you can pot on at {home}."
    else:
        summary = f"{total} plants you can pot on at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "sized": sized,
        "needs_measure": measure,
    }
