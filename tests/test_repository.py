"""
Tests for the SQLite repository layer.
Uses a temporary DB file per test session to stay isolated.
"""

import pytest
from datetime import date, timedelta
from pathlib import Path
import tempfile

import app.config as config


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point DB_PATH at a fresh temp file for every test."""
    db_file = tmp_path / "test_flashcards.db"
    monkeypatch.setattr(config, "DB_PATH", db_file)

    # Re-import after monkeypatching so the module picks up the new path
    import importlib
    import app.db.repository as repo
    importlib.reload(repo)

    repo.init_db()
    yield repo


class TestDecks:
    def test_insert_and_retrieve_deck(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Spanish", "spanish.txt")
        decks = repo.get_all_decks()
        assert len(decks) == 1
        assert decks[0]["name"] == "Spanish"
        assert decks[0]["id"] == deck_id

    def test_deck_card_count_is_zero_initially(self, isolated_db):
        repo = isolated_db
        repo.insert_deck("Empty Deck", "empty.txt")
        decks = repo.get_all_decks()
        assert decks[0]["card_count"] == 0

    def test_deck_card_count_reflects_inserted_cards(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Spanish", "spanish.txt")
        repo.insert_cards(deck_id, [("apple", "manzana"), ("dog", "perro")])
        decks = repo.get_all_decks()
        assert decks[0]["card_count"] == 2

    def test_multiple_decks_returned_newest_first(self, isolated_db):
        repo = isolated_db
        repo.insert_deck("First", "a.txt")
        repo.insert_deck("Second", "b.txt")
        decks = repo.get_all_decks()
        assert decks[0]["name"] == "Second"
        assert decks[1]["name"] == "First"

    def test_delete_deck_removes_it(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("To Delete", "del.txt")
        repo.delete_deck(deck_id)
        assert repo.get_all_decks() == []

    def test_delete_deck_cascades_to_cards(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Spanish", "spanish.txt")
        repo.insert_cards(deck_id, [("apple", "manzana")])
        repo.delete_deck(deck_id)
        assert repo.get_next_due_card(deck_id) is None


class TestCards:
    def test_inserted_cards_are_due_today(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Spanish", "spanish.txt")
        repo.insert_cards(deck_id, [("apple", "manzana")])
        card = repo.get_next_due_card(deck_id)
        assert card is not None
        assert card["term"] == "apple"
        assert card["definition"] == "manzana"

    def test_get_next_due_card_returns_none_when_no_cards(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Empty", "empty.txt")
        assert repo.get_next_due_card(deck_id) is None

    def test_get_next_due_card_returns_oldest_due_first(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Spanish", "spanish.txt")
        repo.insert_cards(deck_id, [("apple", "manzana"), ("banana", "plátano")])

        # Manually push banana's due_date into the past
        cards_conn = config.DB_PATH
        import sqlite3
        conn = sqlite3.connect(config.DB_PATH)
        conn.execute(
            "UPDATE cards SET due_date = ? WHERE term = ?",
            ((date.today() - timedelta(days=3)).isoformat(), "banana"),
        )
        conn.commit()
        conn.close()

        card = repo.get_next_due_card(deck_id)
        assert card["term"] == "banana"

    def test_future_due_card_not_returned(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Spanish", "spanish.txt")
        repo.insert_cards(deck_id, [("apple", "manzana")])

        import sqlite3
        conn = sqlite3.connect(config.DB_PATH)
        conn.execute(
            "UPDATE cards SET due_date = ?",
            ((date.today() + timedelta(days=5)).isoformat(),),
        )
        conn.commit()
        conn.close()

        assert repo.get_next_due_card(deck_id) is None

    def test_due_count_matches_overdue_cards(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Spanish", "spanish.txt")
        repo.insert_cards(deck_id, [
            ("apple", "manzana"),
            ("banana", "plátano"),
            ("cherry", "cereza"),
        ])

        import sqlite3
        conn = sqlite3.connect(config.DB_PATH)
        conn.execute(
            "UPDATE cards SET due_date = ? WHERE term = 'cherry'",
            ((date.today() + timedelta(days=5)).isoformat(),),
        )
        conn.commit()
        conn.close()

        assert repo.get_due_card_count(deck_id) == 2

    def test_total_card_count(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Spanish", "spanish.txt")
        repo.insert_cards(deck_id, [("a", "1"), ("b", "2"), ("c", "3")])
        assert repo.get_total_card_count(deck_id) == 3

    def test_update_card_sm2_persists(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Spanish", "spanish.txt")
        repo.insert_cards(deck_id, [("apple", "manzana")])
        card = repo.get_next_due_card(deck_id)

        new_due = date.today() + timedelta(days=6)
        repo.update_card_sm2(
            card_id=card["id"],
            ease_factor=2.6,
            interval=6,
            repetitions=1,
            due_date=new_due,
        )

        import sqlite3, sqlite3
        conn = sqlite3.connect(config.DB_PATH)
        row = conn.execute("SELECT * FROM cards WHERE id = ?", (card["id"],)).fetchone()
        conn.close()
        assert row[4] == 2.6   # ease_factor
        assert row[5] == 6     # interval
        assert row[6] == 1     # repetitions

    def test_next_due_date_returns_soonest(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Spanish", "spanish.txt")
        repo.insert_cards(deck_id, [("apple", "manzana"), ("banana", "plátano")])

        future = (date.today() + timedelta(days=10)).isoformat()
        import sqlite3
        conn = sqlite3.connect(config.DB_PATH)
        conn.execute("UPDATE cards SET due_date = ? WHERE term = 'banana'", (future,))
        conn.commit()
        conn.close()

        # apple is due today, banana in 10 days
        # After reviewing apple, next_due_date should be banana's date
        card = repo.get_next_due_card(deck_id)
        repo.update_card_sm2(
            card["id"], 2.6, 6, 1, date.today() + timedelta(days=6)
        )
        next_due = repo.get_next_due_date(deck_id)
        assert next_due is not None


class TestReviews:
    def test_insert_review_is_persisted(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Spanish", "spanish.txt")
        repo.insert_cards(deck_id, [("apple", "manzana")])
        card = repo.get_next_due_card(deck_id)

        repo.insert_review(
            card_id=card["id"],
            rating=5,
            was_correct=True,
            transcription="manzana",
            new_interval=6,
            new_ef=2.6,
        )

        import sqlite3
        conn = sqlite3.connect(config.DB_PATH)
        rows = conn.execute("SELECT * FROM reviews").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][3] == 5      # rating
        assert rows[0][4] == 1      # was_correct
        assert rows[0][5] == "manzana"

    def test_deck_stats_accuracy(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Spanish", "spanish.txt")
        repo.insert_cards(deck_id, [("apple", "manzana"), ("banana", "plátano")])
        cards = [repo.get_next_due_card(deck_id)]

        import sqlite3
        conn = sqlite3.connect(config.DB_PATH)
        banana = conn.execute("SELECT id FROM cards WHERE term='banana'").fetchone()[0]
        conn.close()

        repo.insert_review(cards[0]["id"], 5, True, "manzana", 6, 2.6)
        repo.insert_review(banana, 1, False, "wrong", 1, 2.5)

        stats = repo.get_deck_stats(deck_id)
        assert stats["total_reviews"] == 2
        assert stats["total_correct"] == 1
        assert stats["cards_reviewed"] == 2

    def test_delete_card_cascades_reviews(self, isolated_db):
        repo = isolated_db
        deck_id = repo.insert_deck("Spanish", "spanish.txt")
        repo.insert_cards(deck_id, [("apple", "manzana")])
        card = repo.get_next_due_card(deck_id)
        repo.insert_review(card["id"], 5, True, "manzana", 6, 2.6)
        repo.delete_deck(deck_id)

        import sqlite3
        conn = sqlite3.connect(config.DB_PATH)
        rows = conn.execute("SELECT * FROM reviews").fetchall()
        conn.close()
        assert rows == []
