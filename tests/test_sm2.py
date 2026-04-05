"""
Tests for the SM-2 spaced repetition algorithm.
"""

import pytest
from datetime import date, timedelta
from app.models.sm2 import apply_sm2


class TestNewCard:
    """A brand-new card (repetitions=0, interval=1, ef=2.5)."""

    def test_correct_rating5_first_rep_interval_is_1(self):
        r = apply_sm2(2.5, 1, 0, 5)
        assert r.interval == 1

    def test_correct_rating5_increments_repetitions(self):
        r = apply_sm2(2.5, 1, 0, 5)
        assert r.repetitions == 1

    def test_correct_rating5_increases_ease_factor(self):
        r = apply_sm2(2.5, 1, 0, 5)
        assert r.ease_factor > 2.5

    def test_correct_rating4_interval_is_1(self):
        r = apply_sm2(2.5, 1, 0, 4)
        assert r.interval == 1
        assert r.repetitions == 1

    def test_wrong_rating1_stays_interval_1(self):
        r = apply_sm2(2.5, 1, 0, 1)
        assert r.interval == 1
        assert r.repetitions == 0

    def test_wrong_rating2_stays_interval_1(self):
        r = apply_sm2(2.5, 1, 0, 2)
        assert r.interval == 1
        assert r.repetitions == 0

    def test_wrong_answer_does_not_change_ease_factor(self):
        r = apply_sm2(2.5, 1, 0, 1)
        assert r.ease_factor == 2.5

    def test_due_date_is_today_plus_interval(self):
        r = apply_sm2(2.5, 1, 0, 5)
        assert r.due_date == date.today() + timedelta(days=r.interval)


class TestSecondRep:
    """Second correct answer (repetitions=1)."""

    def test_interval_jumps_to_6(self):
        r = apply_sm2(2.5, 1, 1, 5)
        assert r.interval == 6

    def test_repetitions_becomes_2(self):
        r = apply_sm2(2.5, 1, 1, 5)
        assert r.repetitions == 2

    def test_wrong_on_second_rep_resets(self):
        r = apply_sm2(2.5, 1, 1, 1)
        assert r.interval == 1
        assert r.repetitions == 0


class TestEstablishedCard:
    """Card with several correct reps (repetitions >= 2)."""

    def test_interval_grows_by_ease_factor(self):
        r = apply_sm2(2.5, 6, 2, 5)
        assert r.interval == round(6 * 2.5)  # 15

    def test_high_rating_increases_ef(self):
        r = apply_sm2(2.5, 6, 2, 5)
        assert r.ease_factor > 2.5

    def test_low_rating_decreases_ef(self):
        r = apply_sm2(2.5, 6, 2, 3)
        assert r.ease_factor < 2.5

    def test_ef_never_drops_below_floor(self):
        ef = 2.5
        for _ in range(30):
            result = apply_sm2(ef, 6, 2, 3)
            ef = result.ease_factor
        assert ef >= 1.3

    def test_wrong_answer_resets_streak(self):
        r = apply_sm2(2.5, 15, 5, 2)
        assert r.interval == 1
        assert r.repetitions == 0

    def test_wrong_answer_preserves_ef(self):
        r = apply_sm2(2.6, 15, 5, 1)
        assert r.ease_factor == 2.6


class TestRatingBoundary:
    """Rating 3 is the boundary between pass and fail."""

    def test_rating3_is_a_pass(self):
        r = apply_sm2(2.5, 1, 0, 3)
        assert r.repetitions == 1

    def test_rating2_is_a_fail(self):
        r = apply_sm2(2.5, 1, 0, 2)
        assert r.repetitions == 0

    def test_rating3_decreases_ef(self):
        r = apply_sm2(2.5, 1, 1, 3)
        assert r.ease_factor < 2.5

    def test_rating5_gives_highest_ef_gain(self):
        r5 = apply_sm2(2.5, 6, 2, 5)
        r4 = apply_sm2(2.5, 6, 2, 4)
        assert r5.ease_factor > r4.ease_factor

    def test_rating4_gives_higher_ef_than_rating3(self):
        r4 = apply_sm2(2.5, 6, 2, 4)
        r3 = apply_sm2(2.5, 6, 2, 3)
        assert r4.ease_factor > r3.ease_factor


class TestDueDate:
    def test_due_date_correct_on_fail(self):
        r = apply_sm2(2.5, 10, 3, 1)
        assert r.due_date == date.today() + timedelta(days=1)

    def test_due_date_correct_on_pass(self):
        r = apply_sm2(2.5, 6, 2, 5)
        assert r.due_date == date.today() + timedelta(days=r.interval)

    def test_due_date_is_future_on_pass(self):
        r = apply_sm2(2.5, 6, 2, 5)
        assert r.due_date > date.today()
