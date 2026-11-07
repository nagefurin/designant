# Designant

A focused Anki add-on for ordering the active new-card queue by frequency, with a short creation-date block in the middle.

## Ordering

The default order is:

| New-card queue position | Ordering |
|---|---|
| 1–20 | `FreqSort`, ascending by default |
| 21–25 | Card creation timestamp, oldest first |
| 26 onward | `FreqSort`, ascending by default |

The five-card date group is selected from the cards remaining after the first 20 frequency-ranked cards. The final group is then frequency-ranked again. With a daily new-card limit of 25, this gives the requested 20 frequency-ranked cards plus five oldest-created cards.


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

## Safety: what the add-on changes

The add-on only repositions **active, ordinary new cards**. A candidate must have Anki's `CardType.New` (`type == 0`), `CardQueue.New` (`queue == 0`), and no original deck ID (`odid == 0`).

It calls Anki's `reposition_new_cards()` with `shift_existing=False`, then restores Anki's saved random-reposition and shift-existing preferences. Learning, review, suspended, buried, and filtered-deck cards are not passed to the reorder operation. The add-on does not change review intervals, ease, FSRS memory state, deck options, or daily limits.

The default search is `deck:mining is:new`, so the add-on manages the complete ordinary new-card queue. Narrowing `search_to_sort` to a subset intentionally leaves other new cards untouched; because new-card due positions are shared, this can create overlapping position numbers. Keep the default unless a partial reorder is intentional.

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
- After editing an existing note through AnkiConnect `updateNoteFields` or `updateNote` (using Anki's `note_will_flush` hook).
- Whenever an Anki profile is opened or switched to.
- After synchronization finishes, to include new cards received from another device.
- Imports do not trigger `note_will_be_added`; sync and the next profile open are the catch-up points.

Add events are debounced so several notes added close together result in one reorder.

## Configuration

Open **Tools → Add-ons → Designant → Config**.

| Setting | Default | Meaning |
|---|---:|---|
| `search_to_sort` | `deck:mining is:new` | Anki search selecting candidates; each card is additionally checked for new queue state and non-filtered status. |
| `frequency_field` | `FreqSort` | Note field containing numeric frequency/rank values. |
| `frequency_count` | `20` | Number of frequency-ranked cards placed first. |
| `created_time_count` | `5` | Number of oldest remaining cards in the middle group. |
| `frequency_reverse` | `false` | Set true if larger frequency values should come first. |
| `created_reverse` | `false` | Set true for newest-created cards first in the middle group. |
| `reorder_on_open` | `true` | Reorder when a profile opens. |
| `reorder_on_add` | `true` | Reorder after Add-window or AnkiConnect note additions. |
| `reorder_on_note_update` | `true` | Reorder after an existing note is saved/updated, including AnkiConnect field updates. |
| `reorder_on_sync` | `true` | Reorder after sync finishes. |
| `debounce_ms` | `700` | Delay after an add event before reordering. |
| `show_tooltip` | `true` | Show a notice when positions change. |

Blank or non-numeric `FreqSort` values cannot be frequency-ranked. They can enter the five-card date group; any remaining cards without a numeric value trail the final frequency-ranked group.

Anki card IDs are millisecond timestamps of card creation, so the add-on uses the ID for the date group instead of note modification time.

## Development

The ordering helpers are pure Python and have unit tests:

```bash
python -m unittest discover -s tests -v
python -m compileall -q __init__.py core.py
python tools/build_addon.py
```

The build script produces `dist/frequency_date_reorder.ankiaddon`, containing only the files Anki needs at the add-on root.
