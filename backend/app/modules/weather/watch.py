"""Garden watch: frost nights and rain-skip advice from a 7-day forecast."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.modules.weather.client import WeatherSnapshot

INDOOR_KINDS = {
    "room",
    "indoor",
    "windowsill",
    "conservatory",
    "kitchen",
    "living",
    "bathroom",
    "bedroom",
    "office",
    "hallway",
    "cellar",
}

FROST_HARD_C = 0.0
FROST_RISK_C = 4.0
RAIN_SKIP_MM = 5.0
HEAT_C = 28.0


def is_outdoor_kind(kind: str | None) -> bool:
    k = (kind or "room").strip().lower()
    return k not in INDOOR_KINDS


def build_garden_watch(
    *,
    timezone: str,
    now: datetime,
    snap: WeatherSnapshot | None,
    outdoor_plants: list[dict[str, Any]],
    configured: bool,
) -> dict[str, Any]:
    nights: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    daily = list(snap.daily) if snap and snap.daily else []

    for i, d in enumerate(daily[:7]):
        tmin = d.temp_min_c
        tmax = d.temp_max_c
        precip = d.precip_mm
        frost_hard = tmin is not None and tmin <= FROST_HARD_C
        frost_risk = tmin is not None and tmin <= FROST_RISK_C
        rain_skip = precip is not None and precip >= RAIN_SKIP_MM
        heat = tmax is not None and tmax >= HEAT_C
        flags: list[str] = []
        if frost_hard:
            flags.append("hard_frost")
        elif frost_risk:
            flags.append("frost_risk")
        if rain_skip:
            flags.append("rain_skip")
        if heat:
            flags.append("heat")

        weekday = ""
        try:
            weekday = datetime.fromisoformat(d.date).strftime("%A")
        except ValueError:
            weekday = d.date

        nights.append(
            {
                "date": d.date,
                "weekday": weekday,
                "is_today": i == 0,
                "temp_min_c": tmin,
                "temp_max_c": tmax,
                "precip_mm": precip,
                "weather_code": d.weather_code,
                "frost_hard": frost_hard,
                "frost_risk": frost_risk,
                "rain_skip": rain_skip,
                "heat": heat,
                "flags": flags,
            }
        )

        when = " tonight" if i == 0 else f" {weekday}"
        if frost_hard and tmin is not None:
            alerts.append(
                {
                    "kind": "frost",
                    "severity": "danger",
                    "date": d.date,
                    "title": f"Hard frost{when}",
                    "detail": (
                        f"Low {round(tmin)}°C. Bring tender outdoor pots inside or cover them."
                    ),
                }
            )
        elif frost_risk and tmin is not None:
            alerts.append(
                {
                    "kind": "frost",
                    "severity": "warning",
                    "date": d.date,
                    "title": f"Frost risk{when}",
                    "detail": (
                        f"Low {round(tmin)}°C. Tender plants on the balcony or in the garden "
                        "may need a cover."
                    ),
                }
            )
        if rain_skip and precip is not None:
            rain_when = " today" if i == 0 else f" {weekday}"
            alerts.append(
                {
                    "kind": "rain",
                    "severity": "info",
                    "date": d.date,
                    "title": f"Skip outdoor watering{rain_when}",
                    "detail": f"About {precip:.1f} mm rain — outdoor beds can wait.",
                }
            )
        if heat and i == 0 and tmax is not None:
            alerts.append(
                {
                    "kind": "heat",
                    "severity": "warning",
                    "date": d.date,
                    "title": "Hot day",
                    "detail": (
                        f"High {round(tmax)}°C — water outdoor pots in the morning, not midday."
                    ),
                }
            )

    frost_nights = sum(1 for n in nights if n["frost_risk"] or n["frost_hard"])
    rain_days = sum(1 for n in nights if n["rain_skip"])
    n_out = len(outdoor_plants)
    plant_bit = f"{n_out} outdoor plant" + ("" if n_out == 1 else "s")

    if not configured:
        summary = "Set a location in Settings to get frost and rain watch."
    elif not nights:
        summary = "Forecast not available yet. Refresh weather from Settings."
    elif frost_nights:
        summary = (
            f"{frost_nights} frost night"
            + ("" if frost_nights == 1 else "s")
            + f" this week. Protect {plant_bit}."
        )
    elif rain_days:
        summary = (
            f"{rain_days} wet day"
            + ("" if rain_days == 1 else "s")
            + " — outdoor watering can wait those days."
        )
    else:
        summary = "No frost this week. Outdoor plants can stay out."

    return {
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "configured": configured,
        "summary": summary,
        "alerts": alerts,
        "nights": nights,
        "outdoor_plants": outdoor_plants,
        "counts": {
            "frost_nights": frost_nights,
            "rain_days": rain_days,
            "outdoor_plants": n_out,
            "alerts": len(alerts),
        },
    }
