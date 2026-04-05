"""
Study loop screen. Orchestrates the full per-card callback chain:
  _start_card -> TTS -> record -> STT -> Gemini -> show result -> rating -> SM-2 -> repeat
"""

import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

import numpy as np

from app.db import repository as repo
from app.models.card import Card
from app.models.sm2 import apply_sm2
from app.services.audio import record_until_silence
from app.gui.app_window import BG, FG, ACCENT, FONT_FAMILY


# Status bar colours
STATUS_COLORS = {
    "idle":      "#6c7086",
    "speaking":  "#89b4fa",
    "listening": "#a6e3a1",
    "checking":  "#f9e2af",
    "correct":   "#a6e3a1",
    "incorrect": "#f38ba8",
    "manual":    "#cba6f7",
}


class StudyScreen(ttk.Frame):
    def __init__(self, app, deck: dict):
        super().__init__(app)
        self.app = app
        self.deck = deck
        self._card: Card | None = None
        self._active = False
        self._stop_event = threading.Event()
        self._audio_queue: queue.Queue = queue.Queue()
        self._transcript_queue: queue.Queue = queue.Queue()
        self._build()
        self.after(300, self._start_card)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        # Top bar: deck name + progress
        top = ttk.Frame(self)
        top.pack(fill="x", padx=20, pady=(16, 0))

        self._back_btn = ttk.Button(top, text="← Decks", command=self._go_back)
        self._back_btn.pack(side="left")

        self._deck_label = ttk.Label(
            top, text=self.deck["name"],
            font=(FONT_FAMILY, 13, "bold"), foreground=ACCENT,
        )
        self._deck_label.pack(side="left", padx=12)

        self._progress_label = ttk.Label(top, text="", foreground="#6c7086",
                                         font=(FONT_FAMILY, 11))
        self._progress_label.pack(side="right")

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=12)

        # Card term display
        card_frame = ttk.Frame(self)
        card_frame.pack(fill="both", expand=True, padx=30)

        self._term_label = tk.Label(
            card_frame,
            text="",
            font=(FONT_FAMILY, 22),
            bg=BG, fg=FG,
            wraplength=540,
            justify="center",
        )
        self._term_label.pack(expand=True)

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=0)

        # Status / feedback area
        feedback = ttk.Frame(self)
        feedback.pack(fill="x", padx=20, pady=10)

        self._status_label = ttk.Label(
            feedback, text="",
            font=(FONT_FAMILY, 11, "italic"), foreground=STATUS_COLORS["idle"],
        )
        self._status_label.pack(anchor="w")

        self._transcript_label = ttk.Label(
            feedback, text="",
            font=(FONT_FAMILY, 11), foreground="#cdd6f4",
        )
        self._transcript_label.pack(anchor="w", pady=(2, 0))

        self._result_label = ttk.Label(
            feedback, text="",
            font=(FONT_FAMILY, 13, "bold"),
        )
        self._result_label.pack(anchor="w", pady=(4, 0))

        self._answer_label = ttk.Label(
            feedback, text="",
            font=(FONT_FAMILY, 11), foreground="#6c7086",
            wraplength=540, justify="left",
        )
        self._answer_label.pack(anchor="w", pady=(2, 0))

        # Rating row (hidden until needed)
        self._rating_frame = ttk.Frame(self)
        ttk.Label(self._rating_frame, text="Rate your recall:",
                  font=(FONT_FAMILY, 11), foreground="#6c7086").pack(side="left", padx=(20, 10))
        self._rating_btns = []
        for i in range(1, 6):
            btn = ttk.Button(
                self._rating_frame,
                text=str(i),
                width=3,
                command=lambda n=i: self._on_rating(n),
            )
            btn.pack(side="left", padx=3)
            self._rating_btns.append(btn)

        # Bottom controls
        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=20, pady=(0, 16))

        self._stop_btn = ttk.Button(
            controls, text="Done Speaking",
            command=self._force_stop_recording,
        )
        self._stop_btn.pack(side="left", padx=(0, 8))
        self._stop_btn.state(["disabled"])

        self._skip_btn = ttk.Button(
            controls, text="Skip Card",
            command=self._skip_card,
        )
        self._skip_btn.pack(side="left")

        # Manual correct/incorrect buttons (shown on Gemini API failure)
        self._manual_frame = ttk.Frame(controls)
        ttk.Label(self._manual_frame, text="Self-grade:",
                  foreground="#6c7086").pack(side="left", padx=(0, 8))
        ttk.Button(self._manual_frame, text="Correct",
                   style="Accent.TButton",
                   command=lambda: self._on_manual_grade(True)).pack(side="left", padx=3)
        ttk.Button(self._manual_frame, text="Incorrect",
                   command=lambda: self._on_manual_grade(False)).pack(side="left", padx=3)

    # ------------------------------------------------------------------
    # Study loop
    # ------------------------------------------------------------------

    def _start_card(self):
        card_row = repo.get_next_due_card(self.deck["id"])
        if card_row is None:
            self._show_all_caught_up()
            return

        self._card = Card.from_row(card_row)
        self._active = True
        self._stop_event.clear()

        # Update progress
        due = repo.get_due_card_count(self.deck["id"])
        total = repo.get_total_card_count(self.deck["id"])
        self._progress_label.config(text=f"{due} due / {total}")

        # Reset feedback area
        self._term_label.config(text=self._card.term)
        self._transcript_label.config(text="")
        self._result_label.config(text="")
        self._answer_label.config(text="")
        self._rating_frame.pack_forget()
        self._manual_frame.pack_forget()
        self._stop_btn.state(["disabled"])

        self._set_status("speaking", "Speaking...")
        self.app.tts.speak(self._card.term, done_callback=lambda: self.after(0, self._on_tts_done))

    def _on_tts_done(self):
        if not self._active:
            return
        self._set_status("listening", "Listening... (speak your answer)")
        self._stop_btn.state(["!disabled"])

        def _record():
            record_until_silence(
                done_callback=lambda audio: self.after(0, lambda: self._on_recording_done(audio)),
                stop_event=self._stop_event,
            )

        threading.Thread(target=_record, daemon=True).start()

    def _on_recording_done(self, audio: np.ndarray):
        if not self._active:
            return
        self._stop_btn.state(["disabled"])
        self._set_status("checking", "Transcribing...")

        def _transcribe():
            text = self.app.stt.transcribe(audio)
            self.after(0, lambda: self._on_transcript(text))

        threading.Thread(target=_transcribe, daemon=True).start()

    def _on_transcript(self, text: str):
        if not self._active:
            return
        self._transcript_label.config(text=f'You said: "{text}"' if text else 'You said: (nothing heard)')
        self._set_status("checking", "Checking answer...")

        card = self._card

        def _check():
            result = self.app.checker.check(card.term, card.definition, text)
            self.after(0, lambda: self._on_check_result(result, text))

        threading.Thread(target=_check, daemon=True).start()

    def _on_check_result(self, result, transcription: str):
        if not self._active:
            return

        if result.needs_manual:
            # API failed — show correct answer and let user self-grade
            self._answer_label.config(text=f"Answer: {self._card.definition}")
            self._set_status("manual", f"Could not check automatically: {result.reason}")
            self._manual_frame.pack(side="left", padx=(16, 0))
            return

        if result.correct:
            self._set_status("correct", f"Correct!  {result.reason}")
            self._result_label.config(text="✓  CORRECT", foreground=STATUS_COLORS["correct"])
            self._show_rating_buttons()
        else:
            self._set_status("incorrect", f"Incorrect.  {result.reason}")
            self._result_label.config(text="✗  INCORRECT", foreground=STATUS_COLORS["incorrect"])
            self._answer_label.config(text=f"Answer: {self._card.definition}")
            # Save as wrong (rating=1) and read the correct answer aloud
            self._save_review(rating=1, was_correct=False, transcription=transcription)
            self.app.tts.speak(
                f"The answer is: {self._card.definition}",
                done_callback=lambda: self.after(0, self._start_card),
            )

    # ------------------------------------------------------------------
    # Rating
    # ------------------------------------------------------------------

    def _show_rating_buttons(self):
        self._rating_frame.pack(fill="x", pady=(8, 0))

    def _on_rating(self, rating: int):
        self._rating_frame.pack_forget()
        transcription = self._transcript_label.cget("text")
        self._save_review(rating=rating, was_correct=True, transcription=transcription)
        self.after(600, self._start_card)

    def _on_manual_grade(self, correct: bool):
        self._manual_frame.pack_forget()
        rating = 3 if correct else 1
        transcription = self._transcript_label.cget("text")
        self._save_review(rating=rating, was_correct=correct, transcription=transcription)
        if not correct:
            self.app.tts.speak(
                f"The answer is: {self._card.definition}",
                done_callback=lambda: self.after(0, self._start_card),
            )
        else:
            self._show_rating_buttons()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_review(self, rating: int, was_correct: bool, transcription: str):
        card = self._card
        sm2 = apply_sm2(card.ease_factor, card.interval, card.repetitions, rating)
        repo.update_card_sm2(card.id, sm2.ease_factor, sm2.interval, sm2.repetitions, sm2.due_date)
        repo.insert_review(
            card_id=card.id,
            rating=rating,
            was_correct=was_correct,
            transcription=transcription,
            new_interval=sm2.interval,
            new_ef=sm2.ease_factor,
        )

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def _force_stop_recording(self):
        self._stop_event.set()
        self._stop_btn.state(["disabled"])

    def _skip_card(self):
        self._active = False
        self._stop_event.set()
        # Schedule the skipped card for tomorrow (rating=1)
        if self._card:
            self._save_review(rating=1, was_correct=False, transcription="(skipped)")
        self.after(200, self._start_card)

    def _go_back(self):
        self._active = False
        self._stop_event.set()
        from app.gui.deck_screen import DeckScreen
        self.app.show_screen(DeckScreen(self.app))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, key: str, text: str):
        self._status_label.config(text=text, foreground=STATUS_COLORS.get(key, FG))

    def _show_all_caught_up(self):
        self._active = False
        self._term_label.config(text="All caught up!")
        next_due = repo.get_next_due_date(self.deck["id"])
        self._set_status("idle", f"Next card due: {next_due or 'N/A'}")
        self._rating_frame.pack_forget()
        self._stop_btn.state(["disabled"])
        stats = repo.get_deck_stats(self.deck["id"])
        total = stats["total_reviews"]
        correct = stats["total_correct"] or 0
        pct = round(100 * correct / total) if total else 0
        self._answer_label.config(
            text=f"Session stats — {total} reviews, {pct}% correct"
        )
