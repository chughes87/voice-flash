#!/usr/bin/env bash
# voice-flash setup script
# Supports macOS (Homebrew) and Ubuntu/Debian Linux.

set -e

OS=$(uname -s)
PYTHON=""

echo "==> Detected OS: $OS"

# ---------------------------------------------------------------------------
# 1. System dependencies
# ---------------------------------------------------------------------------

if [ "$OS" = "Darwin" ]; then
    if ! command -v brew &>/dev/null; then
        echo ""
        echo "ERROR: Homebrew is required on macOS."
        echo "Install it from https://brew.sh, then re-run this script."
        exit 1
    fi

    echo "==> Installing system dependencies via Homebrew..."
    brew install portaudio ffmpeg

    # Tkinter is bundled with the python.org macOS installer but NOT with
    # Homebrew Python. Install python-tk to cover both cases.
    BREW_PYTHON_VERSION=$(brew list --formula | grep -E '^python@[0-9]' | sort -V | tail -1)
    if [ -n "$BREW_PYTHON_VERSION" ]; then
        TK_FORMULA="python-tk@${BREW_PYTHON_VERSION#python@}"
        echo "==> Installing $TK_FORMULA..."
        brew install "$TK_FORMULA" || true
    fi

    # Prefer the python.org install (has tkinter); fall back to brew python
    for candidate in python3 /usr/local/bin/python3 /opt/homebrew/bin/python3; do
        if command -v "$candidate" &>/dev/null; then
            PYTHON="$candidate"
            break
        fi
    done

elif [ "$OS" = "Linux" ]; then
    echo "==> Installing system dependencies via apt..."
    sudo apt update -q
    sudo apt install -y python3-venv python3-tk espeak-ng ffmpeg portaudio19-dev

    PYTHON=$(command -v python3)

else
    echo "ERROR: Unsupported OS: $OS"
    exit 1
fi

if [ -z "$PYTHON" ]; then
    echo "ERROR: Could not find python3. Install Python 3.10+ and re-run."
    exit 1
fi

echo "==> Using Python: $PYTHON ($($PYTHON --version))"

# ---------------------------------------------------------------------------
# 2. Verify tkinter is available
# ---------------------------------------------------------------------------

if ! $PYTHON -c "import tkinter" 2>/dev/null; then
    echo ""
    echo "WARNING: tkinter not found for $PYTHON."
    if [ "$OS" = "Darwin" ]; then
        echo "  Option A (recommended): Install Python from https://python.org — it includes tkinter."
        echo "  Option B: brew install python-tk@3.x  (match your Python minor version)"
    fi
    echo "  Setup will continue, but the app won't launch without tkinter."
    echo ""
fi

# ---------------------------------------------------------------------------
# 3. Virtual environment
# ---------------------------------------------------------------------------

if [ ! -d ".venv" ]; then
    echo "==> Creating virtual environment..."
    $PYTHON -m venv .venv
else
    echo "==> Virtual environment already exists, skipping creation."
fi

source .venv/bin/activate

# ---------------------------------------------------------------------------
# 4. Python dependencies
# ---------------------------------------------------------------------------

echo "==> Installing PyTorch (CPU-only, smaller download)..."
pip install --quiet torch --index-url https://download.pytorch.org/whl/cpu

echo "==> Installing remaining dependencies..."
pip install --quiet -r requirements.txt

# ---------------------------------------------------------------------------
# 5. Environment file
# ---------------------------------------------------------------------------

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "==> Created .env from .env.example."
    echo "    Add your Gemini API key (free at https://aistudio.google.com):"
    echo "      GEMINI_API_KEY=your_key_here"
else
    echo "==> .env already exists, skipping."
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo "==> Setup complete!"
echo ""
echo "    To run the app:"
echo "      source .venv/bin/activate"
echo "      python3 main.py"
echo ""
echo "    To run tests:"
echo "      source .venv/bin/activate"
echo "      pytest tests/ -v"
echo ""
