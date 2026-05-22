"""Application configuration loaded from .env, then overridden by DB settings."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Defaults from .env (loaded once at import time)
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    WORDS_PER_TICK: int = int(os.getenv("WORDS_PER_TICK", "1"))
    TICK_INTERVAL: float = float(os.getenv("TICK_INTERVAL", "2.0"))
    EMOJI_PREFIX: str = os.getenv("EMOJI_PREFIX", "🎵")
    WINDOW_SIZE: int = int(os.getenv("WINDOW_SIZE", "128"))
    PAUSE_AFTER_SENTENCE: float = float(os.getenv("PAUSE_AFTER_SENTENCE", "1.0"))
    DB_PATH: str = os.getenv("DB_PATH", "data.db")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))

    async def load_from_db(self):
        """Override settings with values saved in database (if any).
        DB values take priority over .env — this is intentional:
        web panel changes persist across restarts."""
        import database as db
        rows = await db.load_all_settings()

        if "words_per_tick" in rows:
            self.WORDS_PER_TICK = int(rows["words_per_tick"])
        if "tick_interval" in rows:
            self.TICK_INTERVAL = float(rows["tick_interval"])
        if "emoji_prefix" in rows:
            self.EMOJI_PREFIX = rows["emoji_prefix"]
        if "pause_after_sentence" in rows:
            self.PAUSE_AFTER_SENTENCE = float(rows["pause_after_sentence"])


settings = Settings()
