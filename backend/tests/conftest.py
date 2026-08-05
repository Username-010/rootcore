"""Pytest fixtures."""

from __future__ import annotations

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure test-friendly settings before app import side effects
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_DEBUG", "false")
os.environ.setdefault(
    "SECRET_KEY",
    "test-secret-key-at-least-32-characters-long",
)
# ALWAYS use a dedicated test database — never wipe the real app DB
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://plantpilot:plantpilot@localhost:5432/plantpilot_test",
)
os.environ.setdefault("REGISTRATION_MODE", "open")

# Clear cached settings so they pick up TEST DATABASE_URL
from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.db.session import engine  # noqa: E402
from app.main import create_app  # noqa: E402


def pytest_configure():
    """Create plantpilot_test DB if missing (best-effort)."""
    url = os.environ["DATABASE_URL"]
    if "plantpilot_test" not in url:
        return
    admin_url = url.rsplit("/", 1)[0] + "/postgres"
    # connect to maintenance db and CREATE DATABASE
    import asyncio

    async def _ensure():
        eng = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
        try:
            async with eng.connect() as conn:
                exists = await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = 'plantpilot_test'")
                )
                if exists.scalar() is None:
                    await conn.execute(text("CREATE DATABASE plantpilot_test"))
        finally:
            await eng.dispose()

    try:
        asyncio.get_event_loop().run_until_complete(_ensure())
    except Exception:
        try:
            asyncio.run(_ensure())
        except Exception:
            pass


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


_TRUNCATE_SQL = (
    "TRUNCATE weather_cache, placements, containers, spaces, sites, "
    "events, task_plants, tasks, watering_states, "
    "plant_photos, plant_tags, tags, plants, care_profiles, taxa, "
    "invitations, memberships, refresh_tokens, households, users "
    "RESTART IDENTITY CASCADE"
)


@pytest.fixture
async def clean_db():
    """Truncate app tables between integration tests (keeps migrations)."""
    # Safety: never truncate the live plantpilot DB
    if engine.url.database and engine.url.database != "plantpilot_test":
        raise RuntimeError(
            f"Refusing to truncate non-test database: {engine.url.database}. "
            "Set TEST_DATABASE_URL to plantpilot_test."
        )
    async with engine.begin() as conn:
        await conn.execute(text(_TRUNCATE_SQL))
    yield
    async with engine.begin() as conn:
        await conn.execute(text(_TRUNCATE_SQL))


async def setup_instance(
    client: AsyncClient,
    *,
    email: str | None = None,
    password: str = "password123",
    display_name: str = "Admin",
    household_name: str = "Home",
) -> dict:
    email = email or f"admin-{uuid.uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/api/v1/auth/setup",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
            "household_name": household_name,
            "timezone": "UTC",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    data["_password"] = password
    data["_email"] = email
    return data


def auth_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}
