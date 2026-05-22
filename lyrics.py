"""Lyrics search via LRCLIB API with caching."""

import httpx
import database as db

LRCLIB_API = "https://lrclib.net/api"


async def search_lrclib(query: str) -> list[dict]:
    """Search for lyrics on LRCLIB. Returns list of results."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{LRCLIB_API}/search",
            params={"q": query},
            timeout=15.0,
        )
        resp.raise_for_status()
        results = resp.json()

        formatted = []
        for item in results:
            # Prefer synced lyrics, fallback to plain
            lyrics = item.get("syncedLyrics") or item.get("plainLyrics") or ""
            if not lyrics:
                continue
            formatted.append({
                "title": item.get("trackName", "Unknown"),
                "artist": item.get("artistName", "Unknown"),
                "album": item.get("albumName", ""),
                "lyrics": lyrics,
                "source": "lrclib",
                "id": item.get("id"),
            })
        return formatted


async def search(query: str) -> list[dict]:
    """Search lyrics: LRCLIB API first, then local cache."""
    results = []

    # Try LRCLIB
    try:
        api_results = await search_lrclib(query)
        results.extend(api_results)
    except Exception:
        pass

    # Also check local cache
    cached = await db.search_cached_lyrics(query)
    for item in cached:
        results.append({
            "title": item["title"],
            "artist": item["artist"],
            "lyrics": item["lyrics"],
            "source": "cache",
            "id": item["id"],
        })

    return results


async def get_lyrics(cache_id: int | None = None, lyrics_text: str | None = None,
                     title: str = "Manual", artist: str = "") -> str:
    """Get lyrics text by cache ID or raw text input. Caches and returns the text."""
    if lyrics_text:
        await db.cache_lyrics(title, artist, lyrics_text, source="manual")
        return lyrics_text

    if cache_id:
        cached = await db.get_cached_lyrics(cache_id)
        if cached:
            return cached["lyrics"]

    return ""


def clean_lyrics(raw: str) -> str:
    """Clean lyrics text: remove LRC timestamps, trim, keep line structure."""
    lines = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        # Remove LRC timestamps like [00:15.30]
        if line.startswith("[") and "]" in line:
            bracket_end = line.index("]") + 1
            line = line[bracket_end:].strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def parse_sentences(text: str) -> list[str]:
    """Parse lyrics into list of sentences. Each sentence ends with . ! ? or line break."""
    # Normalize: treat each line as a unit, split by sentence-ending punctuation
    sentences = []
    current = ""

    for char in text:
        current += char
        # End of sentence on . ! ? followed by space/newline, or just newline
        if char in ".!?":
            stripped = current.strip()
            if stripped:
                sentences.append(stripped)
            current = ""
        elif char == "\n":
            # Line break also acts as sentence boundary
            stripped = current.strip()
            if stripped:
                sentences.append(stripped)
            current = ""

    # Catch remaining text without ending punctuation
    stripped = current.strip()
    if stripped:
        sentences.append(stripped)

    return sentences
