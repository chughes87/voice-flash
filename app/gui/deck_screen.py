"""
Deck selection and import screen.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from app.db.repository import get_all_decks, delete_deck, get_due_card_count, get_total_card_count
from app.services.importer import import_quizlet
from app.gui.app_window import BG, FG, ACCENT, FONT_FAMILY


class DeckScreen(ttk.Frame):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self._build()
        self._refresh()

    def _build(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", padx=24, pady=(24, 0))
        ttk.Label(header, text="voice-flash",
                  font=(FONT_FAMILY, 20, "bold"), foreground=ACCENT).pack(side="left")
        ttk.Button(header, text="+ Import Deck",
                   style="Accent.TButton",
                   command=self._import_deck).pack(side="right")

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=24, pady=16)

        # Deck list
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=24)

        ttk.Label(list_frame, text="YOUR DECKS",
                  font=(FONT_FAMILY, 9), foreground="#6c7086").pack(anchor="w", pady=(0, 8))

        self._listbox_frame = ttk.Frame(list_frame)
        self._listbox_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self._listbox_frame, orient="vertical")
        self._listbox = tk.Listbox(
            self._listbox_frame,
            yscrollcommand=scrollbar.set,
            bg="#313244", fg=FG,
            selectbackground=ACCENT, selectforeground="#1e1e2e",
            font=(FONT_FAMILY, 12),
            relief="flat", bd=0,
            activestyle="none",
            highlightthickness=0,
        )
        scrollbar.config(command=self._listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self._listbox.pack(side="left", fill="both", expand=True)
        self._listbox.bind("<Double-Button-1>", lambda _: self._start_study())

        self._empty_label = ttk.Label(
            self._listbox_frame,
            text="No decks yet.\nImport a Quizlet export to get started.",
            font=(FONT_FAMILY, 12), foreground="#6c7086",
            justify="center",
        )

        # Bottom buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=24, pady=16)

        self._study_btn = ttk.Button(
            btn_frame, text="Study",
            style="Accent.TButton",
            command=self._start_study,
        )
        self._study_btn.pack(side="left", padx=(0, 8))

        ttk.Button(btn_frame, text="Delete Deck",
                   command=self._delete_deck).pack(side="left")

        self._status_label = ttk.Label(btn_frame, text="",
                                       foreground="#6c7086",
                                       font=(FONT_FAMILY, 10))
        self._status_label.pack(side="right")

        self._decks: list[dict] = []

    def _refresh(self):
        self._decks = get_all_decks()
        self._listbox.delete(0, "end")

        if not self._decks:
            self._listbox.pack_forget()
            self._empty_label.pack(expand=True)
            self._study_btn.state(["disabled"])
            return

        self._empty_label.pack_forget()
        self._listbox.pack(side="left", fill="both", expand=True)
        self._study_btn.state(["!disabled"])

        for deck in self._decks:
            due = get_due_card_count(deck["id"])
            total = get_total_card_count(deck["id"])
            label = f"  {deck['name']}   ({due} due / {total} total)"
            self._listbox.insert("end", label)

        if self._decks:
            self._listbox.selection_set(0)

    def _selected_deck(self) -> dict | None:
        sel = self._listbox.curselection()
        if not sel:
            return None
        return self._decks[sel[0]]

    def _import_deck(self):
        path = filedialog.askopenfilename(
            title="Select Quizlet Export",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            deck_id, count = import_quizlet(path)
            self._refresh()
            self._status_label.config(text=f"Imported {count} cards.")
        except Exception as e:
            messagebox.showerror("Import failed", str(e))

    def _delete_deck(self):
        deck = self._selected_deck()
        if not deck:
            return
        if not messagebox.askyesno("Delete deck",
                                   f"Delete \"{deck['name']}\"? This cannot be undone."):
            return
        delete_deck(deck["id"])
        self._refresh()
        self._status_label.config(text="Deck deleted.")

    def _start_study(self):
        deck = self._selected_deck()
        if not deck:
            return
        due = get_due_card_count(deck["id"])
        if due == 0:
            from app.db.repository import get_next_due_date
            next_due = get_next_due_date(deck["id"])
            messagebox.showinfo(
                "All caught up!",
                f"No cards due in \"{deck['name']}\".\n\nNext card due: {next_due or 'N/A'}",
            )
            return
        from app.gui.study_screen import StudyScreen
        self.app.show_screen(StudyScreen(self.app, deck))
