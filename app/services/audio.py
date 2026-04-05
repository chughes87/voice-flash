"""
Audio recording with energy-based VAD (voice activity detection).

State machine: WAITING_FOR_SPEECH -> RECORDING -> DONE

Runs in a worker thread. Calls done_callback(np.ndarray) when finished.
The callback fires on the worker thread — callers must dispatch to the
main thread themselves (e.g. root.after(0, ...)).
"""

import threading
import numpy as np
import sounddevice as sd
from typing import Callable

from app.config import (
    SAMPLE_RATE,
    CHUNK_FRAMES,
    SILENCE_DB,
    SILENCE_SECS,
    SPEECH_SECS,
    MAX_RECORD_SECS,
)

_STATE_WAITING = "WAITING"
_STATE_RECORDING = "RECORDING"
_STATE_DONE = "DONE"


def _rms_db(chunk: np.ndarray) -> float:
    rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2))
    return 20.0 * np.log10(rms + 1e-10)


def record_until_silence(
    done_callback: Callable[[np.ndarray], None],
    stop_event: threading.Event,
) -> None:
    """
    Record from the default microphone until silence is detected or
    stop_event is set. Calls done_callback with the captured audio array.

    Audio is float32, mono, SAMPLE_RATE Hz — ready for Whisper directly.
    """
    chunks: list[np.ndarray] = []
    state = _STATE_WAITING

    # Thresholds in chunk counts
    silence_chunks_threshold = int(SILENCE_SECS / (CHUNK_FRAMES / SAMPLE_RATE))
    speech_chunks_threshold = int(SPEECH_SECS / (CHUNK_FRAMES / SAMPLE_RATE))
    max_chunks = int(MAX_RECORD_SECS / (CHUNK_FRAMES / SAMPLE_RATE))

    speech_chunk_count = 0
    silent_chunk_count = 0
    total_chunk_count = 0

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_FRAMES,
        ) as stream:
            while not stop_event.is_set():
                audio_chunk, _ = stream.read(CHUNK_FRAMES)
                chunk = audio_chunk[:, 0]  # flatten to 1D
                db = _rms_db(chunk)
                is_loud = db > SILENCE_DB
                total_chunk_count += 1

                if state == _STATE_WAITING:
                    if is_loud:
                        speech_chunk_count += 1
                        chunks.append(chunk)
                        if speech_chunk_count >= speech_chunks_threshold:
                            state = _STATE_RECORDING
                            silent_chunk_count = 0
                    else:
                        speech_chunk_count = 0
                        chunks.clear()

                elif state == _STATE_RECORDING:
                    chunks.append(chunk)
                    if not is_loud:
                        silent_chunk_count += 1
                        if silent_chunk_count >= silence_chunks_threshold:
                            state = _STATE_DONE
                            break
                    else:
                        silent_chunk_count = 0

                    if total_chunk_count >= max_chunks:
                        state = _STATE_DONE
                        break

    except Exception as e:
        # Surface the error to the callback via an empty array so the
        # GUI can handle it gracefully rather than hanging.
        done_callback(np.zeros(SAMPLE_RATE, dtype=np.float32))
        return

    if chunks:
        audio = np.concatenate(chunks)
    else:
        # No speech detected (stop_event fired during WAITING)
        audio = np.zeros(SAMPLE_RATE, dtype=np.float32)

    done_callback(audio)
