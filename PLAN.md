# voice-flash: Voice Flashcard App with Spaced Repetition

## Context

Build a voice-driven flashcard application where the computer reads card prompts aloud, the user speaks their answer, and an LLM judges correctness. Correct answers prompt a 1–5 recall-ease rating used by the SM-2 spaced repetition algorithm to schedule future reviews. The app imports decks from Quizlet exports and persists all study state in a local SQLite database.

---

## Stack

| Concern | Choice | Reason |
|---|---|---|
| Language | Python 3.10+ | Best ecosystem for STT/TTS/ML |
| GUI | Tkinter | Built-in, no extra install |
| STT | openai-whisper `base` model (local) | Offline, accurate, ~74MB |
| TTS | pyttsx3 + espeak-ng | Fully offline |
| Answer check | Google Gemini 2.0 Flash API | Free tier (1,500 req/day) |
| Spaced rep | SM-2 algorithm | Standard Anki-style |
| Storage | SQLite (built-in sqlite3) | Zero-dependency persistence |
| Audio I/O | sounddevice + numpy | PortAudio-backed, cross-platform |

---

## Project Structure

```
voice-flash/
├── main.py
├── .env                        # GEMINI_API_KEY=... (gitignored)
├── .env.example
├── requirements.txt
├── app/
│   ├── config.py               # Constants, dotenv loading, paths
│   ├── models/
│   │   ├── card.py             # Card, Deck dataclasses
│   │   └── sm2.py              # Pure SM-2 function
│   ├── db/
│   │   ├── schema.py           # DDL strings
│   │   └── repository.py       # All SQLite CRUD
│   ├── services/
│   │   ├── importer.py         # Quizlet .txt parser
│   │   ├── audio.py            # sounddevice recording + energy VAD
│   │   ├── stt.py              # Whisper wrapper (holds loaded model)
│   │   ├── tts.py              # Thread-safe pyttsx3 wrapper
│   │   └── checker.py          # Gemini API call → CheckResult
│   └── gui/
│       ├── app_window.py       # Root Tk window, screen switcher
│       ├── deck_screen.py      # Deck selector / import screen
│       └── study_screen.py     # Main study loop (orchestrates all threads)
└── data/
    └── flashcards.db           # Auto-created on first run
```

---

## Data Models

### `app/models/card.py`
```python
@dataclass
class Card:
    id: Optional[int]       # None before first insert
    deck_id: int
    term: str               # Spoken to user
    definition: str         # Expected answer (checked by Gemini)
    ease_factor: float = 2.5
    interval: int = 1       # Days until next review
    repetitions: int = 0    # Consecutive correct responses
    due_date: date = field(default_factory=date.today)

@dataclass
class Deck:
    id: Optional[int]
    name: str
    source_file: str
    created_at: str
    card_count: int = 0
```

---

## SQLite Schema (`app/db/schema.py`)

```sql
CREATE TABLE IF NOT EXISTS decks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    source_file TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cards (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id      INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    term         TEXT NOT NULL,
    definition   TEXT NOT NULL,
    ease_factor  REAL    NOT NULL DEFAULT 2.5,
    interval     INTEGER NOT NULL DEFAULT 1,
    repetitions  INTEGER NOT NULL DEFAULT 0,
    due_date     TEXT    NOT NULL DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS reviews (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id       INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    reviewed_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    rating        INTEGER NOT NULL,       -- 1-5 user ease rating
    was_correct   INTEGER NOT NULL,       -- 0 or 1
    transcription TEXT,                   -- what Whisper heard
    new_interval  INTEGER NOT NULL,
    new_ef        REAL    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cards_deck_due ON cards(deck_id, due_date);
```

---

## Threading Model

Only the main thread may touch Tkinter widgets. Workers communicate back via `root.after(0, callback)`.

```
Per-card callback chain (all sequential):

_start_card()               [main thread]
  -> TTS: speak term         [TTS thread]
    -> _on_tts_done()        [main thread via after()]
      -> start recording     [Recording thread]
        -> _on_recording_done(audio)  [main thread via after()]
          -> transcribe      [STT thread]
            -> _on_transcript(text)   [main thread via after()]
              -> check answer [Gemini thread]
                -> _on_result(result) [main thread via after()]
                  -> show CORRECT/INCORRECT + rating buttons
                    -> _on_rating(n)  [main thread, button click]
                      -> SM-2 update -> DB write -> _start_card()
```

Use `queue.Queue` to pass data between threads. Use `threading.Event` for TTS completion signal.

---

## SM-2 Algorithm (`app/models/sm2.py`)

```
Input: card (ease_factor, interval, repetitions), rating (1-5)

Rating -> quality mapping:  1->0, 2->1, 3->2, 4->3, 5->5

If quality < 3:
    repetitions = 0
    interval = 1
    (ease_factor unchanged)
Else:
    if repetitions == 0:   interval = 1
    elif repetitions == 1: interval = 6
    else:                  interval = round(interval * ease_factor)
    ease_factor = ease_factor + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
    ease_factor = max(1.3, ease_factor)
    repetitions += 1

due_date = today + timedelta(days=interval)
```

**Rule:** If Gemini marks the answer incorrect, force rating=1 regardless of button pressed.

---

## Gemini Prompt (`app/services/checker.py`)

```
System: "You are a flashcard answer checker. Be lenient about synonyms,
minor transcription errors, articles, and partial answers that capture the
core concept. Be strict about factually wrong or completely unrelated answers.
Respond ONLY with valid JSON: {"correct": true/false, "reason": "one sentence"}"

User: "Term: {term}\nExpected: {definition}\nStudent said: {transcription}\nIs the student correct?"
```

Parse response with `json.loads()`, strip markdown code fences if present. On parse failure or API error, degrade gracefully: show definition text + manual CORRECT/INCORRECT buttons.

---

## Audio VAD Strategy (`app/services/audio.py`)

- `SAMPLE_RATE = 16000` Hz (Whisper's native rate — no resampling needed)
- `CHUNK_FRAMES = 1600` (100ms chunks)
- `SILENCE_DB = -40` dBFS threshold (configurable)
- `SILENCE_SECS = 1.5` consecutive silence to auto-stop
- `MAX_RECORD_SECS = 30` hard cap

State machine: `WAITING_FOR_SPEECH -> RECORDING -> DONE`

Energy per chunk: `db = 20 * log10(rms + 1e-10)`

"Done Speaking" button in GUI sets a `threading.Event` to force-stop recording at any time.

---

## Quizlet Import (`app/services/importer.py`)

Quizlet exports as UTF-8 tab-separated text: `term\tdefinition` per line.

```python
for line in text.splitlines():
    parts = line.strip().split('\t', 1)
    if len(parts) == 2:
        cards.append((parts[0], parts[1]))
```

Deck name defaults to the filename (without extension).

---

## GUI Layout (`app/gui/study_screen.py`)

```
+-----------------------------------+
|  Deck Name             [12/50]    |
+-----------------------------------+
|                                   |
|   [Card term text here]           |
|                                   |
+-----------------------------------+
| Status: LISTENING... / CHECKING.. |
| You said: "user transcription"    |
| Result: CORRECT / INCORRECT       |
| [Correct answer shown if wrong]   |
|                                   |
| Rate recall:  [1][2][3][4][5]     |
+-----------------------------------+
|  [Done Speaking]    [Skip Card]   |
+-----------------------------------+
```

Rating buttons are hidden until a result is shown. "All caught up" state shows next due date.

---

## System Dependencies

```bash
sudo apt install python3-tk espeak-ng ffmpeg portaudio19-dev
```

---

## requirements.txt

```
openai-whisper>=20231117
google-generativeai>=0.8.0
sounddevice>=0.4.6
numpy>=1.24.0
pyttsx3>=2.90
python-dotenv>=1.0.0
```

---

## Implementation Phases

### Phase 1 — Foundation
1. `requirements.txt`, `.env.example`, `app/config.py`
2. `app/db/schema.py` + `app/db/repository.py` (full CRUD)
3. `app/models/card.py` + `app/models/sm2.py`
4. `app/services/importer.py` — test with real Quizlet export
5. Smoke test: import deck -> query due cards -> apply SM-2 -> verify DB

### Phase 2 — Audio Pipeline (CLI test harness)
6. `app/services/audio.py` — record + VAD, save .wav to verify
7. `app/services/stt.py` — transcribe the .wav, confirm output
8. `app/services/tts.py` — speak a test string
9. `app/services/checker.py` — hardcoded Gemini call, confirm JSON parse

### Phase 3 — GUI Shell
10. `app/gui/app_window.py` — root window + screen switcher
11. `app/gui/deck_screen.py` — file picker, deck list, import button

### Phase 4 — Study Loop
12. `app/gui/study_screen.py` — full callback chain, all widgets
13. "Done Speaking" button override
14. "All caught up" state + next-due-date display

### Phase 5 — Polish
15. Whisper loading splash screen (loads in thread before enabling Study)
16. Graceful Gemini error fallback (manual CORRECT/INCORRECT buttons)
17. Deck stats view (cards due today, accuracy)
18. `main.py` final wiring + logging setup

---

## Verification

1. `python main.py` — app launches, Whisper loads (progress shown)
2. Import a Quizlet export (.txt) — deck appears in list with card count
3. Start study session — first card's term is spoken aloud
4. Speak correct answer — transcription appears, Gemini marks correct, rating buttons appear
5. Rate 1–5 — next card presented, SM-2 interval updated in DB
6. Speak wrong answer — correct answer read aloud, card scheduled for tomorrow
7. Complete all due cards — "All caught up" screen with next due date shown
8. Re-launch — study state (intervals, EF, due dates) persists correctly
