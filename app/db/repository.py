import sqlite3
from datetime import date
from typing import Optional
from contextlib import contextmanager

from app.config import DB_PATH
from app.db.schema import SCHEMA_SQL


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA_SQL)


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Deck operations
# ---------------------------------------------------------------------------

def insert_deck(name: str, source_file: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO decks (name, source_file) VALUES (?, ?)",
            (name, source_file),
        )
        return cur.lastrowid


def get_all_decks() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("""
            SELECT d.id, d.name, d.source_file, d.created_at,
                   COUNT(c.id) AS card_count
            FROM decks d
            LEFT JOIN cards c ON c.deck_id = d.id
            GROUP BY d.id
            ORDER BY d.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]


def delete_deck(deck_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM decks WHERE id = ?", (deck_id,))


# ---------------------------------------------------------------------------
# Card operations
# ---------------------------------------------------------------------------

def insert_cards(deck_id: int, pairs: list[tuple[str, str]]) -> None:
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO cards (deck_id, term, definition) VALUES (?, ?, ?)",
            [(deck_id, term, defn) for term, defn in pairs],
        )


def get_next_due_card(deck_id: int) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute("""
            SELECT * FROM cards
            WHERE deck_id = ?
              AND due_date <= date('now')
            ORDER BY due_date ASC, id ASC
            LIMIT 1
        """, (deck_id,)).fetchone()
        return dict(row) if row else None


def get_next_due_date(deck_id: int) -> Optional[str]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT MIN(due_date) AS next FROM cards WHERE deck_id = ?",
            (deck_id,),
        ).fetchone()
        return row["next"] if row else None


def get_due_card_count(deck_id: int) -> int:
    with _connect() as conn:
        row = conn.execute("""
            SELECT COUNT(*) AS n FROM cards
            WHERE deck_id = ? AND due_date <= date('now')
        """, (deck_id,)).fetchone()
        return row["n"]


def get_total_card_count(deck_id: int) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM cards WHERE deck_id = ?",
            (deck_id,),
        ).fetchone()
        return row["n"]


def update_card_sm2(
    card_id: int,
    ease_factor: float,
    interval: int,
    repetitions: int,
    due_date: date,
) -> None:
    with _connect() as conn:
        conn.execute("""
            UPDATE cards
            SET ease_factor = ?,
                interval     = ?,
                repetitions  = ?,
                due_date     = ?
            WHERE id = ?
        """, (ease_factor, interval, repetitions, due_date.isoformat(), card_id))


# ---------------------------------------------------------------------------
# Review operations
# ---------------------------------------------------------------------------

def insert_review(
    card_id: int,
    rating: int,
    was_correct: bool,
    transcription: Optional[str],
    new_interval: int,
    new_ef: float,
) -> None:
    with _connect() as conn:
        conn.execute("""
            INSERT INTO reviews
                (card_id, rating, was_correct, transcription, new_interval, new_ef)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (card_id, rating, int(was_correct), transcription, new_interval, new_ef))


def get_deck_stats(deck_id: int) -> dict:
    with _connect() as conn:
        row = conn.execute("""
            SELECT
                COUNT(r.id)                          AS total_reviews,
                SUM(r.was_correct)                   AS total_correct,
                COUNT(DISTINCT r.card_id)            AS cards_reviewed
            FROM reviews r
            JOIN cards c ON c.id = r.card_id
            WHERE c.deck_id = ?
        """, (deck_id,)).fetchone()
        return dict(row) if row else {"total_reviews": 0, "total_correct": 0, "cards_reviewed": 0}
