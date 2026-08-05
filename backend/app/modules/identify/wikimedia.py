"""Fetch free plant images (Wikipedia summary + Wikimedia Commons). No API key."""

from __future__ import annotations

from urllib.parse import quote

import httpx

WIKI_API = "https://commons.wikimedia.org/w/api.php"
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"
HEADERS = {
    "User-Agent": "RootCore/0.1 (self-hosted plant care; https://github.com/)",
    "Accept": "application/json",
}


def _search_variants(scientific_name: str) -> list[str]:
    name = scientific_name.strip()
    variants = [name]
    # Strip cultivar quotes: Rosa 'Hot Lips' → Rosa, Salvia microphylla 'Hot Lips'
    if "'" in name:
        base = name.split("'")[0].strip()
        if base:
            variants.append(base)
    parts = name.replace("'", " ").split()
    if len(parts) >= 2:
        variants.append(f"{parts[0]} {parts[1]}")
    if parts:
        variants.append(parts[0])
    # unique preserve order
    seen: set[str] = set()
    out: list[str] = []
    for v in variants:
        key = v.lower()
        if key not in seen and v:
            seen.add(key)
            out.append(v)
    return out


async def fetch_species_image_url(
    scientific_name: str,
    common_names: list[str] | None = None,
) -> str | None:
    queries = _search_variants(scientific_name)
    for common in common_names or []:
        c = (common or "").strip()
        if c and c.lower() not in {q.lower() for q in queries}:
            queries.append(c)
            # genus + common sometimes helps Commons
            parts = scientific_name.replace("'", " ").split()
            if parts:
                queries.append(f"{parts[0]} {c}")
    for query in queries:
        url = await _wikipedia_thumb(query)
        if url:
            return url
        url = await _commons_search(query)
        if url:
            return url
    return None


async def _wikipedia_thumb(title: str) -> str | None:
    """Wikipedia REST summary often has a reliable thumbnail."""
    try:
        path = quote(title.replace(" ", "_"), safe="")
        async with httpx.AsyncClient(timeout=15.0, headers=HEADERS, follow_redirects=True) as client:
            response = await client.get(WIKI_SUMMARY + path)
            if response.status_code != 200:
                return None
            data = response.json()
            # Prefer original / larger image when available
            original = (data.get("originalimage") or {}).get("source")
            if isinstance(original, str) and original:
                return original
            thumb = data.get("thumbnail") or {}
            src = thumb.get("source")
            if isinstance(src, str) and src:
                # Bump common Wikipedia thumb widths for a clearer cover photo
                for w in ("/50px-", "/100px-", "/200px-", "/220px-", "/250px-", "/300px-"):
                    if w in src:
                        return src.replace(w, "/800px-")
                return src
            return None
    except Exception:
        return None


async def _commons_search(query: str) -> str | None:
    hits = await search_commons_images(query, limit=1)
    return hits[0]["url"] if hits else None


async def search_commons_images(query: str, *, limit: int = 12) -> list[dict[str, str]]:
    """Search Wikimedia Commons for plant-related images the user can pick from."""
    q = (query or "").strip()
    if not q:
        return []
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{q} plant",
        "gsrlimit": min(max(limit, 1), 24),
        "gsrnamespace": 6,
        "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata",
        "iiurlwidth": 400,
        "iiurlheight": 400,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0, headers=HEADERS) as client:
            response = await client.get(WIKI_API, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception:
        return []

    pages = (data.get("query") or {}).get("pages") or {}
    out: list[dict[str, str]] = []
    for page in pages.values():
        title = str(page.get("title") or "").replace("File:", "")
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        mime = (info.get("mime") or "").lower()
        if mime not in {"image/jpeg", "image/png", "image/webp", "image/jpg"}:
            continue
        full = info.get("url") or ""
        thumb = info.get("thumburl") or full
        if not full and not thumb:
            continue
        # Prefer a larger download when setting cover
        download = full or thumb
        if "/thumb/" in download and download.endswith((".jpg", ".jpeg", ".png", ".webp")):
            pass
        out.append(
            {
                "title": title or q,
                "url": str(download),
                "thumb_url": str(thumb or download),
                "source": "wikimedia_commons",
            }
        )
    return out[:limit]


async def search_plant_images(
    query: str,
    *,
    limit: int = 12,
) -> list[dict[str, str]]:
    """Combine Wikipedia thumb + Commons search results for a picker UI."""
    q = (query or "").strip()
    if not q:
        return []
    results: list[dict[str, str]] = []
    seen: set[str] = set()

    # Wikipedia summary image first (often the best match)
    for variant in _search_variants(q)[:3]:
        wiki = await _wikipedia_thumb(variant)
        if wiki and wiki not in seen:
            seen.add(wiki)
            results.append(
                {
                    "title": f"Wikipedia · {variant}",
                    "url": wiki,
                    "thumb_url": wiki,
                    "source": "wikipedia",
                }
            )
            if len(results) >= 2:
                break

    for variant in _search_variants(q)[:4]:
        for hit in await search_commons_images(variant, limit=limit):
            u = hit.get("url") or ""
            if u and u not in seen:
                seen.add(u)
                results.append(hit)
            if len(results) >= limit:
                return results[:limit]
    return results[:limit]


async def download_image(url: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            content_type = "image/jpeg"
        return response.content, content_type
