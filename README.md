# voice-flash

A voice-driven flashcard app with spaced repetition. The computer reads your flashcard prompts aloud, you speak your answer, and an LLM judges whether you got it right. Correct answers prompt a 1–5 ease rating that feeds the SM-2 spaced repetition algorithm, so cards you struggle with come back sooner.

## Features

- **Fully voice-driven** — hands-free study session
- **Local speech recognition** — OpenAI Whisper runs on your machine, no cloud STT
- **LLM answer checking** — Google Gemini 2.0 Flash grades your spoken answer semantically (synonyms, paraphrasing, and minor transcription errors handled gracefully)
- **SM-2 spaced repetition** — same algorithm used by Anki
- **Quizlet import** — paste in any Quizlet tab-separated export and go
- **Fully offline TTS** — pyttsx3 + espeak-ng reads cards and answers aloud

## Requirements

### System packages

```bash
sudo apt install python3.12-venv python3-tk espeak-ng ffmpeg portaudio19-dev
```

### Python

Python 3.10 or newer.

## Setup

**1. Clone and enter the repo**

```bash
git clone git@github.com:chughes87/voice-flash.git
cd voice-flash
```

**2. Create a virtual environment and install dependencies**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

> Installing the CPU-only build of PyTorch first keeps the install size manageable (~900MB vs ~3GB for the CUDA build).

**3. Set your Gemini API key**

Copy the example env file and add your key:

```bash
cp .env.example .env
```

Then edit `.env`:

```
GEMINI_API_KEY=your_api_key_here
```

Get a free key at [aistudio.google.com](https://aistudio.google.com). The free tier allows 1,500 requests/day — plenty for study sessions.

**4. Run the app**

```bash
python3 main.py
```

On first launch, Whisper downloads the `base` model (~74MB). This only happens once.

## Importing a Quizlet deck

1. Open your deck on Quizlet
2. Click **Export** → choose **Tab between term and definition**, **New line between cards**
3. Copy the text and save it as a `.txt` file
4. In voice-flash, click **Import Deck** and select the file

## Study session flow

1. The card's term is read aloud
2. Speak your answer
3. Gemini checks if your answer is correct
   - **Correct** — you're asked to rate how easy it was to recall (1–5), then the next card plays
   - **Incorrect** — the correct answer is read aloud, the card is scheduled to repeat tomorrow
4. SM-2 updates the card's schedule based on your rating

### Ease rating scale

| Rating | Meaning |
|--------|---------|
| 1 | Complete blank — didn't know it |
| 2 | Wrong but it felt familiar |
| 3 | Got it, but it was hard |
| 4 | Got it with a little hesitation |
| 5 | Instant, effortless recall |

## Running tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

71 tests covering SM-2 algorithm, Quizlet parsing, database CRUD, and Gemini response parsing.

## Project structure

```
voice-flash/
├── main.py                  # Entry point
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
