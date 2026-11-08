# Designant

A focused Anki add-on for ordering the active new-card queue by frequency, with a short creation-time block in the middle.

## Ordering

The default order is:

| New-card queue position | Ordering |
|---|---|
| 1–20 | `FreqSort`, ascending by default |
| 21–25 | Card creation timestamp, oldest first |
| 26 onward | `FreqSort`, ascending by default |

The five-card time group is selected from the cards remaining after the first 20 frequency-ranked cards. The final group is then frequency-ranked again. With a daily new-card limit of 25, this gives the requested 20 frequency-ranked cards plus five oldest-created cards.


## How the split interacts with the daily new-card limit

The add-on's split is based on **queue positions**, not on the deck's daily limit. The defaults always reserve:
- 20 positions for frequency-ranked cards,
- 5 positions for oldest-created cards,
- then frequency-ranked cards for every later position.

For example, with a daily new-card limit of **30**, Anki draws up to 30 cards from the queue:
- positions 1–20: FreqSort,
- positions 21–25: oldest-created,
- positions 26–30: FreqSort again.

With a limit of 25, you see the first two groups only. With a limit of 15, you see only the first 15 frequency-ranked cards. Raising the limit from 25 to 30 does not change the 20/5 split; it exposes five more cards from the final frequency-ranked section.

The grouping is independent of the limit. If you later change your daily limit to 40, positions 31–40 also come from the final frequency-ranked section.

This assumes Anki is drawing from the same new-card queue selected by `search_to_sort` and that other deck/subdeck limits or other add-ons are not imposing a different selection order.



## Sorting mode switches

Both switches default to `true`:

| `enable_freq_sort` | `enable_time_sort` | Behavior |
|---|---|---|
| `true` | `true` | Normal three-part order: first frequency block, creation-time block, then frequency-sorted remainder. |
| `true` | `false` | Entire selected queue is sorted by `FreqSort`, like a single-field AutoReorder. |
| `false` | `true` | Entire selected queue is sorted by Created Time (Card), oldest first. |
| `false` | `false` | Preserve Anki's existing due order; no sorting is applied. |

The `frequency_count` and `created_time_count` split sizes are used when both switches are enabled. In single-sort mode, the enabled sort applies to the entire selected queue.

For example, with `frequency_count: 20`, both switches enabled, and a deck daily new-card limit of 20, the 20 cards Anki introduces that day are all from the first FreqSort block. The creation-time block begins at position 21, so it does not appear in that day's study queue. This is effectively a pure FreqSort reorder for that day's 20 cards.

## Creation date vs. creation time

The middle group uses **Created Time (Card)**, not a day-only Created Date value. Anki card IDs contain the card's creation timestamp in milliseconds, and Designant sorts those IDs numerically. This preserves the date and the time within that date.

If 25 cards were all created today, the add-on will not skip the date group or wait for cards from an earlier calendar day. It first places the 20 best-ranked cards by `FreqSort`; the next five cards are the five oldest creation timestamps among the remaining cards. If all 25 were created today, those five will also be from today, ordered by the time they were created.

For cards that share the same calendar date, creation time still distinguishes their order. The daily limit controls how many of those positions Anki introduces; it does not alter how Designant chooses the groups.

## Safety: what the add-on changes

The add-on only repositions **active, ordinary new cards**. A candidate must have Anki's `CardType.New` (`type == 0`), `CardQueue.New` (`queue == 0`), and no original deck ID (`odid == 0`).

It calls Anki's `reposition_new_cards()` with `shift_existing=False`, then restores Anki's saved random-reposition and shift-existing preferences. Learning, review, suspended, buried, and filtered-deck cards are not passed to the reorder operation. The add-on does not change review intervals, ease, FSRS memory state, deck options, or daily limits.

The default search is `deck:mining is:new`, so the add-on manages the active ordinary new-card queue in the Mining deck (including its matching subdecks, according to Anki search semantics). New cards in other decks are left untouched. Because new-card due positions are shared, reordering only one deck can leave position numbers overlapping with cards outside that search; this is intentional for this Mining-only default.

## Install

1. Back up your Anki collection.
2. In Anki, open **Tools → Add-ons → Install from file**.
3. Select the `.ankiaddon` package built from this repository.
4. Restart Anki.
5. Use **Tools → Designant** for a manual test.

Disable AutoReorder and Priority Reorder for the same cards while this add-on is active, otherwise those add-ons may overwrite its queue order.

## Automatic triggers

- After adding a note through Anki's Add window.
- After adding a note through AnkiConnect (using `note_will_be_added`).
- After editing an existing note's fields through AnkiConnect `updateNoteFields` or `updateNote` (using Anki's `note_will_flush` hook). A tag-only update does not change `FreqSort` and does not require a reorder.
- Whenever an Anki profile is opened or switched to.
- After synchronization finishes, to include new cards received from another device.
- Imports do not trigger `note_will_be_added`; sync and the next profile open are the catch-up points.

Triggers restart a single-shot timer. The reorder runs **5 seconds after the latest trigger**, allowing a burst of adds or updates to be combined into one reorder. Change this delay with `automatic_reordering.delay_ms`.

## Configuration

Open **Tools → Add-ons → Designant → Config**.

The configuration is grouped into two sections:

- `sorting_options`: frequency/time sorting rules and their direction/count settings.
- `automatic_reordering`: when to run the reorder, the delay, and whether to show a tooltip.

The search query and frequency field remain top-level settings. The default configuration is:

```json
{
    "search_to_sort": "deck:mining is:new",
    "frequency_field": "FreqSort",
    "sorting_options": {
        "frequency_count": 20,
        "enable_freq_sort": true,
        "created_time_count": 5,
        "enable_time_sort": true,
        "frequency_reverse": false,
        "created_reverse": false
    },
    "automatic_reordering": {
        "reorder_on_open": true,
        "reorder_on_add": true,
        "reorder_on_note_update": true,
        "reorder_on_sync": true,
        "delay_ms": 5000,
        "show_tooltip": true
    }
}
```

| Setting | Default | Meaning |
|---|---:|---|
| `search_to_sort` | `deck:mining is:new` | Anki search selecting candidates; each card is additionally checked for new queue state and non-filtered status. |
| `frequency_field` | `FreqSort` | Note field containing numeric frequency/rank values. |
| `sorting_options.frequency_count` | `20` | Number of frequency-ranked cards placed first (used when both sort modes are enabled). |
| `sorting_options.enable_freq_sort` | `true` | Enable frequency sorting. With time sorting off, the whole queue is sorted by `FreqSort`. |
| `sorting_options.enable_time_sort` | `true` | Enable creation-time sorting. With frequency sorting off, the whole queue is sorted by Created Time (Card). |
| `sorting_options.created_time_count` | `5` | Number of oldest remaining cards in the middle group. |
| `sorting_options.frequency_reverse` | `false` | Set true if larger frequency values should come first. |
| `sorting_options.created_reverse` | `false` | Set true for newest-created cards first in the middle group. |
| `automatic_reordering.reorder_on_open` | `true` | Reorder when a profile opens. |
| `automatic_reordering.reorder_on_add` | `true` | Reorder after Add-window or AnkiConnect note additions. |
| `automatic_reordering.reorder_on_note_update` | `true` | Reorder after an existing note is saved/updated, including AnkiConnect field updates. |
| `automatic_reordering.reorder_on_sync` | `true` | Reorder after sync finishes. |
| `automatic_reordering.delay_ms` | `5000` | Wait 5 seconds after the latest trigger before reordering. |
| `automatic_reordering.show_tooltip` | `true` | Show a notice when positions change. |

Blank or non-numeric `FreqSort` values cannot be frequency-ranked. They can enter the five-card time group; any remaining cards without a numeric value trail the final frequency-ranked group.

Anki card IDs are millisecond timestamps of card creation, so the add-on uses the ID for the time group instead of note modification time. This is equivalent to sorting by **Created Time (Card)**, not just **Created Date (Card)**.

## Development

The ordering helpers and config normalization are pure Python and have unit tests:

```bash
python -m unittest discover -s tests -v
python -m compileall -q __init__.py core.py
python tools/build_addon.py
```

The build script produces `dist/frequency_date_reorder.ankiaddon`, containing only the files Anki needs at the add-on root.
