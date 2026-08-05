"""Local media storage and signed URL helpers."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
from PIL import Image, ImageOps

from app.core.config import get_settings

ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class MediaError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def media_root() -> Path:
    path = Path(get_settings().media_root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_plant_image(
    *,
    household_id: uuid.UUID,
    plant_id: uuid.UUID,
    data: bytes,
    content_type: str,
) -> dict:
    if content_type not in ALLOWED_MIME:
        raise MediaError("Unsupported image type. Use JPEG, PNG, or WebP.", status_code=415)

    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise MediaError(f"File exceeds {settings.max_upload_mb} MB limit", status_code=413)

    try:
        image = Image.open(io.BytesIO(data))
        image = ImageOps.exif_transpose(image)
        image.load()
    except Exception as exc:
        raise MediaError("Invalid image file") from exc

    photo_id = uuid.uuid4()
    ext = ALLOWED_MIME[content_type]
    base = f"{household_id}/plants/{plant_id}/{photo_id}"
    original_key = f"{base}/original{ext}"
    display_key = f"{base}/display.jpg"
    thumb_key = f"{base}/thumb.jpg"

    root = media_root()
    original_path = root / original_key
    original_path.parent.mkdir(parents=True, exist_ok=True)
    original_path.write_bytes(data)

    rgb = image.convert("RGB") if image.mode not in ("RGB", "L") else image.convert("RGB")
    width, height = rgb.size

    display = rgb.copy()
    display.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    display.save(root / display_key, format="JPEG", quality=85, optimize=True)

    thumb = rgb.copy()
    thumb.thumbnail((400, 400), Image.Resampling.LANCZOS)
    thumb.save(root / thumb_key, format="JPEG", quality=80, optimize=True)

    return {
        "id": photo_id,
        "storage_key": original_key,
        "display_key": display_key,
        "thumb_key": thumb_key,
        "mime_type": content_type,
        "byte_size": len(data),
        "width": width,
        "height": height,
    }


def delete_media_keys(*keys: str | None) -> None:
    root = media_root()
    for key in keys:
        if not key:
            continue
        path = root / key
        if path.is_file():
            path.unlink(missing_ok=True)


def absolute_media_path(storage_key: str) -> Path:
    path = (media_root() / storage_key).resolve()
    root = media_root().resolve()
    if not str(path).startswith(str(root)):
        raise MediaError("Invalid media path", status_code=400)
    return path


def sign_media_url(storage_key: str, *, minutes: int = 15) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sk": storage_key,
            "type": "media",
            "iat": now,
            "exp": now + timedelta(minutes=minutes),
        },
        settings.secret_key,
        algorithm="HS256",
    )
    return f"/api/v1/media/{token}"


def decode_media_token(token: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise MediaError("Invalid or expired media link", status_code=401) from exc
    if payload.get("type") != "media" or not payload.get("sk"):
        raise MediaError("Invalid media token", status_code=401)
    return str(payload["sk"])
