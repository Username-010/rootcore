"""Pre-parser request bounds for sensor mutations only (no upstream or DB I/O)."""

import re

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import get_settings

MAX_SENSOR_BODY_BYTES = 4096
_SENSOR_PATH = re.compile(
    r"^/api/v1/households/[^/]+/(?:sensor-bindings(?:/[^/]+)?|"
    r"integrations/home_assistant/test)/?$"
)


def write_guard(request: Request):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    settings = get_settings()
    origin = request.headers.get("origin")
    allowed = {
        str(request.base_url).rstrip("/"),
        settings.public_base_url.rstrip("/"),
        *settings.cors_origin_list,
    }
    if request.headers.get("sec-fetch-site") == "cross-site" or (
        origin and origin not in allowed
    ):
        raise HTTPException(403, "Cross-site writes are not allowed")
    try:
        length = int(request.headers.get("content-length", "0"))
        if length < 0:
            raise ValueError
        if length > MAX_SENSOR_BODY_BYTES:
            raise HTTPException(413, "Request too large")
    except ValueError:
        raise HTTPException(400, "Invalid content length") from None


async def bounded_body(request: Request):
    body = bytearray()
    async for chunk in request.stream():
        # Check before extending: never copy an unbounded chunk into our buffer.
        if len(chunk) > MAX_SENSOR_BODY_BYTES - len(body):
            raise HTTPException(413, "Request too large")
        body.extend(chunk)
    return bytes(body)


class SensorBodyLimitMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if (
            scope["type"] != "http"
            or scope["method"] in {"GET", "HEAD", "OPTIONS"}
            or not _SENSOR_PATH.fullmatch(scope["path"])
        ):
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive)
        try:
            write_guard(request)
            # Presence only; shared auth still validates credentials and membership.
            authorization = request.headers.get("authorization", "").split()
            if not (
                len(authorization) == 2 and authorization[0].lower() == "bearer"
            ) and not request.cookies.get("access_token"):
                raise HTTPException(
                    401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"}
                )
            body = await bounded_body(request)
        except HTTPException as exc:
            await JSONResponse(
                {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
            )(scope, receive, send)
            return
        scope["sensor_body_bounded"] = True
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
