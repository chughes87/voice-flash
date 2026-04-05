"""
Tests for the Quizlet export parser.
"""

import pytest
import tempfile
from pathlib import Path

from app.services.importer import _parse, import_quizlet
from app.db.repository import init_db, get_all_decks, get_next_due_card


BASIC = "apple\tmanzana\nbanana\tplátano\ncherry\tcereza\n"
MESSY = (
    "  dog  \t  perro  \n"   # leading/trailing whitespace
    "\n"                      # blank line
    "cat\tgato\n"
    "\t\n"                    # tab-only line (no valid pair)
    "house\tcasa\n"
)


class TestParse:
    def test_basic_tab_separated(self):
        pairs = _parse(BASIC)
        assert pairs == [("apple", "manzana"), ("banana", "plátano"), ("cherry", "cereza")]

    def test_strips_whitespace(self):
        pairs = _parse(MESSY)
        assert ("dog", "perro") in pairs
        assert ("cat", "gato") in pairs
        assert ("house", "casa") in pairs

    def test_skips_blank_lines(self):
        pairs = _parse(MESSY)
        assert len(pairs) == 3

    def test_skips_lines_without_tab(self):
        text = "no tab here\nanother line\nterm\tdefinition\n"
        pairs = _parse(text)
        assert pairs == [("term", "definition")]

    def test_definition_can_contain_tabs(self):
        # Only split on the FIRST tab — definitions may contain tabs
        text = "term\tdef with\textra tabs\n"
        pairs = _parse(text)
        assert pairs == [("term", "def with\textra tabs")]

    def test_empty_input_returns_empty_list(self):
        assert _parse("") == []

    def test_unicode_content(self):
        text = "你好\thello\nmerci\tthank you\n"
        pairs = _parse(text)
        assert pairs == [("你好", "hello"), ("merci", "thank you")]

    def test_skips_pairs_with_empty_term(self):
        text = "\tdefinition only\n"
        pairs = _parse(text)
        assert pairs == []

    def test_skips_pairs_with_empty_definition(self):
        text = "term\t\n"
        pairs = _parse(text)
        assert pairs == []


class TestImportQuizlet:
    def setup_method(self):
        init_db()

    def _write_tmp(self, content: str, name: str = "spanish_vocab.txt") -> Path:
        tmp = Path(tempfile.mktemp(suffix=f"_{name}"))
        tmp.write_text(content, encoding="utf-8")
        return tmp

    def test_returns_correct_card_count(self):
        tmp = self._write_tmp(BASIC)
        _, count = import_quizlet(tmp)
        tmp.unlink()
        assert count == 3

    def test_returns_valid_deck_id(self):
        tmp = self._write_tmp(BASIC)
        deck_id, _ = import_quizlet(tmp)
        tmp.unlink()
        assert isinstance(deck_id, int)
        assert deck_id > 0

    def test_deck_name_derived_from_filename(self):
        tmp = self._write_tmp(BASIC, "spanish_vocab.txt")
        deck_id, _ = import_quizlet(tmp)
        tmp.unlink()
        decks = get_all_decks()
        deck = next(d for d in decks if d["id"] == deck_id)
        assert "Spanish" in deck["name"] and "Vocab" in deck["name"]

    def test_cards_are_queryable_after_import(self):
        tmp = self._write_tmp(BASIC)
        deck_id, _ = import_quizlet(tmp)
        tmp.unlink()
        card = get_next_due_card(deck_id)
        assert card is not None
        assert card["term"] in ("apple", "banana", "cherry")

    def test_raises_on_file_with_no_valid_pairs(self):
        tmp = self._write_tmp("no tabs here at all\njust plain text\n")
        with pytest.raises(ValueError):
            import_quizlet(tmp)
        tmp.unlink()

    def test_multiple_decks_are_independent(self):
        tmp1 = self._write_tmp("dog\tperro\ncat\tgato\n", "animals.txt")
        tmp2 = self._write_tmp("red\trojo\nblue\tazul\n", "colors.txt")
        id1, count1 = import_quizlet(tmp1)
        id2, count2 = import_quizlet(tmp2)
        tmp1.unlink()
        tmp2.unlink()
        assert id1 != id2
        assert count1 == 2
        assert count2 == 2
        card1 = get_next_due_card(id1)
        card2 = get_next_due_card(id2)
        assert card1["term"] in ("dog", "cat")
        assert card2["term"] in ("red", "blue")
