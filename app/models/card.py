from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Card:
    id: Optional[int]
    deck_id: int
    term: str
    definition: str
    ease_factor: float = 2.5
    interval: int = 1
    repetitions: int = 0
    due_date: date = field(default_factory=date.today)

    @classmethod
    def from_row(cls, row: dict) -> "Card":
        return cls(
            id=row["id"],
            deck_id=row["deck_id"],
            term=row["term"],
            definition=row["definition"],
            ease_factor=row["ease_factor"],
            interval=row["interval"],
            repetitions=row["repetitions"],
            due_date=date.fromisoformat(row["due_date"]),
        )


@dataclass
class Deck:
    id: Optional[int]
    name: str
    source_file: str
    created_at: str
    card_count: int = 0

    @classmethod
    def from_row(cls, row: dict) -> "Deck":
        return cls(
            id=row["id"],
            name=row["name"],
            source_file=row["source_file"],
            created_at=row["created_at"],
            card_count=row.get("card_count", 0),
        )
