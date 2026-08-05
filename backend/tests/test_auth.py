"""Auth and household integration tests."""

from __future__ import annotations

import pytest

from tests.conftest import auth_header, setup_instance


@pytest.mark.usefixtures("clean_db")
async def test_setup_login_me(client):
    data = await setup_instance(client)
    assert data["user"]["is_instance_admin"] is True
    assert data["household_id"]

    # Setup twice → 410
    again = await client.post(
        "/api/v1/auth/setup",
        json={
            "email": "other@example.com",
            "password": "password123",
            "display_name": "Other",
            "household_name": "Other",
        },
    )
    assert again.status_code == 410

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": data["_email"],
            "password": data["_password"],
            "client": "api",
        },
    )
    assert login.status_code == 200
    tokens = login.json()

    me = await client.get("/api/v1/auth/me", headers=auth_header(tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == data["_email"]


@pytest.mark.usefixtures("clean_db")
async def test_register_after_setup(client):
    await setup_instance(client)
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "member@example.com",
            "password": "password123",
            "display_name": "Member",
        },
    )
    assert reg.status_code == 201
    assert reg.json()["user"]["email"] == "member@example.com"


@pytest.mark.usefixtures("clean_db")
async def test_household_isolation(client):
    admin = await setup_instance(client, email="a@example.com", household_name="A")

    # Second user via register + create own household
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "b@example.com",
            "password": "password123",
            "display_name": "B",
        },
    )
    assert reg.status_code == 201
    b_token = reg.json()["access_token"]

    created = await client.post(
        "/api/v1/households",
        headers=auth_header(b_token),
        json={"name": "B Home"},
    )
    assert created.status_code == 201
    b_household = created.json()["id"]

    # B cannot see A's household
    peek = await client.get(
        f"/api/v1/households/{admin['household_id']}",
        headers=auth_header(b_token),
    )
    assert peek.status_code == 404

    # A cannot see B's household
    peek_a = await client.get(
        f"/api/v1/households/{b_household}",
        headers=auth_header(admin["access_token"]),
    )
    assert peek_a.status_code == 404


@pytest.mark.usefixtures("clean_db")
async def test_invite_accept_and_roles(client):
    admin = await setup_instance(client, email="owner@example.com")

    invite = await client.post(
        f"/api/v1/households/{admin['household_id']}/invitations",
        headers=auth_header(admin["access_token"]),
        json={"email": "sitter@example.com", "role": "member"},
    )
    assert invite.status_code == 201
    token = invite.json()["token"]
    assert token

    # Register invitee
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "sitter@example.com",
            "password": "password123",
            "display_name": "Sitter",
        },
    )
    sitter_token = reg.json()["access_token"]

    accepted = await client.post(
        "/api/v1/invitations/accept",
        headers=auth_header(sitter_token),
        json={"token": token},
    )
    assert accepted.status_code == 200
    assert accepted.json()["role"] == "member"

    # Viewer cannot create invitations — demote first needs admin path
    # Member cannot create invite
    forbidden = await client.post(
        f"/api/v1/households/{admin['household_id']}/invitations",
        headers=auth_header(sitter_token),
        json={"role": "viewer"},
    )
    assert forbidden.status_code == 403

    members = await client.get(
        f"/api/v1/households/{admin['household_id']}/members",
        headers=auth_header(admin["access_token"]),
    )
    assert members.status_code == 200
    assert len(members.json()) == 2


@pytest.mark.usefixtures("clean_db")
async def test_refresh_and_logout(client):
    data = await setup_instance(client)
    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert refresh.status_code == 200
    new_refresh = refresh.json()["refresh_token"]

    # Old refresh revoked
    old = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert old.status_code == 401

    logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_refresh},
    )
    assert logout.status_code == 200

    after = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh},
    )
    assert after.status_code == 401


@pytest.mark.usefixtures("clean_db")
async def test_meta_initialized_flag(client):
    before = await client.get("/api/v1/meta")
    assert before.json()["initialized"] is False
    await setup_instance(client)
    after = await client.get("/api/v1/meta")
    assert after.json()["initialized"] is True


@pytest.mark.usefixtures("clean_db")
async def test_unauthenticated_me(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
