"""Code-owned registry: metadata is not an install-from-URL mechanism."""

from typing import Protocol

from app.modules.sensors.adapter import HomeAssistantAdapter


class SensorAdapter(Protocol):
    async def discover(self) -> list[dict]: ...
    async def history(self, entity_id: str, hours: int) -> list[dict]: ...


ADAPTERS = {"home_assistant": HomeAssistantAdapter}
CATALOG = [
    {
        "id": "home_assistant",
        "name": "Home Assistant",
        "status": "ready",
        "capabilities": ["discovery", "current", "history", "plant_bindings"],
        "connection_mode": "Administrator-managed, one authorized household per instance",
        "bridges": ["Tuya", "LocalTuya", "ESPHome", "Zigbee2MQTT", "ZHA"],
        "description": (
            "Read-only Home Assistant REST integration. Other brands work only when their "
            "sensor entities are exposed in Home Assistant. "
            "No direct Tuya cloud/local adapter or paid fallback."
        ),
    }
]
