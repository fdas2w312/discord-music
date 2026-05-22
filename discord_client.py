"""Discord API client for managing custom status."""

import httpx
from config import settings

DISCORD_API_BASE = "https://discord.com/api/v10"


class DiscordClient:
    """Async client for Discord user API (custom status management)."""

    def __init__(self, token: str | None = None):
        self.token = token or settings.DISCORD_TOKEN
        self._previous_status: str | None = None
        self._previous_emoji: str | None = None

    def _headers(self) -> dict:
        return {
            "Authorization": f"{self.token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

    async def get_current_status(self) -> dict:
        """Fetch current user settings including custom status."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{DISCORD_API_BASE}/users/@me/settings",
                headers=self._headers(),
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def save_previous_status(self):
        """Save current custom status before we start scrolling."""
        try:
            data = await self.get_current_status()
            custom_status = data.get("custom_status", {}) or {}
            self._previous_status = custom_status.get("text", "")
            self._previous_emoji = custom_status.get("emoji_name", "")
        except Exception:
            self._previous_status = None
            self._previous_emoji = None

    async def set_status(self, text: str, emoji: str | None = None):
        """Set custom status text with optional emoji."""
        custom_status: dict = {"text": text}
        if emoji:
            custom_status["emoji_name"] = emoji

        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{DISCORD_API_BASE}/users/@me/settings",
                headers=self._headers(),
                json={"custom_status": custom_status},
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json() if resp.text else {}

    async def clear_status(self):
        """Clear custom status entirely."""
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{DISCORD_API_BASE}/users/@me/settings",
                headers=self._headers(),
                json={"custom_status": None},
                timeout=10.0,
            )
            resp.raise_for_status()

    async def restore_previous_status(self):
        """Restore the status that was active before scrolling started."""
        if self._previous_status is not None:
            await self.set_status(self._previous_status, self._previous_emoji)
        else:
            await self.clear_status()
