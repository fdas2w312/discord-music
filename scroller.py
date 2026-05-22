"""Word-by-word scroller engine — types one word at a time, clears on sentence end."""

import asyncio
from config import settings
from discord_client import DiscordClient
import database as db
from lyrics import clean_lyrics, parse_sentences


class Scroller:
    """Background task that types lyrics word-by-word into Discord status.

    Behavior:
    - Types one (or more) words per tick
    - Builds up the current sentence progressively
    - When the sentence ends (period, exclamation, question mark, line break):
      shows the complete sentence for one tick, then clears and starts the next
    - Loops back to the first sentence after the last
    """

    def __init__(self, discord_client: DiscordClient):
        self.discord = discord_client
        self._running = False
        self._task: asyncio.Task | None = None
        self._sentences: list[str] = []
        self._current_sentence_idx: int = 0
        self._current_word_idx: int = 0
        self._song_title: str = ""
        self._current_display: str = ""

    @property
    def running(self) -> bool:
        return self._running

    @property
    def state(self) -> dict:
        total_words = sum(len(s.split()) for s in self._sentences) if self._sentences else 0
        words_done = 0
        for i in range(self._current_sentence_idx):
            words_done += len(self._sentences[i].split()) if i < len(self._sentences) else 0
        words_done += self._current_word_idx

        return {
            "running": self._running,
            "song_title": self._song_title,
            "current_text": self._current_display,
            "sentence_index": self._current_sentence_idx,
            "word_index": self._current_word_idx,
            "total_sentences": len(self._sentences),
            "total_words": total_words,
            "words_done": words_done,
            "progress": round(words_done / total_words * 100, 1) if total_words > 0 else 0,
        }

    def _get_sentence_words(self) -> list[str]:
        """Get words of the current sentence."""
        if not self._sentences or self._current_sentence_idx >= len(self._sentences):
            return []
        return self._sentences[self._current_sentence_idx].split()

    def _build_current_text(self) -> str:
        """Build the text to display: words up to current_word_idx in current sentence."""
        words = self._get_sentence_words()
        if not words:
            return ""
        end = min(self._current_word_idx, len(words))
        return " ".join(words[:end])

    async def start(self, raw_lyrics: str, song_title: str = "Unknown",
                    sentence_idx: int = 0, word_idx: int = 0):
        """Start word-by-word scrolling. Stops any previous scroll first."""
        await self.stop()

        cleaned = clean_lyrics(raw_lyrics)
        self._sentences = parse_sentences(cleaned)
        self._song_title = song_title
        self._current_sentence_idx = sentence_idx
        self._current_word_idx = word_idx
        self._running = True

        if not self._sentences:
            self._running = False
            return

        # Save previous Discord status
        await self.discord.save_previous_status()

        # Save state for persistence
        await db.save_state("song_title", song_title)
        await db.save_state("sentence_idx", str(sentence_idx))
        await db.save_state("word_idx", str(word_idx))
        await db.save_state("raw_lyrics", raw_lyrics)

        # Launch background task
        self._task = asyncio.create_task(self._scroll_loop())

    async def stop(self):
        """Stop scrolling and restore previous status."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._current_display = ""

        # Restore previous Discord status
        try:
            await self.discord.restore_previous_status()
        except Exception:
            pass

    async def _scroll_loop(self):
        """Main loop — types words, clears on sentence end, loops forever."""
        try:
            while self._running and self._sentences:
                words = self._get_sentence_words()

                if not words:
                    # Move to next sentence
                    self._current_sentence_idx += 1
                    self._current_word_idx = 0
                    if self._current_sentence_idx >= len(self._sentences):
                        self._current_sentence_idx = 0
                    continue

                total_words_in_sentence = len(words)

                # If we haven't finished the current sentence yet
                if self._current_word_idx <= total_words_in_sentence:
                    # Build and display current text
                    self._current_display = self._build_current_text()

                    if self._current_display:
                        full_status = f"{settings.EMOJI_PREFIX} {self._current_display}"
                        try:
                            await self.discord.set_status(full_status)
                        except Exception:
                            pass

                    # Advance word pointer
                    self._current_word_idx += settings.WORDS_PER_TICK

                    # Check if we just completed the sentence
                    if self._current_word_idx > total_words_in_sentence:
                        # Show the complete sentence for one extra tick (with the period/punctuation)
                        self._current_display = " ".join(words)
                        full_status = f"{settings.EMOJI_PREFIX} {self._current_display}"
                        try:
                            await self.discord.set_status(full_status)
                        except Exception:
                            pass

                        # Pause so the full sentence is visible
                        await asyncio.sleep(settings.PAUSE_AFTER_SENTENCE)

                        # Clear the status (blank tick before next sentence)
                        self._current_display = ""
                        try:
                            await self.discord.set_status(settings.EMOJI_PREFIX)
                        except Exception:
                            pass

                        await asyncio.sleep(settings.TICK_INTERVAL)

                        # Move to next sentence
                        self._current_sentence_idx += 1
                        self._current_word_idx = 0

                        # Loop around
                        if self._current_sentence_idx >= len(self._sentences):
                            self._current_sentence_idx = 0

                        # Persist state periodically
                        await db.save_state("sentence_idx", str(self._current_sentence_idx))
                        await db.save_state("word_idx", str(self._current_word_idx))
                        continue

                await asyncio.sleep(settings.TICK_INTERVAL)

        except asyncio.CancelledError:
            pass
        finally:
            self._running = False

    async def restore_from_state(self):
        """Restore scroller state from database after restart."""
        raw_lyrics = await db.load_state("raw_lyrics", "")
        if not raw_lyrics:
            return False

        song_title = await db.load_state("song_title", "Unknown")
        sentence_idx = int(await db.load_state("sentence_idx", "0"))
        word_idx = int(await db.load_state("word_idx", "0"))
        was_running = await db.load_state("was_running", "false")

        if was_running == "true":
            await self.start(raw_lyrics, song_title, sentence_idx, word_idx)
            return True
        return False
