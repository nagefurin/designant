"""Frequency + Date Reorder for Anki.

The normal new-card queue is reordered as:
- first N by a numeric note field (FreqSort by default),
- next M by card creation time (oldest first),
- all remaining cards by the numeric note field again.

Only active, non-filtered new-queue cards are passed to Anki's scheduler.
"""

from __future__ import annotations

from typing import Any

from anki import hooks as backend_hooks
from anki.collection import OpChangesWithCount
from aqt import gui_hooks, mw
from aqt.operations import CollectionOp
from aqt.qt import QAction, QTimer
from aqt.utils import qconnect, tooltip

from .core import build_order, is_active_normal_new_card


_DEFAULT_CONFIG: dict[str, Any] = {
    "search_to_sort": "is:new",
    "frequency_field": "FreqSort",
    "frequency_count": 20,
    "date_count": 5,
    "frequency_reverse": False,
    "created_reverse": False,
    "reorder_on_open": True,
    "reorder_on_add": True,
    "reorder_on_sync": True,
    "debounce_ms": 700,
    "show_tooltip": True,
}

_reorder_running = False
_reorder_again = False
_profile_closing = False


def _config() -> dict[str, Any]:
    """Read and normalize add-on configuration on the GUI thread."""
    raw = mw.addonManager.getConfig(__name__) or {}
    config = dict(_DEFAULT_CONFIG)
    config.update(raw)

    config["search_to_sort"] = str(config.get("search_to_sort", "is:new")).strip() or "is:new"
    config["frequency_field"] = str(config.get("frequency_field", "FreqSort")).strip() or "FreqSort"
    for key, default in (("frequency_count", 20), ("date_count", 5), ("debounce_ms", 700)):
        try:
            config[key] = max(0, int(config.get(key, default)))
        except (TypeError, ValueError):
            config[key] = default

    for key in (
        "frequency_reverse",
        "created_reverse",
        "reorder_on_open",
        "reorder_on_add",
        "reorder_on_sync",
        "show_tooltip",
    ):
        config[key] = bool(config.get(key, _DEFAULT_CONFIG[key]))

    return config


def reorder_collection(col: Any, config: dict[str, Any]) -> OpChangesWithCount:
    """Reorder only active normal new cards matching the configured search."""
    found_ids = list(col.find_cards(config["search_to_sort"], order="c.due asc, c.id asc"))
    if not found_ids:
        return OpChangesWithCount(count=0)

    schedulable_ids: list[int] = []
    card_values: list[tuple[int, object]] = []
    note_cache: dict[int, Any] = {}

    for card_id in found_ids:
        card = col.get_card(card_id)
        if not is_active_normal_new_card(card):
            continue

        card_id = int(card.id)
        schedulable_ids.append(card_id)

        # Several cards can be generated from one note. Read the note once.
        note_id = int(card.nid)
        note = note_cache.get(note_id)
        if note is None:
            note = card.note()
            note_cache[note_id] = note

        try:
            frequency_value = note[config["frequency_field"]]
        except (KeyError, TypeError, IndexError):
            frequency_value = ""
        card_values.append((card_id, frequency_value))

    if not schedulable_ids:
        return OpChangesWithCount(count=0)

    ordered_ids = build_order(
        card_values,
        frequency_count=config["frequency_count"],
        date_count=config["date_count"],
        frequency_reverse=config["frequency_reverse"],
        created_reverse=config["created_reverse"],
    )

    # Avoid unnecessary writes when the active new-card order is already right.
    if ordered_ids == schedulable_ids:
        return OpChangesWithCount(count=0)

    # The default search is is:new (the complete normal new-card queue). With
    # a narrowed custom search, cards outside it are deliberately left alone.
    # shift_existing=False is essential: Anki must not shift other card due values.
    return col.sched.reposition_new_cards(
        card_ids=ordered_ids,
        starting_from=0,
        step_size=1,
        randomize=False,
        shift_existing=False,
    )


def _finish_reorder(result: Any = None) -> None:
    global _reorder_running, _reorder_again
    _reorder_running = False

    try:
        count = int(getattr(result, "count", 0) or 0)
    except (TypeError, ValueError):
        count = 0

    if count and _config()["show_tooltip"]:
        tooltip(f"Frequency + Date Reorder: updated {count} new-card positions.")

    if _reorder_again:
        _reorder_again = False
        if not _profile_closing and mw.col is not None:
            _timer.start(200)


def _fail_reorder(error: Exception) -> None:
    global _reorder_running, _reorder_again
    _reorder_running = False
    _reorder_again = False
    if not _profile_closing:
        tooltip(f"Frequency + Date Reorder failed: {error}")


def _start_reorder() -> None:
    global _reorder_running, _reorder_again

    if _profile_closing or mw.col is None:
        return
    if _reorder_running:
        _reorder_again = True
        return

    config = _config()
    _reorder_running = True
    operation = CollectionOp(
        parent=mw,
        op=lambda col: reorder_collection(col, config),
    )
    operation.success(_finish_reorder)
    operation.failure(_fail_reorder)
    try:
        operation.run_in_background()
    except Exception as error:
        _fail_reorder(error)


def schedule_reorder() -> None:
    """Debounce triggers so several additions combine into one reorder."""
    if _profile_closing or mw.col is None:
        return
    _timer.start(_config()["debounce_ms"])


def _schedule_add_reorder_if_enabled() -> None:
    # This helper is always dispatched to the GUI thread before reading config
    # or touching the Qt timer.
    if _config()["reorder_on_add"]:
        schedule_reorder()


def _on_profile_did_open() -> None:
    global _profile_closing, _reorder_again
    _profile_closing = False
    _reorder_again = False
    if _config()["reorder_on_open"]:
        schedule_reorder()


def _on_profile_will_close() -> None:
    global _profile_closing, _reorder_again
    _profile_closing = True
    _reorder_again = False
    _timer.stop()


def _on_note_will_be_added(_col: Any, _note: Any, _deck_id: Any) -> None:
    """Catch Add-window and AnkiConnect adds; the backend hook runs pre-insert."""
    # The hook may be called from a collection worker. Marshal to the GUI thread
    # before reading add-on config or starting QTimer.
    mw.taskman.run_on_main(_schedule_add_reorder_if_enabled)


def _on_note_added(_note: Any) -> None:
    """Post-insert Add-window hook; restart debounce after the note is saved."""
    if _config()["reorder_on_add"]:
        schedule_reorder()


def _on_sync_did_finish() -> None:
    if _config()["reorder_on_sync"]:
        schedule_reorder()


def _manual_reorder() -> None:
    schedule_reorder()
    tooltip("Frequency + Date Reorder: reorder queued.")


_timer = QTimer(mw)
_timer.setSingleShot(True)
_timer.timeout.connect(_start_reorder)

gui_hooks.profile_did_open.append(_on_profile_did_open)
gui_hooks.profile_will_close.append(_on_profile_will_close)
backend_hooks.note_will_be_added.append(_on_note_will_be_added)
gui_hooks.add_cards_did_add_note.append(_on_note_added)
gui_hooks.sync_did_finish.append(_on_sync_did_finish)

_reorder_action = QAction("Frequency + Date Reorder: Reorder New Cards", mw)
qconnect(_reorder_action.triggered, _manual_reorder)
mw.form.menuTools.addAction(_reorder_action)
