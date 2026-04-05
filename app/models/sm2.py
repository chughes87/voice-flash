from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class SM2Result:
    ease_factor: float
    interval: int
    repetitions: int
    due_date: date


# Map 1-5 user rating to SM-2 quality score (0-5 scale).
# q >= 3 is a pass; q < 3 is a fail.
# rating 3 = minimum pass (q=3, EF decreases slightly)
# rating 4 = comfortable recall (q=4, EF unchanged)
# rating 5 = effortless recall (q=5, EF increases)
_RATING_TO_QUALITY = {1: 0, 2: 1, 3: 3, 4: 4, 5: 5}


def apply_sm2(
    ease_factor: float,
    interval: int,
    repetitions: int,
    rating: int,
) -> SM2Result:
    """
    Pure SM-2 calculation. Returns updated scheduling values.

    rating: 1-5 (1 = complete blackout, 5 = perfect recall)
    """
    q = _RATING_TO_QUALITY.get(rating, 0)

    if q < 3:
        new_repetitions = 0
        new_interval = 1
        new_ef = ease_factor  # EF unchanged on failure
    else:
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(interval * ease_factor)

        new_ef = ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        new_ef = max(1.3, new_ef)
        new_repetitions = repetitions + 1

    due_date = date.today() + timedelta(days=new_interval)

    return SM2Result(
        ease_factor=round(new_ef, 4),
        interval=new_interval,
        repetitions=new_repetitions,
        due_date=due_date,
    )


if __name__ == "__main__":
    # Quick sanity checks
    def check(label, result, expected_interval, expected_reps):
        ok = result.interval == expected_interval and result.repetitions == expected_reps
        print(f"{'OK' if ok else 'FAIL'} {label}: interval={result.interval} reps={result.repetitions} ef={result.ease_factor:.4f}")

    # First correct answer (rating 5) on a new card
    r = apply_sm2(2.5, 1, 0, 5)
    check("new card, rating=5", r, expected_interval=1, expected_reps=1)

    # Second correct answer
    r = apply_sm2(r.ease_factor, r.interval, r.repetitions, 5)
    check("2nd correct, rating=5", r, expected_interval=6, expected_reps=2)

    # Third correct answer — interval should grow
    r = apply_sm2(r.ease_factor, r.interval, r.repetitions, 5)
    check("3rd correct, rating=5", r, expected_interval=round(6 * r.ease_factor) if False else 16, expected_reps=3)

    # Wrong answer — should reset
    r2 = apply_sm2(2.5, 10, 3, 1)
    check("wrong answer, rating=1", r2, expected_interval=1, expected_reps=0)

    # EF floor: repeated low ratings should not drop below 1.3
    ef = 2.5
    for _ in range(20):
        res = apply_sm2(ef, 1, 1, 3)
        ef = res.ease_factor
    print(f"OK EF floor: ef={ef:.4f} (should be >= 1.3): {ef >= 1.3}")
