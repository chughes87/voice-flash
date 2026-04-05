"""
Tests for the Gemini answer checker response parser.
No API calls are made — all tests exercise _parse_response() directly.
"""

import pytest
from app.services.checker import _parse_response, CheckResult


class TestParseCorrect:
    def test_correct_true(self):
        r = _parse_response('{"correct": true, "reason": "Exact match."}')
        assert r.correct is True
        assert r.reason == "Exact match."
        assert r.needs_manual is False

    def test_correct_false(self):
        r = _parse_response('{"correct": false, "reason": "Wrong word."}')
        assert r.correct is False
        assert r.reason == "Wrong word."
        assert r.needs_manual is False

    def test_missing_reason_field(self):
        r = _parse_response('{"correct": true}')
        assert r.correct is True
        assert r.reason == ""

    def test_extra_fields_ignored(self):
        r = _parse_response('{"correct": true, "reason": "Good.", "confidence": 0.99}')
        assert r.correct is True


class TestFencedCodeBlocks:
    def test_strips_json_fence(self):
        r = _parse_response('```json\n{"correct": true, "reason": "OK."}\n```')
        assert r.correct is True

    def test_strips_plain_fence(self):
        r = _parse_response('```\n{"correct": false, "reason": "Nope."}\n```')
        assert r.correct is False

    def test_strips_fence_no_trailing_newline(self):
        r = _parse_response('```json\n{"correct": true, "reason": "Yes."}```')
        assert r.correct is True


class TestFallbackParsing:
    def test_garbage_input_returns_needs_manual(self):
        r = _parse_response("I'm not sure about this one.")
        assert r.needs_manual is True

    def test_empty_string_returns_needs_manual(self):
        r = _parse_response("")
        assert r.needs_manual is True

    def test_partial_json_returns_needs_manual(self):
        r = _parse_response('{"correct": tru')
        assert r.needs_manual is True

    def test_raw_text_with_true_detected(self):
        r = _parse_response('The answer is "correct": true here somewhere.')
        assert r.correct is True
        assert r.needs_manual is False

    def test_raw_text_with_false_detected(self):
        r = _parse_response('Result: "correct": false — the student was wrong.')
        assert r.correct is False
        assert r.needs_manual is False


class TestCheckResultDataclass:
    def test_default_needs_manual_is_false(self):
        r = CheckResult(correct=True, reason="OK")
        assert r.needs_manual is False

    def test_needs_manual_can_be_set(self):
        r = CheckResult(correct=False, reason="API down", needs_manual=True)
        assert r.needs_manual is True
