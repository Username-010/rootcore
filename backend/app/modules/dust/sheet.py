"""Group active plants into a printable dusty-leaf wipe list."""

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
    "african violet",
    "saintpaulia",
    "gesneriad",
    "rex begonia",
    "begonia rex",
    "fuzzy",
)

_CLOTH_MARKERS = (
    "monstera",
    "ficus",
    "elastica",
    "rubber",
    "philodendron",
    "fiddle",
    "lyrata",
    "bird of paradise",
    "strelitzia",
    "schefflera",
    "umbrella",
)

_DAMP_MARKERS = (
    "palm",
    "areca",
    "kentia",
    "chamaedorea",
    "dracaena",
    "yucca",
    "pothos",
    "epipremnum",
    "spider",
    "chlorophytum",
    "calathea",
    "maranta",
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
        dust = "skip"
        dust_label = "Skip the cloth. Fuzzy, succulent, or outdoor — leave it."
    elif any(m in blob for m in _CLOTH_MARKERS):
        dust = "cloth"
        dust_label = "Soft dry cloth on both sides. Support the leaf."
    elif any(m in blob for m in _DAMP_MARKERS):
        dust = "damp"
        dust_label = "Barely damp cloth. No soap. Let it dry in place."
    else:
        dust = "rinse"
        dust_label = "Quick shower rinse if the sink fits. Else a damp wipe."
    return {
        "plant_id": str(plant.id),
        "nickname": plant.nickname,
        "emoji": _emoji(plant),
        "environment": env,
        "scientific_name": _taxon_name(plant),
        "dust": dust,
        "dust_label": dust_label,
        "skip": skip,
    }


def build_dust_list(
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
    cloth = sum(1 for r in rows if r["dust"] == "cloth")
    damp = sum(1 for r in rows if r["dust"] == "damp")
    rinse = sum(1 for r in rows if r["dust"] == "rinse")

    if total == 0:
        summary = f"No plants listed for {home} yet."
    elif total == 1:
        summary = f"1 plant on the dust list at {home}."
    else:
        summary = f"{total} plants on the dust list at {home}."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "household_name": home,
        "summary": summary,
        "plants": rows,
        "total": total,
        "cloth": cloth,
        "damp": damp,
        "rinse": rinse,
        "skip": skip,
    }
