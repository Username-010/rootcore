"""Read-only sensor adapters. Never infer a reading from unavailable state."""

import math
from datetime import UTC, datetime


class SensorError(Exception):
    pass


class HomeAssistantAdapter:
    """REST adapter: only GET, no services or device writes."""

    def __init__(self, url, token, *, transport=None):
        self.url = validate_destination(url)
        self._token = token
        self._transport = transport

    async def _get(self, path, *, params=None):
        import asyncio
        import json

        import httpx

        try:
            async with asyncio.timeout(12):
                async with (
                    httpx.AsyncClient(
                        transport=self._transport,
                        timeout=8,
                        follow_redirects=False,
                        trust_env=False,
                    ) as client,
                    client.stream(
                        "GET",
                        self.url + path,
                        params=params,
                        headers={"Authorization": "Bearer " + self._token},
                    ) as response,
                ):
                    if response.status_code != 200:
                        raise SensorError(
                            "Home Assistant rejected the request; check connection and permissions"
                        )
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > 4_000_000:
                            raise SensorError(
                                "Home Assistant response exceeds the safety limit"
                            )
                    return json.loads(data)
        except (httpx.HTTPError, TimeoutError, ValueError):
            raise SensorError(
                "Home Assistant is offline or returned invalid data"
            ) from None

    async def history(self, entity_id, hours):
        import re
        from datetime import timedelta

        if not re.fullmatch(r"sensor\.[a-z0-9_]{1,200}", entity_id) or hours not in {
            24,
            168,
        }:
            raise SensorError("Invalid entity or history window")
        end = datetime.now(UTC)
        start = end - timedelta(hours=hours)
        groups = await self._get(
            "/api/history/period/" + start.isoformat(),
            params={
                "filter_entity_id": entity_id,
                "end_time": end.isoformat(),
            },
        )
        if not isinstance(groups, list) or any(not isinstance(g, list) for g in groups):
            raise SensorError("Home Assistant returned invalid history")
        states = [
            s
            for g in groups
            for s in g
            if isinstance(s, dict) and s.get("entity_id") == entity_id
        ]
        if len(states) > 10000:
            raise SensorError("Too many history records; select 24 hours")
        return [normalize_state(s) for s in states]

    async def discover(self):
        states = await self._get("/api/states")
        if not isinstance(states, list):
            raise SensorError("Home Assistant returned invalid states")
        readings = []
        for state in states:
            if not isinstance(state, dict) or not str(
                state.get("entity_id", "")
            ).startswith("sensor."):
                continue
            reading = normalize_state(state)
            if reading["metric"] != "other":
                readings.append(reading)
        if len(readings) > 500:
            raise SensorError(
                "More than 500 supported sensors; narrow the HA integration"
            )
        return readings


def normalize_state(state, *, now=None):
    if (
        not isinstance(state, dict)
        or not isinstance(state.get("entity_id"), str)
        or isinstance(state.get("state"), bool)
    ):
        raise SensorError("Home Assistant returned invalid sensor state")
    attrs = state.get("attributes", {})
    if not isinstance(attrs, dict) or any(
        attrs.get(key) is not None and not isinstance(attrs[key], str)
        for key in ("friendly_name", "unit_of_measurement", "device_class")
    ):
        raise SensorError("Home Assistant returned invalid sensor attributes")
    metric = {
        "moisture": "soil_moisture",
        "illuminance": "illuminance",
        "temperature": "temperature",
        "humidity": "humidity",
        "battery": "battery",
    }.get(attrs.get("device_class"), "other")
    try:
        value = float(state.get("state", ""))
        if not math.isfinite(value):
            value = None
    except OverflowError:
        raise SensorError("Home Assistant returned invalid sensor state") from None
    except (ValueError, TypeError):
        value = None
    timestamp = state.get("last_updated") or state.get("last_changed")
    status = "unavailable" if value is None else "current"
    try:
        source = datetime.fromisoformat(timestamp)
        if source.tzinfo is None:
            raise ValueError("missing timezone")
        if (
            value is not None
            and ((now or datetime.now(UTC)) - source).total_seconds() > 86400
        ):
            status = "stale"
    except (ValueError, TypeError):
        timestamp = None
        if value is not None:
            status = "unknown_time"
    return {
        "entity_id": state.get("entity_id"),
        "name": attrs.get("friendly_name") or state.get("entity_id"),
        "value": value,
        "unit": attrs.get("unit_of_measurement"),
        "timestamp": timestamp,
        "status": status,
        "metric": metric,
    }


def validate_destination(url):
    from ipaddress import ip_address, ip_network
    from urllib.parse import urlsplit

    try:
        parsed = urlsplit(url)
        address = ip_address(parsed.hostname or "")
        # Apply IPv4 policy equally to IPv4-mapped IPv6 destinations.
        address = getattr(address, "ipv4_mapped", None) or address
        metadata_ranges = (
            ip_network("100.64.0.0/10"),  # Includes Alibaba's 100.100.100.200 metadata.
            ip_network("168.63.129.16/32"),  # Azure platform virtual IP.
            ip_network("fd00:ec2::254/128"),  # AWS IMDS IPv6.
            ip_network("fd20:ce::254/128"),  # Google metadata IPv6.
        )
        if (
            any(address in network for network in metadata_ranges)
            or parsed.scheme not in {"http", "https"}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
            or address.is_loopback
            or address.is_link_local
            or address.is_unspecified
            or address.is_multicast
            or address.is_reserved
            or parsed.port not in {None, 80, 443, 8123}
        ):
            raise ValueError("invalid destination")
    except ValueError:
        raise SensorError(
            "Use an explicit Home Assistant IP on HTTP(S), port 80, 443 or 8123; "
            "no path or credentials"
        ) from None
    return url.rstrip("/")
