"""
Root Tkinter window. Owns the Whisper/TTS/Checker service instances and
handles switching between the deck screen and study screen.
"""

import tkinter as tk
from tkinter import ttk

from app.services.stt import STTService
from app.services.tts import TTSService
from app.services.checker import CheckerService
from app.db.repository import init_db


BG = "#1e1e2e"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
FONT_FAMILY = "Helvetica"


class AppWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("voice-flash")
        self.geometry("640x500")
        self.minsize(520, 400)
        self.configure(bg=BG)
        self._apply_theme()

        init_db()

        # Services — created once, shared across screens
        self.tts = TTSService()
        self.checker = CheckerService()
        self.stt = STTService()

        # Show a loading screen while Whisper loads
        self._current_screen = None
        self._show_loading()
        self.after(100, self._load_whisper)

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_theme(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=FG, font=(FONT_FAMILY, 11))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("TButton",
                        background="#313244", foreground=FG,
                        relief="flat", padding=(12, 6))
        style.map("TButton",
                  background=[("active", "#45475a"), ("pressed", "#585b70")])
        style.configure("Accent.TButton",
                        background=ACCENT, foreground="#1e1e2e",
                        font=(FONT_FAMILY, 11, "bold"), padding=(12, 6))
        style.map("Accent.TButton",
                  background=[("active", "#74c7ec"), ("pressed", "#89dceb")])
        style.configure("TListbox", background="#313244", foreground=FG,
                        selectbackground=ACCENT, selectforeground="#1e1e2e")

    # ------------------------------------------------------------------
    # Screen management
    # ------------------------------------------------------------------

    def show_screen(self, screen):
        if self._current_screen is not None:
            self._current_screen.destroy()
        self._current_screen = screen
        screen.pack(fill="both", expand=True)

    def _show_loading(self):
        frame = ttk.Frame(self)
        ttk.Label(frame, text="voice-flash",
                  font=(FONT_FAMILY, 28, "bold"), foreground=ACCENT).pack(pady=(80, 12))
        ttk.Label(frame, text="Loading speech model...",
                  font=(FONT_FAMILY, 12), foreground="#6c7086").pack()
        self._loading_frame = frame
        self.show_screen(frame)

    def _load_whisper(self):
        import threading
        def _load():
            self.stt.load()
            self.after(0, self._on_whisper_loaded)

        threading.Thread(target=_load, daemon=True).start()

    def _on_whisper_loaded(self):
        from app.gui.deck_screen import DeckScreen
        self.show_screen(DeckScreen(self))
