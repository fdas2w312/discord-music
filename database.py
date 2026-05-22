"""SQLite persistence for lyrics cache, state, and settings."""

import aiosqlite
from config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS lyrics_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT NOT NULL DEFAULT '',
    lyrics TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(settings.DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """Initialize database schema."""
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await db.commit()
    finally:
        await db.close()


async def cache_lyrics(title: str, artist: str, lyrics: str, source: str = "manual") -> int:
    """Cache lyrics and return the row ID."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO lyrics_cache (title, artist, lyrics, source) VALUES (?, ?, ?, ?)",
            (title, artist, lyrics, source),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_cached_lyrics(cache_id: int) -> dict | None:
    """Get cached lyrics by ID."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM lyrics_cache WHERE id = ?", (cache_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def search_cached_lyrics(query: str) -> list[dict]:
    """Search cached lyrics by title or artist."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM lyrics_cache WHERE title LIKE ? OR artist LIKE ? ORDER BY created_at DESC LIMIT 20",
            (f"%{query}%", f"%{query}%"),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def save_state(key: str, value: str):
    """Save or update a state value."""
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO app_state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, value, value),
        )
        await db.commit()
    finally:
        await db.close()


async def load_state(key: str, default: str = "") -> str:
    """Load a state value."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT value FROM app_state WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else default
    finally:
        await db.close()


async def save_setting(key: str, value: str):
    """Save or update a setting."""
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, value, value),
        )
        await db.commit()
    finally:
        await db.close()


async def load_all_settings() -> dict:
    """Load all settings as a dict."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT key, value FROM settings")
        rows = await cursor.fetchall()
        return {r["key"]: r["value"] for r in rows}
    finally:
        await db.close()
