SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS decks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    source_file TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cards (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id      INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    term         TEXT NOT NULL,
    definition   TEXT NOT NULL,
    ease_factor  REAL    NOT NULL DEFAULT 2.5,
    interval     INTEGER NOT NULL DEFAULT 1,
    repetitions  INTEGER NOT NULL DEFAULT 0,
    due_date     TEXT    NOT NULL DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS reviews (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id       INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    reviewed_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    rating        INTEGER NOT NULL,
    was_correct   INTEGER NOT NULL,
    transcription TEXT,
    new_interval  INTEGER NOT NULL,
    new_ef        REAL    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cards_deck_due ON cards(deck_id, due_date);
"""
