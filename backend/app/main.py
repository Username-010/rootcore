"""FastAPI application factory and ASGI entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes import auth, care, extras, health, households, meta, plants
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import AsyncSessionLocal
from app.modules.households import models as household_models  # noqa: F401
from app.modules.identity import models as identity_models  # noqa: F401
from app.modules.layout import models as layout_models  # noqa: F401
from app.modules.plants import models as plant_models  # noqa: F401
from app.modules.tasks import models as task_models  # noqa: F401
from app.modules.taxonomy import models as taxonomy_models  # noqa: F401
from app.modules.taxonomy.service import seed_global_taxa
from app.modules.timeline import models as timeline_models  # noqa: F401
from app.modules.watering import models as watering_models  # noqa: F401
from app.modules.weather import models as weather_models  # noqa: F401


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    settings = get_settings()
    media = Path(settings.media_root)
    media.mkdir(parents=True, exist_ok=True)
    # Seed / top-up global taxa catalog (inserts missing species on every boot)
    try:
        async with AsyncSessionLocal() as session:
            # force=True refreshes bloom/fertilize extras on existing seed taxa
            inserted = await seed_global_taxa(session, force=True)
            await session.commit()
            if inserted:
                import logging

                logging.getLogger("rootcore").info("Seeded %s new global taxa", inserted)
    except Exception as exc:
        # DB may not be ready during certain test imports
        import logging

        logging.getLogger("rootcore").warning("Taxa seed skipped: %s", exc)
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Self-hosted plant care platform API. "
            "Adaptive watering, households, layouts, and more."
        ),
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router)
    application.include_router(meta.router)
    application.include_router(auth.router)
    application.include_router(households.router)
    application.include_router(plants.router)
    application.include_router(care.router)
    application.include_router(extras.router)

    # Production: serve built SPA (assets + SPA fallback)
    if settings.static_dir:
        static_path = Path(settings.static_dir)
        if static_path.is_dir():
            assets = static_path / "assets"
            if assets.is_dir():
                application.mount(
                    "/assets",
                    StaticFiles(directory=str(assets)),
                    name="assets",
                )

            @application.get("/{full_path:path}")
            async def spa_fallback(full_path: str) -> FileResponse:
                # Do not shadow API / health routes (already registered above)
                candidate = static_path / full_path
                if full_path and candidate.is_file():
                    return FileResponse(candidate)
                return FileResponse(static_path / "index.html")

    return application


app = create_app()
