"""Authentication and profile routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import CurrentUser, DbSession, client_meta
from app.core.config import get_settings
from app.modules.identity import service as identity_service
from app.modules.identity.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    SetupRequest,
    SetupResponse,
    TokenResponse,
    UpdateProfileRequest,
    UserPublic,
)
from app.modules.identity.service import AuthError, count_users

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    settings = get_settings()
    secure = settings.app_env == "production"
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def _auth_error(exc: AuthError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get("/status")
async def auth_status(db: DbSession) -> dict:
    """Public bootstrap status for the SPA."""
    settings = get_settings()
    users = await count_users(db)
    return {
        "initialized": users > 0,
        "registration_mode": settings.registration_mode,
        "user_count": users if settings.app_env == "development" else None,
    }


@router.post("/setup", response_model=SetupResponse, status_code=status.HTTP_201_CREATED)
async def setup(
    body: SetupRequest,
    response: Response,
    db: DbSession,
    meta: Annotated[tuple[str | None, str | None], Depends(client_meta)],
) -> SetupResponse:
    user_agent, ip = meta
    try:
        user, household = await identity_service.setup_instance(
            db,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            household_name=body.household_name,
            timezone=body.timezone,
            latitude=body.latitude,
            longitude=body.longitude,
        )
        access, refresh = await identity_service.issue_tokens(
            db, user, user_agent=user_agent, ip_address=ip
        )
        await db.commit()
    except AuthError as exc:
        await db.rollback()
        raise _auth_error(exc) from exc

    _set_auth_cookies(response, access, refresh)
    return SetupResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserPublic.model_validate(user),
        household_id=household.id,
        household_name=household.name,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    db: DbSession,
    meta: Annotated[tuple[str | None, str | None], Depends(client_meta)],
) -> TokenResponse:
    user_agent, ip = meta
    try:
        user = await identity_service.register_user(
            db,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            timezone=body.timezone,
        )
        access, refresh = await identity_service.issue_tokens(
            db, user, user_agent=user_agent, ip_address=ip
        )
        await db.commit()
    except AuthError as exc:
        await db.rollback()
        raise _auth_error(exc) from exc

    _set_auth_cookies(response, access, refresh)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserPublic.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: DbSession,
    meta: Annotated[tuple[str | None, str | None], Depends(client_meta)],
) -> TokenResponse:
    user_agent, ip = meta
    try:
        user = await identity_service.authenticate(
            db, email=body.email, password=body.password
        )
        access, refresh = await identity_service.issue_tokens(
            db, user, user_agent=user_agent, ip_address=ip
        )
        await db.commit()
    except AuthError as exc:
        await db.rollback()
        raise _auth_error(exc) from exc

    if body.client == "web":
        _set_auth_cookies(response, access, refresh)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserPublic.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    response: Response,
    db: DbSession,
    request: Request,
    body: RefreshRequest | None = None,
    meta: Annotated[tuple[str | None, str | None], Depends(client_meta)] = (None, None),
) -> TokenResponse:
    user_agent, ip = meta
    raw = None
    if body and body.refresh_token:
        raw = body.refresh_token
    else:
        raw = request.cookies.get("refresh_token")

    if not raw:
        raise HTTPException(status_code=401, detail="Refresh token required")

    try:
        user, access, refresh = await identity_service.rotate_refresh_token(
            db, raw, user_agent=user_agent, ip_address=ip
        )
        await db.commit()
    except AuthError as exc:
        await db.rollback()
        raise _auth_error(exc) from exc

    _set_auth_cookies(response, access, refresh)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserPublic.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    db: DbSession,
    request: Request,
    body: RefreshRequest | None = None,
) -> MessageResponse:
    raw = (body.refresh_token if body else None) or request.cookies.get("refresh_token")
    await identity_service.revoke_refresh_token(db, raw)
    await db.commit()
    _clear_auth_cookies(response)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserPublic)
async def me(user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(user)


@router.patch("/me", response_model=UserPublic)
async def update_me(
    body: UpdateProfileRequest,
    user: CurrentUser,
    db: DbSession,
) -> UserPublic:
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return UserPublic.model_validate(user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    user: CurrentUser,
    db: DbSession,
    response: Response,
) -> MessageResponse:
    try:
        await identity_service.change_password(
            db,
            user,
            current_password=body.current_password,
            new_password=body.new_password,
        )
        await db.commit()
    except AuthError as exc:
        await db.rollback()
        raise _auth_error(exc) from exc

    _clear_auth_cookies(response)
    return MessageResponse(message="Password changed. Please log in again.")
