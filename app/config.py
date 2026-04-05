import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "flashcards.db"

DATA_DIR.mkdir(exist_ok=True)

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

# Whisper
WHISPER_MODEL = "base"

# Audio recording / VAD
SAMPLE_RATE = 16000       # Hz — Whisper's native rate
CHUNK_FRAMES = 1600       # 100ms chunks
SILENCE_DB = -40          # dBFS threshold for silence detection
SILENCE_SECS = 1.5        # Consecutive silence seconds before auto-stop
SPEECH_SECS = 0.3         # Minimum speech before silence detection kicks in
MAX_RECORD_SECS = 30      # Hard cap on recording length
