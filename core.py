"""Pure ordering helpers for Frequency + Date Reorder."""

from __future__ import annotations

import math
from typing import Iterable, Optional, Tuple


def parse_frequency(value: object) -> Optional[float]:
    """Return a finite numeric frequency value, or None for blank/invalid data."""
    if value is None:
        return None
    raw = str(value).strip().replace(",", "")
    if not raw:
        return None
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def is_active_normal_new_card(card: object) -> bool:
    """True only for an ordinary, actively queued new card.

    Anki's scheduler repositions every card with CardType.New, including some
    suspended/buried cards. It can also update original_due for filtered cards.
    Requiring both CardType.New and CardQueue.New, and excluding cards with an
    original deck ID, keeps those cards outside the reorder operation.
    """
    try:
        card_type = int(getattr(card, "type"))
        queue = int(getattr(card, "queue"))
        original_deck_id = int(getattr(card, "odid", 0) or 0)
    except (AttributeError, TypeError, ValueError):
        return False
    return card_type == 0 and queue == 0 and original_deck_id == 0


def build_order(
    card_values: Iterable[Tuple[int, object]],
    frequency_count: int = 20,
    date_count: int = 5,
    frequency_reverse: bool = False,
    created_reverse: bool = False,
) -> list[int]:
    """Build the requested three-part new-card order.

    1. First frequency_count cards by FreqSort.
    2. Next date_count cards by creation time, selected from the remainder.
    3. All remaining cards by FreqSort again.

    Each input item is (card_id, frequency_field_value). Anki card IDs are
    millisecond timestamps, so ascending IDs put older-created cards first.

    Cards with missing/non-numeric FreqSort values cannot enter either
    frequency-ranked section. They remain eligible for the date section and,
    if not selected there, trail the final frequency-ranked section.
    """
    scored: list[Tuple[int, float]] = []
    unscored: list[int] = []

    for card_id, raw_value in card_values:
        value = parse_frequency(raw_value)
        if value is None:
            unscored.append(int(card_id))
        else:
            scored.append((int(card_id), value))

    # Lower numerical ranks come first by default. Card ID breaks ties without
    # being reversed when frequency_reverse=True.
    scored.sort(key=lambda item: item[0])
    scored.sort(key=lambda item: item[1], reverse=frequency_reverse)

    frequency_count = max(0, int(frequency_count))
    date_count = max(0, int(date_count))

    first_frequency = scored[:frequency_count]
    remaining_scored = scored[frequency_count:]

    # The date group is selected only from the remainder after the first
    # frequency group. Blank frequency values are eligible for this group.
    remaining_ids = {card_id for card_id, _ in remaining_scored}
    remaining_ids.update(unscored)
    date_candidates = sorted(remaining_ids, reverse=created_reverse)
    date_group = date_candidates[:date_count]
    date_group_set = set(date_group)

    # After the date group, return to frequency ordering for all remaining
    # cards. Missing frequency values have no comparable rank, so they trail.
    final_scored = [
        (card_id, value)
        for card_id, value in remaining_scored
        if card_id not in date_group_set
    ]
    final_unscored = [card_id for card_id in unscored if card_id not in date_group_set]
    final_unscored.sort(reverse=created_reverse)

    return (
        [card_id for card_id, _ in first_frequency]
        + date_group
        + [card_id for card_id, _ in final_scored]
        + final_unscored
    )
