"""
Thread-safe text-to-speech wrapper around pyttsx3.

pyttsx3's runAndWait() blocks, so all speech must run in a worker thread.
done_event is set when speech finishes so callers can chain the next step.
"""

import threading
import pyttsx3


class TTSService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._engine: pyttsx3.Engine | None = None

    def _get_engine(self) -> pyttsx3.Engine:
        # pyttsx3 engines are not thread-safe to share; create per-thread
        # but cache within a thread by storing on the thread-local object.
        if not hasattr(_thread_local, "engine"):
            engine = pyttsx3.init()
            engine.setProperty("rate", 165)
            _thread_local.engine = engine
        return _thread_local.engine

    def speak(self, text: str, done_callback: callable = None) -> threading.Thread:
        """
        Speak text asynchronously in a worker thread.
        Calls done_callback() (no args) on the worker thread when finished.
        Returns the Thread so callers can join if needed.
        """
        def _run():
            engine = self._get_engine()
            engine.say(text)
            engine.runAndWait()
            if done_callback:
                done_callback()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t


_thread_local = threading.local()
