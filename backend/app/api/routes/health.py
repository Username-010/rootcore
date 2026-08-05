"""Health and readiness probes."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db.session import check_db_connection

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    database: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — process is up."""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> JSONResponse:
    """Readiness probe — dependencies are reachable."""
    db_ok = await check_db_connection()
    payload = ReadyResponse(
        status="ok" if db_ok else "degraded",
        database="up" if db_ok else "down",
    )
    code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=payload.model_dump(), status_code=code)
