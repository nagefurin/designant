"""Pure ordering helpers for Designant."""

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
    """True only for an ordinary, actively queued new card."""
    try:
        card_type = int(getattr(card, "type"))
        queue = int(getattr(card, "queue"))
        original_deck_id = int(getattr(card, "odid", 0) or 0)
    except (AttributeError, TypeError, ValueError):
        return False
    return card_type == 0 and queue == 0 and original_deck_id == 0


def _frequency_order(
    card_values: list[Tuple[int, object]],
    reverse: bool,
) -> list[int]:
    scored: list[Tuple[int, float]] = []
    unscored: list[int] = []

    for card_id, raw_value in card_values:
        value = parse_frequency(raw_value)
        if value is None:
            unscored.append(int(card_id))
        else:
            scored.append((int(card_id), value))

    # Stable deterministic ties: creation-time/card ID ascending.
    scored.sort(key=lambda item: item[0])
    scored.sort(key=lambda item: item[1], reverse=reverse)
    return [card_id for card_id, _ in scored] + sorted(unscored)


def build_order(
    card_values: Iterable[Tuple[int, object]],
    frequency_count: int = 20,
    created_time_count: int = 5,
    frequency_reverse: bool = False,
    created_reverse: bool = False,
    enable_freq_sort: bool = True,
    enable_time_sort: bool = True,
) -> list[int]:
    """Build Designant's new-card order.

    When both sort modes are enabled:
      1. First frequency_count cards by FreqSort.
      2. Next created_time_count cards by exact card-creation timestamp.
      3. All remaining cards by FreqSort again.

    When only one mode is enabled, the complete queue is sorted by that mode.
    When both are disabled, the input (current Anki due) order is preserved.

    Anki card IDs are millisecond timestamps, so sorting by ID uses the full
    Created Time (Card), including time-of-day for cards created on one date.
    """
    values = [(int(card_id), raw) for card_id, raw in card_values]
    original_ids = [card_id for card_id, _ in values]

    if enable_freq_sort and not enable_time_sort:
        return _frequency_order(values, frequency_reverse)

    if enable_time_sort and not enable_freq_sort:
        return sorted(original_ids, reverse=created_reverse)

    if not enable_freq_sort and not enable_time_sort:
        return original_ids

    # Both modes enabled: use the three-stage split.
    scored: list[Tuple[int, float]] = []
    unscored: list[int] = []
    for card_id, raw_value in values:
        value = parse_frequency(raw_value)
        if value is None:
            unscored.append(card_id)
        else:
            scored.append((card_id, value))

    # Lower numerical ranks first by default; card ID breaks ties.
    scored.sort(key=lambda item: item[0])
    scored.sort(key=lambda item: item[1], reverse=frequency_reverse)

    frequency_count = max(0, int(frequency_count))
    created_time_count = max(0, int(created_time_count))

    first_frequency = scored[:frequency_count]
    remaining_scored = scored[frequency_count:]

    # Date/time group is picked only from cards after the first frequency block.
    remaining_ids = {card_id for card_id, _ in remaining_scored}
    remaining_ids.update(unscored)
    date_candidates = sorted(remaining_ids, reverse=created_reverse)
    date_group = date_candidates[:created_time_count]
    date_group_set = set(date_group)

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


def reposition_preserving_user_defaults(
    col: object,
    card_ids: list[int],
    random_config_key: object,
    shift_config_key: object,
):
    """Reposition supplied cards without changing Anki's saved defaults."""
    scheduler = getattr(col, "sched")
    defaults = scheduler.reposition_defaults()
    try:
        return scheduler.reposition_new_cards(
            card_ids=card_ids,
            starting_from=0,
            step_size=1,
            randomize=False,
            shift_existing=False,
        )
    finally:
        col.set_config_bool(random_config_key, bool(defaults.random))
        col.set_config_bool(shift_config_key, bool(defaults.shift))
