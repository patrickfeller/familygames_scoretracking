# Mobile & Tablet Interaction Redesign

_2026-06-17_

## Problem

Player selection uses HTML5 drag-and-drop (`dragstart`/`drop`) which never fires on touch screens. On a phone or tablet, players cannot be selected at all. Score entry uses wide tables with tiny inputs. History is a 5-column table that overflows narrow screens.

## Scope

Four screens: player selection, score entry (Yahtzee / Triominos / Uno), score history. No framework changes — same Flask + Jinja + vanilla JS.

---

## 1. Player Selection

**Option B: Two lists, tap to move.**

Replace all drag-and-drop with tap handlers. Keep the two-box structure (Playing / Available).

### Template (`select_players.html`)

- Remove all `draggable`, `ondragstart`, `ondragover`, `ondrop` attributes
- Playing list: each row shows turn number badge, avatar, name, ↑ / ↓ reorder buttons, × remove button
- Available list: each row shows avatar, name, + button; tapping anywhere on the row moves to Playing
- "Add new player" input + Add button below Available list
- Sticky bottom bar: "Start game · N players" green button (disabled/greyed when 0 players selected)
- Form hidden input `selected_player_ids` still comma-joined player IDs in turn order

### Script (`select_players.js`)

- Remove: all `DragEvent` listeners (`dragstart`, `dragover`, `dragleave`, `drop`)
- Add: `handleAdd(playerId)` — appends to Playing, removes from Available, re-renders
- Add: `handleRemove(playerId)` — moves back to Available
- Add: `handleUp(playerId)` / `handleDown(playerId)` — swap adjacent items in Playing array
- On any state change: re-render both lists, update hidden input, update button count
- "Add player" form: on submit, POST `/add_player` (existing route), then re-render
- Touch targets minimum 44 × 44 px

---

## 2. Yahtzee Score Entry

**Per-player tabs with live totals.**

### Template (`yahtzee.html`)

- Sticky tab bar at top: one tab per player, avatar + name, active tab highlighted green
- Live total banner below tabs: player name, Upper subtotal, Bonus status, Grand total (large number)
- Upper section inputs: label + numeric input per row
- Lower section inputs: label + numeric input per row
- All `<input>` elements: `inputmode="numeric"`, `font-size: 16px` (prevents iOS auto-zoom)
- Submit button at bottom: "Submit scores" — posts all players' data in one form (hidden inputs for inactive players populated from JS state)

### Script (`yahtzee.js`)

- State: `scores` object keyed by `playerId`, each holding category values
- `setActiveTab(playerId)`: re-renders visible inputs from stored state, saves current inputs to state first
- `recalculate()`: upper sum, bonus (35 if upper ≥ 63), lower sum, total — updates banner live on every `input` event
- On submit: populate hidden inputs for all players before form POST

---

## 3. Triominos Score Entry

**Sticky leaderboard + round cards with steppers.**

### Template (`triominos.html`)

- Sticky leaderboard at top: one card per player showing avatar, name, running total
- Round cards: one card per round, each showing player rows with − input + stepper buttons
- Stepper buttons: 44 × 44 px minimum, − decrements (floor 0), ＋ increments
- "+ Add round" dashed button at bottom
- "Save scores" sticky bottom bar
- All inputs: `inputmode="numeric"`, `font-size: 16px`
- Form POST structure unchanged: `score_<player_id>_<round>` fields

---

## 4. Uno Score Entry

**Tap finishing order instead of typing ranks.**

### Template (`enter_scores.html`, Uno branch)

- Instruction banner: "Tap each player in the order they went out. Tap again to clear."
- Player list: each row shows place badge (1st/2nd/3rd gold/silver/bronze, or · dashed), avatar, name, label
- Tapping an unranked player assigns next available rank; tapping a ranked player removes their rank and renumbers those below
- Submit button: disabled until all players ranked; label shows progress "Rank all N players (X/N)"
- On submit: hidden inputs `rank_<player_id>` = rank integer (1 = first out = winner for Uno scoring)
- Backend `UnoGame.process_scores` already expects `rank_<player_id>` — no backend change needed

---

## 5. Score History

**Session cards with filter chips.**

### Backend (`app.py` `/history` route)

Currently returns flat rows joined across games/players/scores. Change to group by `session_id`:

```python
# Query: select session_id, game name, min(created_at), list of (player, score, total_score, rank)
# Group rows by session_id, sort sessions by timestamp desc
# Pass `sessions` list to template instead of flat `scores` list
```

Winner per session: player with the highest `total_score` in that session (all three games store higher = better in `total_score`; `TriominosGame.process_scores` ranks highest total as winner per CLAUDE.md).

### Template (`history.html`)

- Filter chips row (sticky): All / Yahtzee / Uno / Triominos — JS hides/shows session cards by game name
- Session cards: game badge (colored initial), game name, formatted timestamp
- Each card: player rows with avatar, name, score/total, "Winner" pill for rank-1 player (gold background)
- "Back to home" button at bottom
- No server round-trip for filter — pure CSS class toggle via JS

---

## 6. Global Styles & Base

### `style.css`

- Add `font-size: 16px` to all `input` elements (prevents iOS keyboard zoom)
- Add touch-action / tap highlight suppression on interactive elements
- Responsive: remove `max-width: 960px` constraint on mobile (`@media (max-width: 768px)`)
- Card styles: `border-radius: 14–18px`, white background, `#f6f8f7` page background
- Sticky bottom action bar pattern: `position: sticky; bottom: 0; background: #fff; padding: 12px 16px`
- Green primary: `#1f9d57`; dark text: `#232b36`

### `base.html`

- Add Manrope font from Google Fonts (preconnect + stylesheet link)
- Existing Bootstrap-style classes can remain; new classes added alongside

---

## Out of Scope

- Game index page (`index.html`) — game grid already uses `auto-fit` CSS Grid, works fine on touch
- Confirmation page (`confirmation.html`) — simple table, readable on mobile
- Any backend game logic changes
- New games or new routes
