"""
Speech-to-text wrapper around OpenAI Whisper.

Load once at startup (model loading takes a few seconds) and call
transcribe() per recording. Thread-safe for reads — the model is
stateless after loading.
"""

import numpy as np
import whisper

from app.config import WHISPER_MODEL


class STTService:
    def __init__(self) -> None:
        self._model = None

    def load(self) -> None:
        """Load the Whisper model. Call once at startup (blocking ~3-10s)."""
        self._model = whisper.load_model(WHISPER_MODEL)

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe a float32 mono 16kHz audio array.
        Returns the transcript string (stripped), or "" on failure.
        """
        if self._model is None:
            raise RuntimeError("STTService.load() must be called before transcribe()")

        if audio is None or len(audio) == 0:
            return ""

        result = self._model.transcribe(audio, fp16=False, language="en")
        return result.get("text", "").strip()
