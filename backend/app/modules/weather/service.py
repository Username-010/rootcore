"""Weather cache and household weather helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.households.models import Household
from app.modules.weather.client import DailyForecast, WeatherSnapshot
from app.modules.weather.models import WeatherCache

CACHE_MINUTES = 60


def _daily_from_raw(raw: dict) -> list[DailyForecast]:
    from app.modules.weather.client import _parse_daily

    raw = raw or {}
    # Open-Meteo shape
    if raw.get("daily"):
        return _parse_daily(raw.get("daily") or {})
    # Cached MET Norway — no open-meteo daily block; empty is fine
    return []


async def get_household_weather(
    db: AsyncSession,
    household: Household,
    *,
    force: bool = False,
) -> WeatherSnapshot | None:
    if household.latitude is None or household.longitude is None:
        return None

    now = datetime.now(UTC)
    if not force:
        result = await db.execute(
            select(WeatherCache)
            .where(
                WeatherCache.household_id == household.id,
                WeatherCache.site_id.is_(None),
                WeatherCache.expires_at > now,
            )
            .order_by(WeatherCache.fetched_at.desc())
            .limit(1)
        )
        cached = result.scalar_one_or_none()
        if cached:
            return WeatherSnapshot(
                latitude=cached.latitude,
                longitude=cached.longitude,
                current_temp_c=cached.current_temp_c,
                current_humidity=cached.current_humidity,
                precip_next_24h_mm=cached.precip_next_24h_mm,
                raw=cached.payload or {},
                daily=_daily_from_raw(cached.payload or {}),
            )

    settings = household.settings or {}
    provider = str(settings.get("weather_provider") or "open_meteo")

    try:
        from app.modules.weather.client import fetch_weather

        snap = await fetch_weather(
            household.latitude, household.longitude, provider=provider
        )
    except Exception:
        # Degrade gracefully — return last cache if any
        result = await db.execute(
            select(WeatherCache)
            .where(WeatherCache.household_id == household.id)
            .order_by(WeatherCache.fetched_at.desc())
            .limit(1)
        )
        cached = result.scalar_one_or_none()
        if cached:
            return WeatherSnapshot(
                latitude=cached.latitude,
                longitude=cached.longitude,
                current_temp_c=cached.current_temp_c,
                current_humidity=cached.current_humidity,
                precip_next_24h_mm=cached.precip_next_24h_mm,
                raw=cached.payload or {},
                daily=_daily_from_raw(cached.payload or {}),
            )
        return None

    row = WeatherCache(
        household_id=household.id,
        site_id=None,
        latitude=snap.latitude,
        longitude=snap.longitude,
        fetched_at=now,
        expires_at=now + timedelta(minutes=CACHE_MINUTES),
        provider=provider,
        payload=snap.raw,
        current_temp_c=snap.current_temp_c,
        current_humidity=snap.current_humidity,
        precip_next_24h_mm=snap.precip_next_24h_mm,
    )
    db.add(row)
    await db.flush()
    return snap


def weather_public(snap: WeatherSnapshot | None) -> dict | None:
    if snap is None:
        return None
    return {
        "provider": "open_meteo",
        "latitude": snap.latitude,
        "longitude": snap.longitude,
        "temperature_c": snap.current_temp_c,
        "humidity": snap.current_humidity,
        "precip_next_24h_mm": snap.precip_next_24h_mm,
        "daily": [
            {
                "date": d.date,
                "temp_max_c": d.temp_max_c,
                "temp_min_c": d.temp_min_c,
                "precip_mm": d.precip_mm,
                "weather_code": d.weather_code,
                "precip_probability_max": d.precip_probability_max,
            }
            for d in (snap.daily or [])
        ],
    }
