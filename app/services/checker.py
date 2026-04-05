"""
Answer correctness checker using Google Gemini 2.0 Flash.

Falls back to a manual self-grade result if the API is unavailable
or returns unparseable output.
"""

import json
import re
from dataclasses import dataclass

import google.genai as genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL


@dataclass
class CheckResult:
    correct: bool
    reason: str
    needs_manual: bool = False  # True when API failed — user must self-grade


_SYSTEM_PROMPT = (
    "You are a flashcard answer checker. "
    "Be lenient about synonyms, minor transcription errors, articles (a/an/the), "
    "and partial answers that capture the core concept. "
    "Be strict about factually wrong or completely unrelated answers. "
    'Respond ONLY with valid JSON: {"correct": true/false, "reason": "one sentence"}'
)

_USER_TEMPLATE = (
    "Term: {term}\n"
    "Expected answer: {definition}\n"
    "Student said: {transcription}\n"
    "Is the student correct?"
)


class CheckerService:
    def __init__(self) -> None:
        if not GEMINI_API_KEY:
            self._client = None
        else:
            self._client = genai.Client(api_key=GEMINI_API_KEY)

    def check(self, term: str, definition: str, transcription: str) -> CheckResult:
        if not self._client:
            return CheckResult(correct=False, reason="No API key configured.", needs_manual=True)

        prompt = _USER_TEMPLATE.format(
            term=term,
            definition=definition,
            transcription=transcription or "(no answer)",
        )

        try:
            response = self._client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    temperature=0.0,
                ),
            )
            raw = response.text or ""
            return _parse_response(raw)
        except Exception as e:
            return CheckResult(
                correct=False,
                reason=f"API error: {e}",
                needs_manual=True,
            )


def _parse_response(text: str) -> CheckResult:
    # Strip markdown code fences if Gemini wraps its response
    clean = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        data = json.loads(clean)
        return CheckResult(
            correct=bool(data["correct"]),
            reason=data.get("reason", ""),
        )
    except (json.JSONDecodeError, KeyError):
        # Best-effort: look for true/false in raw text
        lower = text.lower()
        if '"correct": true' in lower or "'correct': true" in lower:
            return CheckResult(correct=True, reason="(parsed from raw response)")
        if '"correct": false' in lower or "'correct': false" in lower:
            return CheckResult(correct=False, reason="(parsed from raw response)")
        return CheckResult(correct=False, reason="Could not parse response.", needs_manual=True)
