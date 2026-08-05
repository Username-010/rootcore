"""Plant and taxonomy integration tests."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.db.session import AsyncSessionLocal
from app.modules.taxonomy.service import seed_global_taxa
from tests.conftest import auth_header, setup_instance


async def _seed():
    async with AsyncSessionLocal() as session:
        await seed_global_taxa(session, force=False)
        await session.commit()


def _png_bytes(color: tuple[int, int, int] = (34, 139, 34)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.usefixtures("clean_db")
async def test_create_list_plant_with_taxon(client):
    await _seed()
    admin = await setup_instance(client)
    headers = auth_header(admin["access_token"])
    hid = admin["household_id"]

    taxa = await client.get("/api/v1/taxa", params={"q": "Monstera"}, headers=headers)
    assert taxa.status_code == 200
    assert len(taxa.json()) >= 1
    taxon_id = taxa.json()[0]["id"]

    created = await client.post(
        f"/api/v1/households/{hid}/plants",
        headers=headers,
        json={
            "nickname": "Hallway Monstera",
            "taxon_id": taxon_id,
            "environment": "indoor",
            "pot_size_liters": 5,
            "tag_names": ["trailing", "favorite"],
        },
    )
    assert created.status_code == 201, created.text
    plant = created.json()
    assert plant["nickname"] == "Hallway Monstera"
    assert plant["taxon"]["scientific_name"] == "Monstera deliciosa"
    assert {t["name"] for t in plant["tags"]} == {"trailing", "favorite"}

    listed = await client.get(
        f"/api/v1/households/{hid}/plants",
        headers=headers,
        params={"q": "Hallway"},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


@pytest.mark.usefixtures("clean_db")
async def test_plant_isolation(client):
    await _seed()
    a = await setup_instance(client, email="a@example.com", household_name="A")
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "b@example.com", "password": "password123", "display_name": "B"},
    )
    b_token = reg.json()["access_token"]
    b_hh = await client.post(
        "/api/v1/households",
        headers=auth_header(b_token),
        json={"name": "B Home"},
    )
    b_hid = b_hh.json()["id"]

    plant = await client.post(
        f"/api/v1/households/{a['household_id']}/plants",
        headers=auth_header(a["access_token"]),
        json={"nickname": "Secret Fern"},
    )
    pid = plant.json()["id"]

    peek = await client.get(
        f"/api/v1/households/{a['household_id']}/plants/{pid}",
        headers=auth_header(b_token),
    )
    assert peek.status_code == 404

    wrong = await client.get(
        f"/api/v1/households/{b_hid}/plants/{pid}",
        headers=auth_header(b_token),
    )
    assert wrong.status_code == 404


@pytest.mark.usefixtures("clean_db")
async def test_photo_upload_and_media(client):
    admin = await setup_instance(client)
    headers = auth_header(admin["access_token"])
    hid = admin["household_id"]

    plant = await client.post(
        f"/api/v1/households/{hid}/plants",
        headers=headers,
        json={"nickname": "Photo Plant"},
    )
    pid = plant.json()["id"]

    files = {"file": ("leaf.png", _png_bytes(), "image/png")}
    data = {"caption": "Day 1", "set_cover": "true"}
    upload = await client.post(
        f"/api/v1/households/{hid}/plants/{pid}/photos",
        headers=headers,
        files=files,
        data=data,
    )
    assert upload.status_code == 201, upload.text
    photo = upload.json()
    assert photo["caption"] == "Day 1"
    assert photo["is_cover"] is True
    assert photo["thumb_url"]

    media = await client.get(photo["thumb_url"])
    assert media.status_code == 200
    assert media.headers["content-type"].startswith("image/")

    detail = await client.get(
        f"/api/v1/households/{hid}/plants/{pid}",
        headers=headers,
    )
    assert detail.json()["cover_photo"]["id"] == photo["id"]


@pytest.mark.usefixtures("clean_db")
async def test_archive_and_viewer_cannot_create(client):
    admin = await setup_instance(client, email="owner@example.com")
    hid = admin["household_id"]

    invite = await client.post(
        f"/api/v1/households/{hid}/invitations",
        headers=auth_header(admin["access_token"]),
        json={"email": "view@example.com", "role": "viewer"},
    )
    token = invite.json()["token"]
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "view@example.com",
            "password": "password123",
            "display_name": "Viewer",
        },
    )
    v_headers = auth_header(reg.json()["access_token"])
    await client.post(
        "/api/v1/invitations/accept",
        headers=v_headers,
        json={"token": token},
    )

    forbidden = await client.post(
        f"/api/v1/households/{hid}/plants",
        headers=v_headers,
        json={"nickname": "Nope"},
    )
    assert forbidden.status_code == 403

    plant = await client.post(
        f"/api/v1/households/{hid}/plants",
        headers=auth_header(admin["access_token"]),
        json={"nickname": "Keep"},
    )
    pid = plant.json()["id"]
    archived = await client.post(
        f"/api/v1/households/{hid}/plants/{pid}/archive",
        headers=auth_header(admin["access_token"]),
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    listed = await client.get(
        f"/api/v1/households/{hid}/plants",
        headers=auth_header(admin["access_token"]),
    )
    assert listed.json()["total"] == 0
