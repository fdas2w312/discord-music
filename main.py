"""FastAPI application — Discord Lyrics Scroller."""

import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import database as db
from config import settings
from discord_client import DiscordClient
from scroller import Scroller
from lyrics import search as search_lyrics, get_lyrics

# Global instances
discord_client = DiscordClient()
scroller = Scroller(discord_client)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    await db.init_db()

    # Load settings from DB (overrides .env defaults)
    await settings.load_from_db()

    # Try to restore previous state
    await scroller.restore_from_state()

    yield

    # Graceful shutdown: save state and restore Discord status
    await db.save_state("was_running", "true" if scroller.running else "false")
    await scroller.stop()


app = FastAPI(title="Discord Lyrics Scroller", lifespan=lifespan)

# Serve static files
static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")


# ─── Request Models ───────────────────────────────────────────────

class StartRequest(BaseModel):
    lyrics: str | None = None
    cache_id: int | None = None
    title: str = "Unknown"
    artist: str = ""

class SettingsRequest(BaseModel):
    words_per_tick: int | None = None
    tick_interval: float | None = None
    emoji_prefix: str | None = None
    pause_after_sentence: float | None = None


# ─── API Routes ───────────────────────────────────────────────────

@app.get("/")
async def index():
    """Serve the web panel."""
    return FileResponse(os.path.join(static_path, "index.html"))


@app.get("/api/status")
async def get_status():
    """Get current scroller state."""
    return scroller.state


@app.get("/api/search")
async def api_search(q: str = ""):
    """Search for lyrics."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    results = await search_lyrics(q)
    return {"results": results}


@app.post("/api/start")
async def api_start(req: StartRequest):
    """Start scrolling lyrics."""
    if not req.lyrics and not req.cache_id:
        raise HTTPException(status_code=400, detail="Provide 'lyrics' text or 'cache_id'")

    lyrics_text = await get_lyrics(
        cache_id=req.cache_id,
        lyrics_text=req.lyrics,
        title=req.title,
        artist=req.artist,
    )

    if not lyrics_text:
        raise HTTPException(status_code=404, detail="Lyrics not found")

    await scroller.start(lyrics_text, song_title=req.title)
    await db.save_state("was_running", "true")
    return {"status": "started", "title": req.title}


@app.post("/api/stop")
async def api_stop():
    """Stop scrolling and restore previous status."""
    await scroller.stop()
    await db.save_state("was_running", "false")
    return {"status": "stopped"}


@app.get("/api/settings")
async def api_get_settings():
    """Get current settings."""
    return {
        "words_per_tick": settings.WORDS_PER_TICK,
        "tick_interval": settings.TICK_INTERVAL,
        "emoji_prefix": settings.EMOJI_PREFIX,
        "pause_after_sentence": settings.PAUSE_AFTER_SENTENCE,
    }


@app.put("/api/settings")
async def api_update_settings(req: SettingsRequest):
    """Update runtime settings."""
    if req.words_per_tick is not None:
        settings.WORDS_PER_TICK = req.words_per_tick
        await db.save_setting("words_per_tick", str(req.words_per_tick))

    if req.tick_interval is not None:
        settings.TICK_INTERVAL = req.tick_interval
        await db.save_setting("tick_interval", str(req.tick_interval))

    if req.emoji_prefix is not None:
        settings.EMOJI_PREFIX = req.emoji_prefix
        await db.save_setting("emoji_prefix", req.emoji_prefix)

    if req.pause_after_sentence is not None:
        settings.PAUSE_AFTER_SENTENCE = req.pause_after_sentence
        await db.save_setting("pause_after_sentence", str(req.pause_after_sentence))

    return {
        "words_per_tick": settings.WORDS_PER_TICK,
        "tick_interval": settings.TICK_INTERVAL,
        "emoji_prefix": settings.EMOJI_PREFIX,
        "pause_after_sentence": settings.PAUSE_AFTER_SENTENCE,
    }


# ─── Entry Point ──────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
