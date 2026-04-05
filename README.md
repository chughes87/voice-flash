# voice-flash

A voice-driven flashcard app with spaced repetition. The computer reads your flashcard prompts aloud, you speak your answer, and an LLM judges whether you got it right. Correct answers prompt a 1–5 ease rating that feeds the SM-2 spaced repetition algorithm, so cards you struggle with come back sooner.

## Features

- **Fully voice-driven** — hands-free study session
- **Local speech recognition** — OpenAI Whisper runs on your machine, no cloud STT
- **LLM answer checking** — Google Gemini 2.0 Flash grades your spoken answer semantically (synonyms, paraphrasing, and minor transcription errors handled gracefully)
- **SM-2 spaced repetition** — same algorithm used by Anki
- **Quizlet import** — load any Quizlet tab-separated export and go
- **Offline TTS** — pyttsx3 reads cards aloud using your OS's built-in voice engine

## Requirements

- Python 3.10 or newer
- macOS or Ubuntu/Debian Linux
- A free [Google AI Studio](https://aistudio.google.com) API key (1,500 requests/day free)

## Setup

**1. Clone the repo**

```bash
git clone git@github.com:chughes87/voice-flash.git
cd voice-flash
```

**2. Run the setup script**

```bash
bash setup.sh
```

This installs system dependencies, creates a Python virtual environment, and installs all Python packages. It also creates a `.env` file for your API key.

> On macOS, [Homebrew](https://brew.sh) must be installed first. On Linux, `sudo` access is required for `apt`.

**3. Add your Gemini API key**

Edit the `.env` file created by setup:

```
GEMINI_API_KEY=your_key_here
```

Get a free key at [aistudio.google.com](https://aistudio.google.com).

**4. Run the app**

```bash
source .venv/bin/activate
python3 main.py
```

On first launch, Whisper downloads the `base` model (~74MB). This only happens once.

---

### macOS notes

- Tkinter is bundled with the [python.org macOS installer](https://www.python.org/downloads/). If you're using Homebrew Python and tkinter is missing, run `brew install python-tk@3.x` (replace `3.x` with your Python version).
- macOS uses its built-in `NSSpeechSynthesizer` for TTS — no espeak needed, and the voice quality is better than Linux.
- You'll be prompted to grant microphone access on first run.

---

## Importing a Quizlet deck

1. Open your deck on Quizlet
2. Click **Export** → choose **Tab between term and definition**, **New line between cards**
3. Copy the text and save it as a `.txt` file
4. In voice-flash, click **+ Import Deck** and select the file

## Study session flow

1. The card's term is read aloud
2. Speak your answer
3. Gemini checks if your answer is correct
   - **Correct** — rate how easy it was to recall (1–5), then the next card plays
   - **Incorrect** — the correct answer is read aloud, the card is scheduled to repeat tomorrow
4. SM-2 updates the card's schedule based on your rating

### Ease rating scale

| Rating | Meaning |
|--------|---------|
| 1 | Complete blank |
| 2 | Wrong but it felt familiar |
| 3 | Got it, but it was hard |
| 4 | Got it with a little hesitation |
| 5 | Instant, effortless recall |

## Running tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

71 tests covering the SM-2 algorithm, Quizlet parsing, database CRUD, and Gemini response parsing.

## Project structure

```
voice-flash/
├── main.py                  # Entry point
├── setup.sh                 # Cross-platform install script (macOS + Linux)
├── app/
│   ├── config.py            # Constants and env loading
│   ├── models/
│   │   ├── card.py          # Card and Deck dataclasses
│   │   └── sm2.py           # SM-2 spaced repetition algorithm
│   ├── db/
│   │   ├── schema.py        # SQLite schema
│   │   └── repository.py    # Database operations
│   ├── services/
│   │   ├── importer.py      # Quizlet export parser
│   │   ├── audio.py         # Microphone recording with VAD
│   │   ├── stt.py           # Whisper speech-to-text
│   │   ├── tts.py           # pyttsx3 text-to-speech
│   │   └── checker.py       # Gemini answer checker
│   └── gui/
│       ├── app_window.py    # Root window and screen switcher
│       ├── deck_screen.py   # Deck list and import
│       └── study_screen.py  # Study loop UI
└── tests/                   # pytest test suite
```

## Configuration

Tunable constants in `app/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `WHISPER_MODEL` | `"base"` | Whisper model size (`tiny`, `base`, `small`, `medium`) |
| `SILENCE_DB` | `-40` | dBFS threshold for silence detection |
| `SILENCE_SECS` | `1.5` | Seconds of silence before recording stops |
| `MAX_RECORD_SECS` | `30` | Hard cap on recording length |

## License

MIT
