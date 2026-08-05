"""PlantNet API client (optional — free API key from my.plantnet.org)."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings

PLANTNET_URL = "https://my-api.plantnet.org/v2/identify/all"


async def identify_plant(
    image_bytes: bytes,
    *,
    filename: str = "photo.jpg",
    content_type: str = "image/jpeg",
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    key = api_key or get_settings().plantnet_api_key
    if not key:
        raise RuntimeError(
            "PlantNet API key not configured. Add PLANTNET_API_KEY to .env "
            "or set it in household settings (free key at https://my.plantnet.org/)."
        )

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            PLANTNET_URL,
            params={"api-key": key},
            files={"images": (filename, image_bytes, content_type)},
            data={"organs": "auto"},
        )
        if response.status_code == 401:
            raise RuntimeError("PlantNet rejected the API key")
        if response.status_code >= 400:
            raise RuntimeError(f"PlantNet error: {response.status_code} {response.text[:200]}")
        data = response.json()

    results = data.get("results") or []
    out: list[dict[str, Any]] = []
    for item in results[:8]:
        score = float(item.get("score") or 0)
        species = item.get("species") or {}
        sci = species.get("scientificNameWithoutAuthor") or species.get("scientificName") or ""
        common = species.get("commonNames") or []
        out.append(
            {
                "score": round(score, 4),
                "scientific_name": sci,
                "common_names": common[:5] if isinstance(common, list) else [],
                "family": (species.get("family") or {}).get("scientificNameWithoutAuthor"),
                "genus": (species.get("genus") or {}).get("scientificNameWithoutAuthor"),
            }
        )
    return out
