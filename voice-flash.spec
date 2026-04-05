# PyInstaller spec for voice-flash macOS .app bundle
# Build with: pyinstaller voice-flash.spec

import subprocess
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_all

block_cipher = None

# Collect all data files and hidden imports from heavy packages
whisper_datas, whisper_binaries, whisper_hidden = collect_all('whisper')
tiktoken_datas, tiktoken_binaries, tiktoken_hidden = collect_all('tiktoken')
genai_datas, genai_binaries, genai_hidden = collect_all('google.genai')

# Bundle PortAudio dylib for sounddevice.
# Find it via Homebrew; falls back to common paths.
def find_portaudio() -> list:
    candidates = [
        "/opt/homebrew/lib/libportaudio.dylib",   # Apple Silicon Homebrew
        "/usr/local/lib/libportaudio.dylib",       # Intel Homebrew
    ]
    try:
        prefix = subprocess.check_output(
            ["brew", "--prefix", "portaudio"], stderr=subprocess.DEVNULL
        ).decode().strip()
        candidates.insert(0, f"{prefix}/lib/libportaudio.dylib")
    except Exception:
        pass
    for path in candidates:
        if Path(path).exists():
            return [(path, ".")]
    return []


a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=whisper_binaries + tiktoken_binaries + genai_binaries + find_portaudio(),
    datas=whisper_datas + tiktoken_datas + genai_datas,
    hiddenimports=(
        whisper_hidden
        + tiktoken_hidden
        + genai_hidden
        + [
            "sounddevice",
            "pyttsx3",
            "pyttsx3.drivers",
            "pyttsx3.drivers.nsss",   # macOS TTS driver
            "pyttsx3.drivers.dummy",
            "google.genai",
            "google.auth",
            "pkg_resources",
            "sqlite3",
            "dotenv",
        ]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim unused torch components to reduce bundle size
        "torch.testing",
        "torch.distributions",
        "torchvision",
        "torchaudio",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="voice-flash",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,       # No terminal window
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file="entitlements.plist",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="voice-flash",
)

app = BUNDLE(
    coll,
    name="voice-flash.app",
    icon=None,
    bundle_identifier="com.chughes87.voice-flash",
    info_plist={
        # Required for macOS microphone permission dialog
        "NSMicrophoneUsageDescription": (
            "voice-flash listens to your spoken answers to check them against flashcard definitions."
        ),
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleName": "voice-flash",
        "CFBundleDisplayName": "voice-flash",
    },
)
