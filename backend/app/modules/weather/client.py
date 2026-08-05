"""Open-Meteo forecast client (no API key)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass
class DailyForecast:
    date: str  # YYYY-MM-DD
    temp_max_c: float | None
    temp_min_c: float | None
    precip_mm: float | None
    weather_code: int | None
    precip_probability_max: float | None = None


@dataclass
class WeatherSnapshot:
    latitude: float
    longitude: float
    current_temp_c: float | None
    current_humidity: float | None
    precip_next_24h_mm: float | None
    raw: dict[str, Any]
    daily: list[DailyForecast] = field(default_factory=list)

    @property
    def outdoor_demand_multiplier(self) -> float:
        """Higher → plants dry faster (shorten interval)."""
        mult = 1.0
        if self.current_temp_c is not None:
            if self.current_temp_c >= 30:
                mult *= 0.8
            elif self.current_temp_c >= 25:
                mult *= 0.9
            elif self.current_temp_c <= 5:
                mult *= 1.2
        if self.current_humidity is not None:
            if self.current_humidity < 30:
                mult *= 0.9
            elif self.current_humidity > 75:
                mult *= 1.1
        if self.precip_next_24h_mm is not None and self.precip_next_24h_mm >= 5:
            mult *= 1.25  # rain expected → lengthen for outdoor
        return mult


async def fetch_open_meteo(latitude: float, longitude: float) -> WeatherSnapshot:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation",
        "hourly": "precipitation",
        "daily": (
            "temperature_2m_max,temperature_2m_min,precipitation_sum,"
            "precipitation_probability_max,weather_code"
        ),
        "forecast_days": 7,
        "timezone": "auto",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        data = response.json()

    current = data.get("current") or {}
    hourly = data.get("hourly") or {}
    precip_list = hourly.get("precipitation") or []
    precip_24 = sum(float(x or 0) for x in precip_list[:24]) if precip_list else None

    daily = _parse_daily(data.get("daily") or {})

    return WeatherSnapshot(
        latitude=latitude,
        longitude=longitude,
        current_temp_c=_num(current.get("temperature_2m")),
        current_humidity=_num(current.get("relative_humidity_2m")),
        precip_next_24h_mm=precip_24,
        raw={**data, "_provider": "open_meteo"},
        daily=daily,
    )


async def fetch_met_norway(latitude: float, longitude: float) -> WeatherSnapshot:
    """Norwegian Meteorological Institute locationforecast (free, no key).

    Requires a descriptive User-Agent per their terms of service.
    """
    url = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
    headers = {
        "User-Agent": "RootCore/1.0 self-hosted plant care (https://github.com/rootcore)",
        "Accept": "application/json",
    }
    params = {"lat": latitude, "lon": longitude}
    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    timeseries = (data.get("properties") or {}).get("timeseries") or []
    temp = humidity = None
    precip_24 = 0.0
    if timeseries:
        instant = (timeseries[0].get("data") or {}).get("instant") or {}
        details = instant.get("details") or {}
        temp = _num(details.get("air_temperature"))
        humidity = _num(details.get("relative_humidity"))
        # Sum next ~24 hours of 1h precipitation if present
        for entry in timeseries[:25]:
            next1 = (entry.get("data") or {}).get("next_1_hours") or {}
            det = next1.get("details") or {}
            p = _num(det.get("precipitation_amount"))
            if p is not None:
                precip_24 += p

    # Build coarse daily from series (max/min per local date stamp)
    by_day: dict[str, dict[str, float | None]] = {}
    for entry in timeseries:
        t = str(entry.get("time") or "")[:10]
        if not t:
            continue
        instant = (entry.get("data") or {}).get("instant") or {}
        details = instant.get("details") or {}
        at = _num(details.get("air_temperature"))
        bucket = by_day.setdefault(t, {"max": None, "min": None, "precip": 0.0})
        if at is not None:
            bucket["max"] = at if bucket["max"] is None else max(float(bucket["max"]), at)
            bucket["min"] = at if bucket["min"] is None else min(float(bucket["min"]), at)
        next6 = (entry.get("data") or {}).get("next_6_hours") or {}
        p6 = _num((next6.get("details") or {}).get("precipitation_amount"))
        if p6 is not None:
            bucket["precip"] = float(bucket["precip"] or 0) + p6

    daily: list[DailyForecast] = []
    for day, vals in list(by_day.items())[:7]:
        daily.append(
            DailyForecast(
                date=day,
                temp_max_c=vals.get("max"),  # type: ignore[arg-type]
                temp_min_c=vals.get("min"),  # type: ignore[arg-type]
                precip_mm=vals.get("precip"),  # type: ignore[arg-type]
                weather_code=None,
                precip_probability_max=None,
            )
        )

    return WeatherSnapshot(
        latitude=latitude,
        longitude=longitude,
        current_temp_c=temp,
        current_humidity=humidity,
        precip_next_24h_mm=precip_24 if timeseries else None,
        raw={**data, "_provider": "met_norway"},
        daily=daily,
    )


async def fetch_weather(
    latitude: float,
    longitude: float,
    *,
    provider: str = "open_meteo",
) -> WeatherSnapshot:
    """Dispatch to configured free weather provider."""
    p = (provider or "open_meteo").lower().strip()
    if p in {"met_norway", "met.no", "yr", "metno"}:
        return await fetch_met_norway(latitude, longitude)
    return await fetch_open_meteo(latitude, longitude)


def _parse_daily(daily: dict[str, Any]) -> list[DailyForecast]:
    times = daily.get("time") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    precip = daily.get("precipitation_sum") or []
    codes = daily.get("weather_code") or []
    probs = daily.get("precipitation_probability_max") or []
    out: list[DailyForecast] = []
    for i, day in enumerate(times):
        out.append(
            DailyForecast(
                date=str(day),
                temp_max_c=_num(tmax[i]) if i < len(tmax) else None,
                temp_min_c=_num(tmin[i]) if i < len(tmin) else None,
                precip_mm=_num(precip[i]) if i < len(precip) else None,
                weather_code=int(codes[i]) if i < len(codes) and codes[i] is not None else None,
                precip_probability_max=_num(probs[i]) if i < len(probs) else None,
            )
        )
    return out


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
