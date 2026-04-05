import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# When running as a PyInstaller .app bundle, __file__ is inside the read-only
# app bundle. User data (DB, .env) must live in a writable location instead.

_bundled = getattr(sys, "frozen", False)

if _bundled:
    # macOS: ~/Library/Application Support/voice-flash/
    _APP_SUPPORT = Path.home() / "Library" / "Application Support" / "voice-flash"
else:
    _APP_SUPPORT = Path(__file__).parent.parent

DATA_DIR = _APP_SUPPORT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "flashcards.db"

# Load .env from the app-support dir first, then fall back to project root
load_dotenv(_APP_SUPPORT / ".env")
load_dotenv()  # project root .env (dev mode)

# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

# ---------------------------------------------------------------------------
# Whisper
# ---------------------------------------------------------------------------
WHISPER_MODEL = "base"

# ---------------------------------------------------------------------------
# Audio recording / VAD
# ---------------------------------------------------------------------------
SAMPLE_RATE = 16000       # Hz — Whisper's native rate
CHUNK_FRAMES = 1600       # 100ms chunks
SILENCE_DB = -40          # dBFS threshold for silence detection
SILENCE_SECS = 1.5        # Consecutive silence seconds before auto-stop
SPEECH_SECS = 0.3         # Minimum speech before silence detection kicks in
MAX_RECORD_SECS = 30      # Hard cap on recording length
