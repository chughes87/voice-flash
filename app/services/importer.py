from pathlib import Path

from app.db import repository as repo


def import_quizlet(file_path: str | Path) -> tuple[int, int]:
    """
    Parse a Quizlet tab-separated export and insert it as a new deck.

    Quizlet export format: one card per line, term and definition
    separated by a tab character.

    Returns (deck_id, card_count).
    """
    path = Path(file_path)
    text = path.read_text(encoding="utf-8", errors="replace")

    pairs = _parse(text)
    if not pairs:
        raise ValueError(f"No valid term/definition pairs found in {path.name}")

    deck_name = path.stem.replace("_", " ").replace("-", " ").title()
    deck_id = repo.insert_deck(name=deck_name, source_file=path.name)
    repo.insert_cards(deck_id, pairs)

    return deck_id, len(pairs)


def _parse(text: str) -> list[tuple[str, str]]:
    pairs = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            term, defn = parts[0].strip(), parts[1].strip()
            if term and defn:
                pairs.append((term, defn))
    return pairs


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 -m app.services.importer <quizlet_export.txt>")
        sys.exit(1)

    from app.db.repository import init_db
    init_db()

    deck_id, count = import_quizlet(sys.argv[1])
    print(f"Imported {count} cards into deck id={deck_id}")

    from app.db import repository as repo
    card = repo.get_next_due_card(deck_id)
    print(f"First due card: {card['term']} -> {card['definition']}")
