"""Asset search and download — uses Gemini for web search.

Flow:
1. Check local data/assets/{category}/ for fuzzy matches
2. If nothing local, ask Gemini to find a direct URL
3. Download the asset to data/assets/{category}/
4. Return the path (accessible via sandbox volume mount)
"""
from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

import httpx

from server.config import api_credentials_for, get_settings

logger = logging.getLogger(__name__)

ASSET_DIR = Path("data/assets")


def _sanitize_filename(query: str, ext: str) -> str:
    """Create a safe filename from a query string."""
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", query.lower())[:50]
    # Add hash for uniqueness
    h = hashlib.md5(query.encode()).hexdigest()[:6]
    return f"{clean}_{h}{ext}"


def search_local_assets(query: str, category: str) -> list[dict]:
    """Scan data/assets/{category}/ for files matching the query."""
    cat_dir = ASSET_DIR / category
    if not cat_dir.exists():
        return []

    query_lower = query.lower()
    query_words = set(query_lower.split())
    matches = []

    for f in cat_dir.iterdir():
        if not f.is_file():
            continue
        name_lower = f.stem.lower().replace("_", " ").replace("-", " ")
        name_words = set(name_lower.split())
        # Score by word overlap
        overlap = len(query_words & name_words)
        if overlap > 0 or any(w in name_lower for w in query_words):
            matches.append({
                "path": f"assets/{category}/{f.name}",
                "filename": f.name,
                "size": f.stat().st_size,
                "score": overlap,
            })

    return sorted(matches, key=lambda m: m["score"], reverse=True)


async def search_asset_url(query: str, category: str) -> str | None:
    """Ask Gemini to find a direct download URL for an asset."""
    s = get_settings()

    category_hints = {
        "meme": "meme image or GIF (direct image URL ending in .jpg, .png, .gif, or .webp)",
        "sfx": "sound effect audio file (direct URL ending in .mp3 or .wav)",
        "music": "background music track (direct URL ending in .mp3 or .wav)",
    }
    hint = category_hints.get(category, "file")

    prompt = (
        f'Find a direct download URL for this {hint}: "{query}"\n\n'
        "Requirements:\n"
        "- Return ONLY a single valid URL to the actual file (not a webpage)\n"
        "- The URL must end with a file extension (.gif, .png, .jpg, .mp3, .wav, etc.)\n"
        "- If you cannot find a direct file URL, return exactly: NONE\n"
        "- Do not return any other text, explanation, or formatting"
    )

    api_key, base_url = api_credentials_for(s.vlm_model)
    client = httpx.Client(
        timeout=30.0,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    payload = {
        "model": s.vlm_model,  # Gemini 3 Pro — has web search
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 256,
        "stream": False,
    }

    try:
        resp = client.post(f"{base_url}/chat/completions", json=payload)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()

        # Extract URL from response
        url = content.strip().strip('"').strip("'").strip("`")
        if url == "NONE" or not url.startswith("http"):
            # Try to find a URL in the response
            urls = re.findall(r'https?://\S+', content)
            if urls:
                url = urls[0].rstrip(")")
            else:
                logger.info("Gemini returned no URL for '%s': %s", query, content[:100])
                return None

        logger.info("Gemini found URL for '%s': %s", query, url[:100])
        return url
    except Exception as e:
        logger.error("Gemini search failed for '%s': %s", query, e)
        return None


async def download_asset(url: str, category: str, query: str) -> str | None:
    """Download an asset from a URL to data/assets/{category}/. Returns relative path."""
    # Determine extension from URL
    ext_match = re.search(r'\.(gif|png|jpg|jpeg|webp|mp3|wav|mp4|ogg)(\?|$)', url.lower())
    ext = f".{ext_match.group(1)}" if ext_match else ".bin"

    filename = _sanitize_filename(query, ext)
    dest = ASSET_DIR / category / filename
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.error("Download failed (%d) for %s", resp.status_code, url[:80])
                return None
            if len(resp.content) < 100:
                logger.warning("Downloaded file too small (%d bytes), skipping", len(resp.content))
                return None

            dest.write_bytes(resp.content)
            logger.info("Downloaded %s → %s (%.1f KB)", url[:60], dest, len(resp.content) / 1024)
            return f"assets/{category}/{filename}"
    except Exception as e:
        logger.error("Download failed for %s: %s", url[:60], e)
        return None


async def stage_asset(query: str, category: str) -> dict | None:
    """Find and stage an asset. Local search first, then Gemini fallback.

    Returns {"path": "assets/{category}/file.ext", "source": "local"|"web"} or None.
    """
    # 1. Check local assets
    local = search_local_assets(query, category)
    if local:
        best = local[0]
        logger.info("Found local asset for '%s': %s", query, best["path"])
        return {"path": best["path"], "source": "local", "filename": best["filename"]}

    # 2. Ask Gemini for a URL
    url = await search_asset_url(query, category)
    if not url:
        return None

    # 3. Download
    path = await download_asset(url, category, query)
    if not path:
        return None

    return {"path": path, "source": "web", "url": url}
