"""
Thread-safe text-to-speech wrapper around pyttsx3.

Uses a single persistent worker thread that owns the pyttsx3 engine for
the lifetime of the app. This avoids the weakref crash that occurs when
the engine is created on a short-lived thread and gets garbage collected
before espeak's async callback fires.
"""

import queue
import threading
import pyttsx3

_STOP = object()  # sentinel to shut down the worker


class TTSService:
    def __init__(self) -> None:
        self._queue: queue.Queue = queue.Queue()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def speak(self, text: str, done_callback: callable = None) -> None:
        """
        Queue text to be spoken. Calls done_callback() (no args) on the
        TTS worker thread when the utterance finishes.
        """
        self._queue.put((text, done_callback))

    def _run(self) -> None:
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)

        while True:
            item = self._queue.get()
            if item is _STOP:
                break
            text, done_callback = item
            engine.say(text)
            engine.runAndWait()
            if done_callback:
                done_callback()

    def shutdown(self) -> None:
        """Cleanly stop the worker thread."""
        self._queue.put(_STOP)
        self._worker.join(timeout=3)
