"""Security regression tests; no live database or Home Assistant access."""

import uuid

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from app.api import deps
from app.api.routes import sensors
from app.modules.sensors.adapter import (
    HomeAssistantAdapter,
    SensorError,
    normalize_state,
    validate_destination,
)


@pytest.mark.parametrize(
    "host",
    [
        "100.100.100.200",
        "[::ffff:100.100.100.200]",
        "168.63.129.16",
        "[::ffff:168.63.129.16]",
        "[fd00:ec2::254]",
        "[fd20:ce::254]",
        "169.254.169.254",
        "[::ffff:169.254.169.254]",
    ],
)
def test_metadata_destination_is_blocked(host):
    with pytest.raises(SensorError):
        validate_destination(f"http://{host}")


def test_actual_private_ha_destination_remains_allowed():
    assert (
        validate_destination("http://10.10.10.210:8123/") == "http://10.10.10.210:8123"
    )


@pytest.mark.parametrize("field", ["url", "token", "config", "base_url"])
def test_binding_rejects_client_configuration(field):
    with pytest.raises(ValidationError):
        sensors.BindingCreate(
            plant_id=uuid.uuid4(), entity_id="sensor.test", **{field: "secret-marker"}
        )


@pytest.mark.parametrize(
    "attributes",
    [
        None,
        [],
        "secret-marker",
        {"device_class": []},
        {"device_class": {}},
        {"friendly_name": 4},
        {"unit_of_measurement": []},
    ],
)
def test_malformed_attributes_raise_only_sanitized_error(attributes, caplog):
    with pytest.raises(SensorError) as error:
        normalize_state(
            {"entity_id": "sensor.test", "state": "1", "attributes": attributes}
        )
    assert str(error.value) == "Home Assistant returned invalid sensor attributes"
    assert "secret-marker" not in caplog.text


@pytest.mark.parametrize(
    "field,value",
    [
        ("entity_id", []),
        ("entity_id", {"secret-marker": 1}),
        ("state", True),
        ("state", 10**400),
    ],
)
def test_malformed_exposed_values_raise_sanitized_error(field, value):
    state = {"entity_id": "sensor.test", "state": "1", "attributes": {}}
    state[field] = value
    with pytest.raises(SensorError):
        normalize_state(state)


@pytest.fixture
def guarded_app(monkeypatch):
    app = FastAPI()
    app.include_router(sensors.router)

    async def forbidden_db():
        raise AssertionError("Database dependency must not be reached")
        yield

    async def forbidden_ha(*args, **kwargs):
        raise AssertionError("HA must not be reached")

    app.dependency_overrides[deps.get_db] = forbidden_db
    monkeypatch.setattr(HomeAssistantAdapter, "discover", forbidden_ha)
    from app.core.sensor_body_limit import SensorBodyLimitMiddleware

    app.add_middleware(SensorBodyLimitMiddleware)
    return app


@pytest.mark.parametrize(
    "suffix",
    [
        "/sensor-bindings",
        "/integrations/home_assistant/test",
        "/sensor-bindings/" + str(uuid.uuid4()),
    ],
)
@pytest.mark.parametrize("declared", [None, "2", "9000"])
async def test_streamed_limit_before_parser_or_dependencies(
    guarded_app, suffix, declared
):
    chunks = [b"{", b"x" * 2048, b"x" * 2048, b"never-consumed"]
    consumed = []

    async def stream():
        for chunk in chunks:
            consumed.append(chunk)
            yield chunk

    headers = {"content-type": "application/json", "authorization": "Bearer test-only"}
    if declared is not None:
        headers["content-length"] = declared
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=guarded_app), base_url="http://test"
    ) as client:
        response = await client.request(
            "DELETE" if "/sensor-bindings/" in suffix else "POST",
            "/api/v1/households/" + str(uuid.uuid4()) + suffix,
            content=stream(),
            headers=headers,
        )
    assert response.status_code == 413
    assert b"never-consumed" not in consumed


@pytest.mark.parametrize(
    "headers",
    [{}, {"origin": "https://evil.invalid"}, {"sec-fetch-site": "cross-site"}],
)
async def test_rejection_does_not_reach_db_or_ha(guarded_app, headers):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=guarded_app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/households/" + str(uuid.uuid4()) + "/sensor-bindings",
            json={"plant_id": str(uuid.uuid4()), "entity_id": "sensor.test"},
            headers=headers,
        )
    assert response.status_code == (403 if headers else 401)


@pytest.mark.parametrize("size,status", [(4096, 200), (4097, 413)])
async def test_middleware_bounds_before_any_downstream_application(size, status):
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    from app.core.sensor_body_limit import SensorBodyLimitMiddleware

    reached = []

    async def downstream(scope, receive, send):
        body = await Request(scope, receive).body()
        reached.append(body)
        await JSONResponse({"bytes": len(body)})(scope, receive, send)

    async def stream():
        yield b"x" * 2048
        yield b"x" * (size - 2048)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=SensorBodyLimitMiddleware(downstream)),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/households/test/sensor-bindings",
            content=stream(),
            headers={"authorization": "Bearer test-only"},
        )
    assert response.status_code == status
    assert len(reached) == (1 if status == 200 else 0)
    if status == 200:
        assert response.json() == {"bytes": 4096}


@pytest.mark.parametrize("length", ["-1", "invalid"])
async def test_invalid_content_length_before_dependencies(guarded_app, length):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=guarded_app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/households/test/sensor-bindings",
            content=b"{}",
            headers={"content-length": length},
        )
    assert response.status_code == 400


async def test_production_app_has_sensor_middleware():
    from app.core.sensor_body_limit import SensorBodyLimitMiddleware
    from app.main import create_app

    app = create_app()  # Do not enter lifespan: no DB seeding or startup I/O.
    assert any(item.cls is SensorBodyLimitMiddleware for item in app.user_middleware)


@pytest.mark.parametrize("operation", ["discover", "history"])
@pytest.mark.parametrize(
    "attributes", [None, [], "secret-marker", {"device_class": ["secret-marker"]}]
)
async def test_malformed_mock_upstream_sanitized_in_adapter(
    operation, attributes, caplog
):
    state = {"entity_id": "sensor.test", "state": "1", "attributes": attributes}
    payload = [state] if operation == "discover" else [[state]]
    adapter = HomeAssistantAdapter(
        "http://10.10.10.210:8123",
        "secret-marker",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload)),
    )
    with pytest.raises(SensorError) as error:
        if operation == "discover":
            await adapter.discover()
        else:
            await adapter.history("sensor.test", 24)
    assert str(error.value) == "Home Assistant returned invalid sensor attributes"
    assert "secret-marker" not in caplog.text


async def test_malformed_upstream_route_is_502_not_500(monkeypatch):
    from types import SimpleNamespace

    app = FastAPI()
    app.include_router(sensors.router)
    hid = uuid.uuid4()

    async def no_io_db():
        yield object()

    async def user():
        return SimpleNamespace(id=uuid.uuid4())

    async def membership(*args, **kwargs):
        return SimpleNamespace(role="owner", household=SimpleNamespace(id=hid))

    app.dependency_overrides[deps.get_db] = no_io_db
    app.dependency_overrides[deps.get_current_user] = user
    monkeypatch.setattr(deps, "get_membership", membership)
    adapter = HomeAssistantAdapter(
        "http://10.10.10.210:8123",
        "secret-marker",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json=[
                    {
                        "entity_id": "sensor.test",
                        "state": "1",
                        "attributes": "secret-marker",
                    }
                ],
            )
        ),
    )
    monkeypatch.setattr(sensors, "adapter_for", lambda _: adapter)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/v1/households/{hid}/sensors")
    assert response.status_code == 502
    assert response.json() == {
        "detail": "Home Assistant returned invalid sensor attributes"
    }
    assert "secret-marker" not in response.text
