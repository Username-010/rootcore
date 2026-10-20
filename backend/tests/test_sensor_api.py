"""Sensor API tenant, permission and browser-write boundaries."""

import uuid

import pytest

from app.core.config import get_settings
from tests.conftest import auth_header, setup_instance


@pytest.mark.parametrize("role", ["viewer", "member", "admin", "owner"])
@pytest.mark.usefixtures("clean_db")
async def test_database_membership_role_matrix(client, monkeypatch, role):
    from pydantic import SecretStr
    from sqlalchemy import update

    from app.db.session import AsyncSessionLocal
    from app.modules.households.models import Membership
    from app.modules.sensors.adapter import HomeAssistantAdapter

    admin = await setup_instance(client)
    hid = admin["household_id"]
    headers = auth_header(admin["access_token"])
    base = f"/api/v1/households/{hid}"
    plant = await client.post(base + "/plants", headers=headers, json={"nickname": "Role test"})
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Membership).where(Membership.household_id == uuid.UUID(hid)).values(role=role)
        )
        await db.commit()
    settings = get_settings()
    monkeypatch.setattr(settings, "rootcore_ha_household_id", hid)
    monkeypatch.setattr(settings, "rootcore_ha_url", "http://10.10.10.210:8123")
    monkeypatch.setattr(settings, "rootcore_ha_token", SecretStr("test-only-token"))
    calls = []

    async def discover(_):
        calls.append(True)
        return [{"entity_id": "sensor.test_soil", "metric": "humidity"}]

    monkeypatch.setattr(HomeAssistantAdapter, "discover", discover)
    assert (await client.get(base + "/sensors", headers=headers)).status_code == 200
    calls.clear()
    tested = await client.post(base + "/integrations/home_assistant/test", headers=headers)
    assert tested.status_code == (200 if role in {"admin", "owner"} else 403)
    assert len(calls) == (1 if role in {"admin", "owner"} else 0)
    calls.clear()
    body = {"plant_id": plant.json()["id"], "entity_id": "sensor.test_soil"}
    created = await client.post(base + "/sensor-bindings", headers=headers, json=body)
    assert created.status_code == (403 if role == "viewer" else 201)
    assert len(calls) == (0 if role == "viewer" else 1)
    if role != "viewer":
        duplicate = await client.post(base + "/sensor-bindings", headers=headers, json=body)
        assert duplicate.status_code == 409
        assert (
            await client.delete(base + "/sensor-bindings/" + created.json()["id"], headers=headers)
        ).status_code == 204


@pytest.mark.usefixtures("clean_db")
async def test_integrations_require_membership_and_configuration(client, monkeypatch):
    admin = await setup_instance(client)
    hid = admin["household_id"]
    url = f"/api/v1/households/{hid}/integrations"
    client.cookies.clear()
    assert (await client.get(url)).status_code == 401
    headers = auth_header(admin["access_token"])
    result = await client.get(url, headers=headers)
    assert result.status_code == 200, result.text
    assert result.json()[0]["id"] == "home_assistant"
    assert result.json()[0]["configured"] is False
    assert "token" not in result.text
    wrong = await client.get(f"/api/v1/households/{uuid.uuid4()}/integrations", headers=headers)
    assert wrong.status_code == 404


@pytest.mark.usefixtures("clean_db")
async def test_streamed_oversize_body_rejected_before_auth_and_db(client):
    async def body():
        yield b'{"extra":"' + b"x" * 5000 + b'"}'

    response = await client.post(
        f"/api/v1/households/{uuid.uuid4()}/sensor-bindings",
        content=body(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer test-only-invalid"},
    )
    assert response.status_code == 413


@pytest.mark.usefixtures("clean_db")
async def test_other_household_cannot_use_configured_connection(client, monkeypatch):
    admin = await setup_instance(client)
    headers = auth_header(admin["access_token"])
    hid = admin["household_id"]
    monkeypatch.setattr(get_settings(), "rootcore_ha_household_id", str(uuid.uuid4()))
    monkeypatch.setattr(get_settings(), "rootcore_ha_url", "http://10.10.10.210:8123")
    from pydantic import SecretStr

    monkeypatch.setattr(get_settings(), "rootcore_ha_token", SecretStr("test-only-token"))
    base = f"/api/v1/households/{hid}"
    assert (await client.get(base + "/integrations", headers=headers)).json()[0][
        "configured"
    ] is False
    assert (await client.get(base + "/sensors", headers=headers)).status_code == 409
    assert (
        await client.post(base + "/integrations/home_assistant/test", headers=headers)
    ).status_code == 409


@pytest.mark.usefixtures("clean_db")
async def test_viewer_and_cross_household_cannot_mutate_bindings(client, monkeypatch):
    admin = await setup_instance(client)
    hid = admin["household_id"]
    headers = auth_header(admin["access_token"])
    invitation = await client.post(
        f"/api/v1/households/{hid}/invitations",
        headers=headers,
        json={"email": "sensor-viewer@example.com", "role": "viewer"},
    )
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "sensor-viewer@example.com",
            "password": "test-only-password",
            "display_name": "Test viewer",
        },
    )
    viewer = auth_header(reg.json()["access_token"])
    await client.post(
        "/api/v1/invitations/accept", headers=viewer, json={"token": invitation.json()["token"]}
    )
    base = f"/api/v1/households/{hid}"
    assert (await client.get(base + "/sensor-bindings", headers=viewer)).status_code == 200
    body = {"plant_id": str(uuid.uuid4()), "entity_id": "sensor.test"}
    assert (
        await client.post(base + "/sensor-bindings", headers=viewer, json=body)
    ).status_code == 403
    assert (
        await client.delete(base + "/sensor-bindings/" + str(uuid.uuid4()), headers=viewer)
    ).status_code == 403
    assert (
        await client.post(base + "/integrations/home_assistant/test", headers=viewer)
    ).status_code == 403
    other = await client.post(
        "/api/v1/households", headers=viewer, json={"name": "Other test home"}
    )
    other_base = f"/api/v1/households/{other.json()['id']}"
    assert (await client.get(other_base + "/sensors", headers=headers)).status_code == 404
    assert (await client.get(other_base + "/sensor-bindings", headers=headers)).status_code == 404
    assert (
        await client.post(other_base + "/sensor-bindings", headers=headers, json=body)
    ).status_code == 404
    assert (
        await client.delete(other_base + "/sensor-bindings/" + str(uuid.uuid4()), headers=headers)
    ).status_code == 404


@pytest.mark.usefixtures("clean_db")
async def test_foreign_plant_and_binding_ids_stay_unchanged(client, monkeypatch):
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.modules.sensors.adapter import HomeAssistantAdapter
    from app.modules.sensors.models import SensorBinding

    admin = await setup_instance(client)
    headers = auth_header(admin["access_token"])
    own = admin["household_id"]
    second = (
        await client.post(
            "/api/v1/households", headers=headers, json={"name": "Foreign test household"}
        )
    ).json()["id"]
    plant = (
        await client.post(
            f"/api/v1/households/{second}/plants",
            headers=headers,
            json={"nickname": "Foreign plant"},
        )
    ).json()["id"]
    async with AsyncSessionLocal() as db:
        row = SensorBinding(
            household_id=uuid.UUID(second),
            plant_id=uuid.UUID(plant),
            adapter_id="home_assistant",
            entity_id="sensor.test_foreign",
        )
        db.add(row)
        await db.commit()
        binding_id = row.id

    async def fail(_):
        raise AssertionError("Foreign plant must reject before HA access")

    monkeypatch.setattr(HomeAssistantAdapter, "discover", fail)
    url = f"/api/v1/households/{own}/sensor-bindings"
    assert (
        await client.post(
            url, headers=headers, json={"plant_id": plant, "entity_id": "sensor.test_foreign"}
        )
    ).status_code == 404
    assert (await client.delete(url + "/" + str(binding_id), headers=headers)).status_code == 404
    assert (await client.get(url, headers=headers)).json() == []
    async with AsyncSessionLocal() as db:
        assert (
            await db.scalar(select(SensorBinding.id).where(SensorBinding.id == binding_id))
            == binding_id
        )


@pytest.mark.usefixtures("clean_db")
async def test_binding_create_read_delete_and_write_guard(client, monkeypatch):
    admin = await setup_instance(client)
    hid = admin["household_id"]
    headers = auth_header(admin["access_token"])
    plant = await client.post(
        f"/api/v1/households/{hid}/plants", headers=headers, json={"nickname": "Sensor test"}
    )
    pid = plant.json()["id"]
    settings = get_settings()
    monkeypatch.setattr(settings, "rootcore_ha_household_id", hid)
    monkeypatch.setattr(settings, "rootcore_ha_url", "http://10.10.10.210:8123")
    from pydantic import SecretStr

    monkeypatch.setattr(settings, "rootcore_ha_token", SecretStr("test-only-token"))
    from app.modules.sensors.adapter import HomeAssistantAdapter

    async def discover(_):
        return [
            {
                "entity_id": "sensor.test_soil",
                "name": "Test soil",
                "metric": "humidity",
                "unit": "%",
                "value": 42,
                "timestamp": None,
                "status": "unknown_time",
            }
        ]

    monkeypatch.setattr(HomeAssistantAdapter, "discover", discover)
    url = f"/api/v1/households/{hid}/sensor-bindings"
    body = {"plant_id": pid, "entity_id": "sensor.test_soil"}
    rejected = await client.post(
        url,
        headers={**headers, "Origin": "https://evil.invalid", "Sec-Fetch-Site": "cross-site"},
        json=body,
    )
    assert rejected.status_code == 403
    assert (await client.get(url, headers=headers)).json() == []
    created = await client.post(url, headers={**headers, "Origin": "http://test"}, json=body)
    assert created.status_code == 201, created.text
    binding = created.json()
    assert binding["plant_id"] == pid
    assert binding["entity_id"] == "sensor.test_soil"
    assert "test-only-token" not in created.text
    listed = (await client.get(url, headers=headers)).json()
    assert len(listed) == 1
    bad = await client.post(url, headers=headers, json={**body, "plant_id": str(uuid.uuid4())})
    assert bad.status_code == 404
    assert (await client.delete(url + "/" + binding["id"], headers=headers)).status_code == 204
    assert (await client.get(url, headers=headers)).json() == []
