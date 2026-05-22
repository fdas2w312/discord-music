# Discord Lyrics Scroller — Design Spec

## Overview

A 24/7 background service that scrolls song lyrics as a "running line" in the user's Discord custom status. Managed via a local web panel on localhost:8080.

## Architecture

```
Web Panel (:8080) ←→ FastAPI Backend ←→ Discord API
                       ↕
                    SQLite (cache + state)
```

## Components

### 1. FastAPI Backend (`main.py`)
- REST API endpoints: /api/search, /api/start, /api/stop, /api/status, /api/settings
- Async httpx for Discord API calls
- Background task for scrolling loop
- Graceful shutdown: saves state, restores previous Discord status

### 2. Scroller Engine (`scroller.py`)
- Takes lyrics text, splits into lines, joins with separator
- Slides a 128-char window across the joined text
- Adjustable speed (chars per tick, tick interval in seconds)
- Wraps around when reaching end
- Emits current window text via callback

### 3. Discord Client (`discord_client.py`)
- PATCH /users/@me/settings with custom_status field
- Save/restore previous status
- Token from config/.env

### 4. Lyrics Search (`lyrics.py`)
- Primary: LRCLIB API (free, no key needed)
- Fallback: manual text input via web panel
- Cache results in SQLite

### 5. Web Panel (`static/`)
- Single-page HTML/CSS/JS
- Search song, start/stop scroller, adjust speed
- Real-time status display

### 6. Persistence (`database.py`)
- SQLite: lyrics cache, current state (song, position), settings
- Auto-creates tables on first run

### 7. Systemd Service (`discord-lyrics.service`)
- Auto-start on boot
- Restart on failure
- WorkingDirectory + EnvironmentFile

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/status | Current scroller state |
| GET | /api/search?q=... | Search lyrics via LRCLIB |
| POST | /api/start | Start scrolling (body: lyrics text or search result ID) |
| POST | /api/stop | Stop scrolling, restore status |
| GET | /api/settings | Get current settings |
| PUT | /api/settings | Update settings (speed, emoji prefix, etc.) |

## Data Flow

1. User searches song in web panel → LRCLIB API returns results
2. User selects song or pastes lyrics → POST /api/start
3. Backend saves lyrics to SQLite, starts background scroller task
4. Scroller slides 128-char window, calls Discord API each tick
5. On /api/stop or shutdown → restore previous Discord status

## Configuration (.env)

```
DISCORD_TOKEN=your_user_token_here
SCROLL_SPEED=3          # chars per tick
TICK_INTERVAL=2.0       # seconds between ticks
EMOJI_PREFIX=🎵         # emoji before lyrics text
WINDOW_SIZE=128         # Discord custom status char limit
```

## File Structure

```
discord-lyrics-scroller/
├── main.py              # FastAPI app + entry point
├── scroller.py          # Scrolling engine
├── discord_client.py    # Discord API wrapper
├── lyrics.py            # LRCLIB search + cache
├── database.py          # SQLite persistence
├── config.py            # Settings from .env
├── static/
│   ├── index.html       # Web panel
│   ├── style.css        # Styles
│   └── app.js           # Frontend logic
├── .env.example         # Template for environment variables
├── discord-lyrics.service  # systemd unit file
├── requirements.txt     # Python dependencies
└── docs/
    └── design.md        # This file
```
