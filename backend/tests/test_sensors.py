"""Home Assistant adapter contracts; all upstream data here is test-only."""

from datetime import UTC, datetime

import httpx
import pytest

from app.modules.sensors.adapter import (
    HomeAssistantAdapter,
    SensorError,
    normalize_state,
    validate_destination,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8123",
        "http://169.254.169.254",
        "http://localhost:8123",
        "file:///etc/passwd",
        "http://user:pass@10.10.10.210:8123",
        "http://10.10.10.210:8123/?url=x",
        "http://[::1]:8123",
        "http://0.0.0.0",
        "http://10.10.10.210:22",
        "http://10.10.10.210:8123/api",
    ],
)
def test_rejects_unsafe_destinations(url):
    with pytest.raises(SensorError):
        validate_destination(url)


def test_accepts_explicit_lan_home_assistant():
    assert validate_destination("http://10.10.10.210:8123/") == "http://10.10.10.210:8123"


async def test_discovery_reads_only_supported_sensor_states():
    def upstream(request):
        assert request.headers["Authorization"] == "Bearer test-only-token"
        assert request.url.path == "/api/states"
        return httpx.Response(
            200,
            json=[
                {
                    "entity_id": "sensor.test_soil",
                    "state": "42",
                    "last_updated": "2026-10-20T08:00:00+00:00",
                    "attributes": {"device_class": "moisture", "unit_of_measurement": "%"},
                },
                {"entity_id": "light.test", "state": "on", "attributes": {}},
                {
                    "entity_id": "sensor.test_cost",
                    "state": "5",
                    "attributes": {"device_class": "monetary"},
                },
            ],
        )

    adapter = HomeAssistantAdapter(
        "http://10.10.10.210:8123", "test-only-token", transport=httpx.MockTransport(upstream)
    )
    result = await adapter.discover()
    assert [r["entity_id"] for r in result] == ["sensor.test_soil"]
    assert result[0]["value"] == 42


@pytest.mark.parametrize(
    "bad", [None, [], "bad", {"unit_of_measurement": {"bad": 1}}, {"friendly_name": []}]
)
def test_malformed_attributes_are_rejected_cleanly(bad):
    with pytest.raises(SensorError):
        normalize_state({"entity_id": "sensor.test", "state": "1", "attributes": bad})


async def test_history_retains_gaps_and_source_timestamps():
    def upstream(request):
        assert request.url.path.startswith("/api/history/period/")
        assert request.url.params["filter_entity_id"] == "sensor.test_soil"
        assert request.url.params["end_time"]
        return httpx.Response(
            200,
            json=[
                [
                    {
                        "entity_id": "sensor.test_soil",
                        "state": "21",
                        "last_updated": "2026-10-20T08:00:00+00:00",
                        "attributes": {"unit_of_measurement": "%"},
                    },
                    {
                        "entity_id": "sensor.test_soil",
                        "state": "unknown",
                        "last_updated": "2026-10-20T09:00:00+00:00",
                        "attributes": {"unit_of_measurement": "%"},
                    },
                ]
            ],
        )

    adapter = HomeAssistantAdapter(
        "http://10.10.10.210:8123", "test-only-token", transport=httpx.MockTransport(upstream)
    )
    result = await adapter.history("sensor.test_soil", 24)
    assert [r["value"] for r in result] == [21, None]
    assert result[0]["timestamp"] == "2026-10-20T08:00:00+00:00"
    with pytest.raises(SensorError):
        await adapter.history("sensor.test_soil/../../config", 24)
    with pytest.raises(SensorError):
        await adapter.history("sensor.test_soil", 10000)


@pytest.mark.parametrize("code", [302, 401, 500])
async def test_upstream_errors_are_sanitized(code):
    adapter = HomeAssistantAdapter(
        "http://10.10.10.210:8123",
        "test-only-token",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                code, text="sensitive upstream text", headers={"Location": "http://127.0.0.1"}
            )
        ),
    )
    with pytest.raises(SensorError) as exc:
        await adapter.discover()
    assert "sensitive" not in str(exc.value)
    assert "test-only-token" not in str(exc.value)


def test_stale_numeric_state_and_invalid_number():
    state = {
        "entity_id": "sensor.test",
        "state": "0",
        "last_updated": "2026-10-18T08:00:00+00:00",
        "attributes": {},
    }
    assert normalize_state(state)["status"] == "stale"
    assert normalize_state(state)["value"] == 0
    state["state"] = "NaN"
    assert normalize_state(state)["value"] is None


def test_unavailable_is_not_zero_and_preserves_source_time():
    state = {
        "entity_id": "sensor.test_soil",
        "state": "unavailable",
        "last_updated": "2026-10-20T08:00:00+00:00",
        "attributes": {"unit_of_measurement": "%", "device_class": "moisture"},
    }
    result = normalize_state(state, now=datetime(2026, 10, 20, 9, tzinfo=UTC))
    assert result["value"] is None
    assert result["status"] == "unavailable"
    assert result["timestamp"] == state["last_updated"]
    assert result["unit"] == "%"
    assert result["metric"] == "soil_moisture"
