"""Public application metadata."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import __version__
from app.api.deps import DbSession
from app.core.config import get_settings
from app.modules.identity.service import count_users

router = APIRouter(prefix="/api/v1", tags=["system"])


class Features(BaseModel):
    plantnet: bool
    smtp: bool = False


class MetaResponse(BaseModel):
    name: str
    version: str
    registration_mode: str
    initialized: bool
    features: Features
    docs_url: str = Field(description="OpenAPI UI path")


@router.get("/meta", response_model=MetaResponse)
async def meta(db: DbSession) -> MetaResponse:
    settings = get_settings()
    users = await count_users(db)
    return MetaResponse(
        name=settings.app_name,
        version=__version__,
        registration_mode=settings.registration_mode,
        initialized=users > 0,
        features=Features(
            plantnet=bool(settings.plantnet_api_key),
            smtp=False,
        ),
        docs_url="/api/docs",
    )
