"""Health and meta endpoint tests."""


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_meta(client):
    response = await client.get("/api/v1/meta")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "RootCore"
    assert data["version"] == "0.1.0"
    assert data["registration_mode"] in {"open", "invite", "closed"}
    assert "initialized" in data
    assert "features" in data
    assert data["docs_url"] == "/api/docs"
