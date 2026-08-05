"""Baseline watering calculator — explainable factors + plain-language care card.

Considers pot, soil, environment, season, heat, humidity, and rain.
Returns when to water (local morning/evening), how much (ml + how-to), and why.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo


@dataclass
class WateringRecommendation:
    next_due_at: datetime
    urgency: str
    recommended_amount: str
    confidence: float
    moisture_score: float
    factor_breakdown: list[dict[str, Any]]
    explanation: str
    # Plain-language care card
    amount_label: str = "Normal water"
    amount_howto: str = ""
    amount_ml: int | None = None
    volume_guide: str = ""
    best_time_of_day: str = "morning"  # morning | evening | either
    best_time_label: str = "Morning"
    best_time_local: str | None = None  # e.g. "around 8:00"
    schedule_plain: str = ""
    weather_note: str | None = None
    interval_days: float = 7.0
    advice: dict[str, Any] = field(default_factory=dict)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _estimate_volume_ml(amount: str, pot_size_liters: float | None) -> int:
    """Rough guide: water volume as fraction of pot volume."""
    pot = pot_size_liters if pot_size_liters and pot_size_liters > 0 else 3.0
    # ml water ≈ pot liters × fraction × 1000
    frac = {"light": 0.12, "normal": 0.22, "deep": 0.35}.get(amount, 0.22)
    ml = int(round(pot * frac * 1000 / 50) * 50)  # nearest 50 ml
    return max(50, min(ml, 8000))


def _amount_howto(amount: str, ml: int | None, pot_size_liters: float | None) -> tuple[str, str, str]:
    pot_note = (
        f" (≈{pot_size_liters:g} L pot)"
        if pot_size_liters and pot_size_liters > 0
        else ""
    )
    vol = f"About **{ml} ml**" if ml else "A moderate pour"
    if amount == "light":
        return (
            "Light water",
            f"{vol}{pot_note}. Moisten the top half of the soil. Stop when a few drops appear at the drainage holes — do not soak fully.",
            f"~{ml} ml · top half moist" if ml else "Light moistening",
        )
    if amount == "deep":
        return (
            "Deep soak",
            f"{vol}{pot_note}. Water slowly until water runs freely from the bottom. Wait 10 minutes, empty the saucer so roots don’t sit in water.",
            f"~{ml} ml · full soak + drain" if ml else "Full soak until drain",
        )
    return (
        "Normal water",
        f"{vol}{pot_note}. Water until a little runs out the bottom, then empty the saucer. Soil should feel evenly moist, not soggy.",
        f"~{ml} ml · until slight runoff" if ml else "Until slight runoff",
    )


def _pick_best_time(
    *,
    environment: str,
    weather_temp_c: float | None,
    weather_precip_24h_mm: float | None,
) -> tuple[str, str, int]:
    """Return (key, label, local_hour). Prefer morning; evening if mild outdoor evening ok."""
    env = (environment or "indoor").lower()
    hot = weather_temp_c is not None and weather_temp_c >= 28
    very_hot = weather_temp_c is not None and weather_temp_c >= 32
    rainy = weather_precip_24h_mm is not None and weather_precip_24h_mm >= 5

    if env == "outdoor":
        if very_hot:
            return "morning", "Early morning (before heat)", 7
        if hot:
            return "morning", "Morning (avoid midday heat)", 8
        if rainy:
            return "either", "Anytime — rain may help outdoor plants", 9
        return "morning", "Morning (best for outdoor)", 8

    if env == "greenhouse":
        if hot:
            return "morning", "Morning (greenhouse warms up fast)", 8
        return "morning", "Morning", 9

    # Indoor — morning is usually best; evening OK if cooler
    if hot:
        return "morning", "Morning (hot day — cooler indoor air earlier)", 8
    return "morning", "Morning (good routine)", 9


def _snap_to_local_hour(dt: datetime, tz_name: str | None, hour: int) -> datetime:
    """Snap UTC datetime to the given local hour on the same local calendar day."""
    try:
        tz = ZoneInfo(tz_name) if tz_name else ZoneInfo("UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    local = dt.astimezone(tz)
    snapped = local.replace(hour=hour, minute=0, second=0, microsecond=0)
    # If we snapped into the past on a "due now" day, keep original day morning next cycle is fine
    return snapped.astimezone(UTC)


def compute_baseline(
    *,
    now: datetime | None = None,
    last_watered_at: datetime | None,
    baseline_min_days: float | None,
    baseline_max_days: float | None,
    pot_size_liters: float | None,
    pot_material: str | None,
    soil_type: str | None,
    environment: str,
    growth_stage: str | None,
    interval_bias_days: float = 0.0,
    waterings_logged: int = 0,
    manual_next_due_at: datetime | None = None,
    paused_until: datetime | None = None,
    weather_temp_c: float | None = None,
    weather_humidity: float | None = None,
    weather_precip_24h_mm: float | None = None,
    timezone: str | None = "UTC",
) -> WateringRecommendation:
    """Compute next watering due using species baseline + modifiers + care card."""
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    factors: list[dict[str, Any]] = []
    weather_bits: list[str] = []

    lo = baseline_min_days if baseline_min_days is not None else 7.0
    hi = baseline_max_days if baseline_max_days is not None else max(lo, 10.0)
    base_days = (lo + hi) / 2.0
    factors.append(
        {
            "key": "species_baseline",
            "label": "Species typical schedule",
            "value": round(base_days, 2),
            "unit": "days",
            "effect": "base",
            "detail": f"Usually every {lo:g}–{hi:g} days",
        }
    )

    multiplier = 1.0

    if pot_size_liters is not None:
        if pot_size_liters < 2:
            multiplier *= 0.8
            factors.append(
                {
                    "key": "pot_size",
                    "label": "Small pot dries faster",
                    "value": 0.8,
                    "unit": "multiplier",
                    "effect": "shorten",
                    "detail": f"{pot_size_liters:g} L",
                }
            )
        elif pot_size_liters > 10:
            multiplier *= 1.15
            factors.append(
                {
                    "key": "pot_size",
                    "label": "Large pot holds moisture longer",
                    "value": 1.15,
                    "unit": "multiplier",
                    "effect": "lengthen",
                    "detail": f"{pot_size_liters:g} L",
                }
            )

    material = (pot_material or "").lower()
    if "terra" in material or "clay" in material:
        multiplier *= 0.85
        factors.append(
            {
                "key": "pot_material",
                "label": "Terracotta / clay dries faster",
                "value": 0.85,
                "unit": "multiplier",
                "effect": "shorten",
                "detail": pot_material,
            }
        )
    elif "plastic" in material or "glazed" in material:
        multiplier *= 1.1
        factors.append(
            {
                "key": "pot_material",
                "label": "Plastic / glazed holds moisture",
                "value": 1.1,
                "unit": "multiplier",
                "effect": "lengthen",
                "detail": pot_material,
            }
        )

    soil = (soil_type or "").lower()
    if "free" in soil or "drain" in soil or "cactus" in soil or "arid" in soil:
        multiplier *= 0.9
        factors.append(
            {
                "key": "soil_type",
                "label": "Fast-draining soil",
                "value": 0.9,
                "unit": "multiplier",
                "effect": "shorten",
                "detail": soil_type,
            }
        )
    elif "moist" in soil or "retent" in soil:
        multiplier *= 1.15
        factors.append(
            {
                "key": "soil_type",
                "label": "Moisture-holding soil",
                "value": 1.15,
                "unit": "multiplier",
                "effect": "lengthen",
                "detail": soil_type,
            }
        )

    env = (environment or "indoor").lower()
    if env == "outdoor":
        multiplier *= 0.85
        factors.append(
            {
                "key": "environment",
                "label": "Outdoor — dries faster",
                "value": 0.85,
                "unit": "multiplier",
                "effect": "shorten",
                "detail": "outdoor",
            }
        )
    elif env == "greenhouse":
        multiplier *= 0.95
        factors.append(
            {
                "key": "environment",
                "label": "Greenhouse",
                "value": 0.95,
                "unit": "multiplier",
                "effect": "shorten",
                "detail": "greenhouse",
            }
        )
    else:
        factors.append(
            {
                "key": "environment",
                "label": "Indoor",
                "value": 1.0,
                "unit": "multiplier",
                "effect": "base",
                "detail": "indoor",
            }
        )

    stage = (growth_stage or "").lower()
    if stage in {"seedling", "juvenile", "young"}:
        multiplier *= 0.9
        factors.append(
            {
                "key": "growth_stage",
                "label": "Young plant needs water more often",
                "value": 0.9,
                "unit": "multiplier",
                "effect": "shorten",
                "detail": growth_stage,
            }
        )

    month = now.month
    if month in (12, 1, 2):
        multiplier *= 1.25
        factors.append(
            {
                "key": "season",
                "label": "Winter — plants drink less",
                "value": 1.25,
                "unit": "multiplier",
                "effect": "lengthen",
                "detail": "winter",
            }
        )
    elif month in (6, 7, 8):
        multiplier *= 0.9
        factors.append(
            {
                "key": "season",
                "label": "Summer — plants drink more",
                "value": 0.9,
                "unit": "multiplier",
                "effect": "shorten",
                "detail": "summer",
            }
        )

    # Weather — stronger outdoors
    weather_weight = 1.0 if env == "outdoor" else 0.4 if env == "greenhouse" else 0.25
    if weather_temp_c is not None:
        weather_bits.append(f"{weather_temp_c:g}°C")
        if weather_temp_c >= 32:
            w = 1.0 - (0.28 * weather_weight)
            multiplier *= w
            factors.append(
                {
                    "key": "weather_temp",
                    "label": "Very hot — soil dries fast",
                    "value": round(w, 3),
                    "unit": "multiplier",
                    "effect": "shorten",
                    "detail": f"{weather_temp_c:g}°C",
                }
            )
        elif weather_temp_c >= 28:
            w = 1.0 - (0.18 * weather_weight)
            multiplier *= w
            factors.append(
                {
                    "key": "weather_temp",
                    "label": "Hot weather — water sooner",
                    "value": round(w, 3),
                    "unit": "multiplier",
                    "effect": "shorten",
                    "detail": f"{weather_temp_c:g}°C",
                }
            )
        elif weather_temp_c >= 24:
            w = 1.0 - (0.08 * weather_weight)
            multiplier *= w
            factors.append(
                {
                    "key": "weather_temp",
                    "label": "Warm weather",
                    "value": round(w, 3),
                    "unit": "multiplier",
                    "effect": "shorten",
                    "detail": f"{weather_temp_c:g}°C",
                }
            )
        elif weather_temp_c <= 5:
            w = 1.0 + (0.22 * weather_weight)
            multiplier *= w
            factors.append(
                {
                    "key": "weather_temp",
                    "label": "Cold — plants need less water",
                    "value": round(w, 3),
                    "unit": "multiplier",
                    "effect": "lengthen",
                    "detail": f"{weather_temp_c:g}°C",
                }
            )
        elif weather_temp_c <= 12:
            w = 1.0 + (0.1 * weather_weight)
            multiplier *= w
            factors.append(
                {
                    "key": "weather_temp",
                    "label": "Cool weather",
                    "value": round(w, 3),
                    "unit": "multiplier",
                    "effect": "lengthen",
                    "detail": f"{weather_temp_c:g}°C",
                }
            )

    if weather_humidity is not None:
        weather_bits.append(f"{weather_humidity:g}% humidity")
        if weather_humidity < 25:
            w = 1.0 - (0.15 * weather_weight)
            multiplier *= w
            factors.append(
                {
                    "key": "weather_humidity",
                    "label": "Very dry air — dries soil faster",
                    "value": round(w, 3),
                    "unit": "multiplier",
                    "effect": "shorten",
                    "detail": f"{weather_humidity:g}%",
                }
            )
        elif weather_humidity < 35:
            w = 1.0 - (0.1 * weather_weight)
            multiplier *= w
            factors.append(
                {
                    "key": "weather_humidity",
                    "label": "Low humidity",
                    "value": round(w, 3),
                    "unit": "multiplier",
                    "effect": "shorten",
                    "detail": f"{weather_humidity:g}%",
                }
            )
        elif weather_humidity > 80:
            w = 1.0 + (0.12 * weather_weight)
            multiplier *= w
            factors.append(
                {
                    "key": "weather_humidity",
                    "label": "High humidity — soil stays wet longer",
                    "value": round(w, 3),
                    "unit": "multiplier",
                    "effect": "lengthen",
                    "detail": f"{weather_humidity:g}%",
                }
            )
        elif weather_humidity > 70:
            w = 1.0 + (0.08 * weather_weight)
            multiplier *= w
            factors.append(
                {
                    "key": "weather_humidity",
                    "label": "Humid air",
                    "value": round(w, 3),
                    "unit": "multiplier",
                    "effect": "lengthen",
                    "detail": f"{weather_humidity:g}%",
                }
            )

    if weather_precip_24h_mm is not None:
        weather_bits.append(f"{weather_precip_24h_mm:g} mm rain/24h")
        if weather_precip_24h_mm >= 8 and env == "outdoor":
            multiplier *= 1.4
            factors.append(
                {
                    "key": "weather_precip",
                    "label": "Significant rain expected — outdoor may wait",
                    "value": 1.4,
                    "unit": "multiplier",
                    "effect": "lengthen",
                    "detail": f"{weather_precip_24h_mm:g} mm next 24h",
                }
            )
        elif weather_precip_24h_mm >= 3 and env == "outdoor":
            multiplier *= 1.2
            factors.append(
                {
                    "key": "weather_precip",
                    "label": "Some rain expected outdoors",
                    "value": 1.2,
                    "unit": "multiplier",
                    "effect": "lengthen",
                    "detail": f"{weather_precip_24h_mm:g} mm next 24h",
                }
            )
        elif weather_precip_24h_mm >= 5 and env != "outdoor":
            factors.append(
                {
                    "key": "weather_precip",
                    "label": "Rain outdoors (little effect indoors)",
                    "value": 1.0,
                    "unit": "multiplier",
                    "effect": "base",
                    "detail": f"{weather_precip_24h_mm:g} mm next 24h",
                }
            )

    if abs(interval_bias_days) > 0.01:
        factors.append(
            {
                "key": "user_learning",
                "label": "Adjusted from your past feedback",
                "value": round(interval_bias_days, 2),
                "unit": "days",
                "effect": "bias",
                "detail": None,
            }
        )

    interval_days = _clamp(base_days * multiplier + interval_bias_days, 1.0, 60.0)

    # Amount
    amount = "normal"
    if soil and ("dry" in soil or "cactus" in soil or "arid" in soil):
        amount = "light"
    if weather_temp_c is not None and weather_temp_c >= 30 and env == "outdoor":
        amount = "deep" if amount != "light" else "normal"
    if pot_size_liters is not None and pot_size_liters >= 8 and amount == "normal":
        amount = "deep"
    if pot_size_liters is not None and pot_size_liters < 1.5 and amount == "deep":
        amount = "normal"

    amount_ml = _estimate_volume_ml(amount, pot_size_liters)
    amount_label, amount_howto, volume_guide = _amount_howto(
        amount, amount_ml, pot_size_liters
    )

    time_key, time_label, local_hour = _pick_best_time(
        environment=env,
        weather_temp_c=weather_temp_c,
        weather_precip_24h_mm=weather_precip_24h_mm,
    )

    if manual_next_due_at is not None:
        due = manual_next_due_at
        if due.tzinfo is None:
            due = due.replace(tzinfo=UTC)
        factors.append(
            {
                "key": "manual_override",
                "label": "You set a custom next-water date",
                "value": due.isoformat(),
                "unit": "datetime",
                "effect": "override",
                "detail": None,
            }
        )
    else:
        anchor = last_watered_at or now
        if anchor.tzinfo is None:
            anchor = anchor.replace(tzinfo=UTC)
        due = anchor + timedelta(days=interval_days)
        due = _snap_to_local_hour(due, timezone, local_hour)

    if paused_until and paused_until > now:
        if paused_until.tzinfo is None:
            paused_until = paused_until.replace(tzinfo=UTC)
        due = max(due, paused_until)
        factors.append(
            {
                "key": "paused",
                "label": "Watering reminders paused",
                "value": paused_until.isoformat(),
                "unit": "datetime",
                "effect": "pause",
                "detail": None,
            }
        )

    if last_watered_at is None:
        moisture = 0.3
    else:
        lw = last_watered_at if last_watered_at.tzinfo else last_watered_at.replace(tzinfo=UTC)
        elapsed = max((now - lw).total_seconds(), 0) / 86400.0
        moisture = _clamp(1.0 - (elapsed / interval_days), 0.0, 1.0)

    hours_until = (due - now).total_seconds() / 3600.0
    if hours_until < -24:
        urgency = "overdue"
    elif hours_until <= 0:
        urgency = "due"
    elif hours_until <= 36:
        urgency = "soon"
    else:
        urgency = "ok"

    confidence = _clamp(0.25 + min(waterings_logged, 12) * 0.05, 0.25, 0.85)

    # Local time label for best_time_local
    best_time_local = f"around {local_hour}:00"
    try:
        tz = ZoneInfo(timezone) if timezone else ZoneInfo("UTC")
        local_due = due.astimezone(tz)
        best_time_local = local_due.strftime("around %H:%M").replace("around 0", "around ")
        # cleaner: always use preferred hour wording
        best_time_local = f"around {local_hour}:00 local time"
    except Exception:
        pass

    # Schedule plain English
    if urgency == "overdue":
        when_plain = f"Water **as soon as you can** — ideally {time_label.lower()}"
    elif urgency == "due":
        when_plain = f"Water **today**, {time_label.lower()} ({best_time_local})"
    elif urgency == "soon":
        when_plain = f"Water **within a day** — {time_label.lower()} ({best_time_local})"
    else:
        try:
            tz = ZoneInfo(timezone) if timezone else ZoneInfo("UTC")
            day = due.astimezone(tz).strftime("%a %d %b")
        except Exception:
            day = due.strftime("%a %d %b")
        when_plain = f"Next water **{day}**, {time_label.lower()} ({best_time_local})"

    schedule_plain = (
        f"{when_plain}. Use **{amount_label.lower()}** (~{amount_ml} ml). "
        f"Typical gap for this plant right now: about **{interval_days:.0f} days** between waterings."
    )

    weather_note = None
    if weather_bits:
        weather_note = "Weather at your location: " + ", ".join(weather_bits)
        if env == "outdoor" and weather_precip_24h_mm and weather_precip_24h_mm >= 5:
            weather_note += ". Outdoor plants may get natural rain — check soil before watering."
        elif weather_temp_c is not None and weather_temp_c >= 28:
            weather_note += ". Prefer morning so leaves don’t scorch and water doesn’t evaporate instantly."

    explanation = schedule_plain
    if weather_note:
        explanation = f"{schedule_plain} {weather_note}"

    advice = {
        "when": when_plain,
        "how_much": amount_howto,
        "volume_ml": amount_ml,
        "time_of_day": time_key,
        "time_label": time_label,
        "interval_days": round(interval_days, 1),
        "check_soil": "Poke a finger ~2 cm into the soil — if still wet, wait another day.",
    }

    return WateringRecommendation(
        next_due_at=due,
        urgency=urgency,
        recommended_amount=amount,
        confidence=round(confidence, 3),
        moisture_score=round(moisture, 4),
        factor_breakdown=factors,
        explanation=explanation,
        amount_label=amount_label,
        amount_howto=amount_howto.replace("**", ""),
        amount_ml=amount_ml,
        volume_guide=volume_guide.replace("**", ""),
        best_time_of_day=time_key,
        best_time_label=time_label,
        best_time_local=best_time_local,
        schedule_plain=schedule_plain.replace("**", ""),
        weather_note=weather_note,
        interval_days=round(interval_days, 2),
        advice=advice,
    )
