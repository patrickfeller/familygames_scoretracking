# Watten Game Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Watten (a team-based Austrian card game) to the family score tracker, with an interactive client-side setup+play UI that submits final scores to Flask/Postgres.

**Architecture:** Three new files (game class, template, tests) and targeted edits to `app.py`. All game logic runs client-side in vanilla JS; submission POSTs form data to a dedicated `/calculate_watten` Flask route that persists scores via the existing `add_score` helper. Player-to-team assignment happens inside the Watten template; the standard `select_players` route is still used to choose which DB players participate.

**Tech Stack:** Flask, Jinja2, psycopg2, vanilla JS (no bundler), Manrope font (already in base.html), Python stdlib (zlib/struct) for logo generation.

## Global Constraints

- Python game class must follow the 4-tuple return: `(bool, dict[int,int], dict[int,int], str)` matching how `app.py` calls `game_logic.process_scores`.
- Template extends `base.html`; must include `csrf_token` in every form POST.
- Inline JS must HTML-escape all user-supplied strings via an `esc()` helper before inserting into innerHTML.
- Logo filename: `static/images/watten_logo.png` (lowercase game name + `_logo.png`).
- Win target default: 11 (passed from Flask as `win_target` template variable).
- Negative rounds (−2) are valid; score cells accept any integer.
- Client-side-added players (draft input) are session-only and not submitted to the DB.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `games/watten.py` | Parse team form data → rankings + total_scores dicts |
| Create | `tests/test_watten.py` | Unit tests for WattenGame (no DB) |
| Modify | `app.py:117` | Seed 'Watten' in `ensure_games()` |
| Modify | `app.py:239` | Add `elif game_name == 'watten':` branch in `enter_scores` |
| Add | `app.py` (after `calculate_yahtzee`) | New `/calculate_watten/<game_id>/<player_ids>` route |
| Create | `static/images/watten_logo.png` | Card-themed placeholder PNG (128×128) |
| Create | `templates/watten.html` | Setup screen + play screen + JS game logic |

---

## Task 1: WattenGame class + unit tests

**Files:**
- Create: `games/watten.py`
- Create: `tests/test_watten.py`

**Interfaces:**
- Produces: `WattenGame().process_scores(players, form_data) -> (bool, dict[int,int], dict[int,int], str)`
  - `players`: list of RealDictRow with at least `id` key (not used internally, kept for interface parity)
  - `form_data`: dict-like with keys `team_count`, `team_{i}_players` (comma-sep int IDs), `team_{i}_score`
  - returns: `(success, rankings, total_scores, message)` where rankings/total_scores map `player_id → value`

- [ ] **Step 1: Create `games/watten.py`**

```python
class WattenGame:
    def __init__(self):
        self.name = "Watten"

    def process_scores(self, players, form_data):
        try:
            team_count = int(form_data.get('team_count', 2))
        except (ValueError, TypeError):
            return False, None, None, "Invalid team count."

        team_scores = {}
        team_members = {}
        for i in range(team_count):
            try:
                score = int(form_data.get(f'team_{i}_score', 0))
            except (ValueError, TypeError):
                return False, None, None, f"Invalid score for team {i + 1}."
            raw = form_data.get(f'team_{i}_players', '')
            pids = [int(x) for x in raw.split(',') if x.strip().lstrip('-').isdigit() and int(x) > 0]
            team_scores[i] = score
            team_members[i] = pids

        for i in range(team_count):
            if not team_members[i]:
                return False, None, None, f"Team {i + 1} has no players."

        sorted_teams = sorted(range(team_count), key=lambda i: team_scores[i], reverse=True)
        team_rank = {ti: rank + 1 for rank, ti in enumerate(sorted_teams)}

        rankings = {}
        total_scores = {}
        for ti in range(team_count):
            for pid in team_members[ti]:
                rankings[pid] = team_rank[ti]
                total_scores[pid] = team_scores[ti]

        if not rankings:
            return False, None, None, "No players assigned to teams."

        return True, rankings, total_scores, "Scores saved successfully."
```

- [ ] **Step 2: Create `tests/test_watten.py`**

```python
import unittest
from werkzeug.datastructures import ImmutableMultiDict
from games.watten import WattenGame


class TestWattenGame(unittest.TestCase):

    def setUp(self):
        self.game = WattenGame()
        self.p4 = [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}]

    def _form(self, t0_score, t1_score, t0_players='1,2', t1_players='3,4'):
        return ImmutableMultiDict([
            ('team_count', '2'),
            ('team_0_name', 'Team A'), ('team_0_players', t0_players), ('team_0_score', str(t0_score)),
            ('team_1_name', 'Team B'), ('team_1_players', t1_players), ('team_1_score', str(t1_score)),
        ])

    def test_winner_gets_rank_1(self):
        success, rankings, total_scores, msg = self.game.process_scores(self.p4, self._form(11, 7))
        self.assertTrue(success)
        self.assertEqual(rankings[1], 1)
        self.assertEqual(rankings[2], 1)
        self.assertEqual(rankings[3], 2)
        self.assertEqual(rankings[4], 2)

    def test_total_scores_match_team_score(self):
        success, rankings, total_scores, msg = self.game.process_scores(self.p4, self._form(11, 7))
        self.assertEqual(total_scores[1], 11)
        self.assertEqual(total_scores[2], 11)
        self.assertEqual(total_scores[3], 7)
        self.assertEqual(total_scores[4], 7)

    def test_loser_team_wins_when_higher_score(self):
        success, rankings, total_scores, msg = self.game.process_scores(self.p4, self._form(3, 11))
        self.assertEqual(rankings[3], 1)
        self.assertEqual(rankings[1], 2)

    def test_missing_team_players_fails(self):
        success, rankings, total_scores, msg = self.game.process_scores(
            self.p4, self._form(11, 7, t0_players=''))
        self.assertFalse(success)
        self.assertIsNone(rankings)

    def test_invalid_team_count_fails(self):
        form = ImmutableMultiDict([('team_count', 'abc')])
        success, rankings, total_scores, msg = self.game.process_scores(self.p4, form)
        self.assertFalse(success)
        self.assertIsNone(rankings)

    def test_one_player_per_team(self):
        players = [{'id': 1}, {'id': 2}]
        success, rankings, total_scores, msg = self.game.process_scores(
            players, self._form(11, 5, t0_players='1', t1_players='2'))
        self.assertTrue(success)
        self.assertEqual(rankings[1], 1)
        self.assertEqual(rankings[2], 2)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they pass**

```
uv run python -m unittest tests.test_watten -v
```

Expected output:
```
test_invalid_team_count_fails ... ok
test_loser_team_wins_when_higher_score ... ok
test_missing_team_players_fails ... ok
test_one_player_per_team ... ok
test_total_scores_match_team_score ... ok
test_winner_gets_rank_1 ... ok

Ran 6 tests in 0.XXXs

OK
```

- [ ] **Step 4: Commit**

```bash
git add games/watten.py tests/test_watten.py
git commit -m "feat: add WattenGame class and unit tests"
```

---

## Task 2: app.py plumbing + logo

**Files:**
- Modify: `app.py:117` — `ensure_games()`
- Modify: `app.py:239-243` — `enter_scores` game branch
- Add: `app.py` — `calculate_watten` route (after `calculate_yahtzee`, around line 267)
- Create: `static/images/watten_logo.png`

**Interfaces:**
- Consumes: `WattenGame().process_scores(players, form_data)` from Task 1
- Produces:
  - Route `calculate_watten(game_id, player_ids)` — accessible at `url_for('calculate_watten', game_id=..., player_ids=...)`
  - Template receives: `players`, `game`, `player_ids` (str), `win_target` (int 11)

- [ ] **Step 1: Add 'Watten' to `ensure_games()` in `app.py`**

Find this line in `app.py` (~line 117):
```python
    required_games = ['Yahtzee', 'Uno', 'Triominos']  # Add more games here
```
Replace with:
```python
    required_games = ['Yahtzee', 'Uno', 'Triominos', 'Watten']
```

- [ ] **Step 2: Add `elif game_name == 'watten':` branch in `enter_scores`**

Find these lines in `app.py` (~line 239):
```python
    if game_name == 'yahtzee':
        return render_template('yahtzee.html', players=players, game=game, player_ids=player_ids)
    elif game_name == 'triominos':
        return render_template('triominos.html', players=players, game=game, player_ids=player_ids)
    return render_template('enter_scores.html', players=players, game=game, is_uno=game_name == 'uno')
```
Replace with:
```python
    if game_name == 'yahtzee':
        return render_template('yahtzee.html', players=players, game=game, player_ids=player_ids)
    elif game_name == 'triominos':
        return render_template('triominos.html', players=players, game=game, player_ids=player_ids)
    elif game_name == 'watten':
        return render_template('watten.html', players=players, game=game, player_ids=player_ids, win_target=11)
    return render_template('enter_scores.html', players=players, game=game, is_uno=game_name == 'uno')
```

- [ ] **Step 3: Add `calculate_watten` route after `calculate_yahtzee` in `app.py`**

Insert after the closing line of `calculate_yahtzee` (~line 267):

```python
@app.route('/calculate_watten/<int:game_id>/<player_ids>', methods=['POST'])
def calculate_watten(game_id, player_ids):
    from games.watten import WattenGame
    watten = WattenGame()
    player_ids_list = [int(pid) for pid in player_ids.split(',') if pid]
    conn = get_db_connection()
    placeholders = ','.join(['%s'] * len(player_ids_list))
    players = query_db(conn, f'SELECT * FROM players WHERE id IN ({placeholders})', player_ids_list)
    conn.close()
    success, rankings, total_scores, message = watten.process_scores(players, request.form)
    if success:
        session_id = str(uuid.uuid4())
        add_score(game_id, rankings, session_id, total_scores)
        return redirect(url_for('confirmation', session_id=session_id))
    flash(message)
    return redirect(url_for('enter_scores', game_id=game_id, player_ids=player_ids))
```

- [ ] **Step 4: Create the logo — run this one-off Python script from project root**

```bash
uv run python -c "
import zlib, struct

def write_png(path, w, h, rgb_fn):
    rows = b''
    for y in range(h):
        rows += b'\\x00'
        for x in range(w):
            rows += bytes(rgb_fn(x, y))
    compressed = zlib.compress(rows)
    def crc32(d): return struct.pack('>I', zlib.crc32(d) & 0xffffffff)
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + crc32(t + d)
    with open(path, 'wb') as f:
        f.write(b'\\x89PNG\\r\\n\\x1a\\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)))
        f.write(chunk(b'IDAT', compressed))
        f.write(chunk(b'IEND', b''))

W = H = 128
def pixel(x, y):
    in_card1 = 16 < x < 76 and 18 < y < 110
    in_card2 = 52 < x < 112 and 12 < y < 104
    if in_card1 or in_card2:
        return (255, 255, 255)
    return (31, 157, 87)

write_png('static/images/watten_logo.png', W, H, pixel)
print('Created static/images/watten_logo.png')
"
```

Expected output: `Created static/images/watten_logo.png`

- [ ] **Step 5: Verify app starts and Watten tile appears**

```bash
uv run python app.py
```

Open http://127.0.0.1:5000/ — confirm "Watten" tile visible with card logo. Stop server (Ctrl-C).

- [ ] **Step 6: Commit**

```bash
git add app.py static/images/watten_logo.png
git commit -m "feat: register Watten game and add calculate_watten route"
```

---

## Task 3: watten.html template

**Files:**
- Create: `templates/watten.html`

**Interfaces:**
- Consumes from Flask context: `game` (dict with `id`, `name`), `players` (list of dicts with `id`, `name`), `player_ids` (str, e.g. `"1,2,3,4"`), `win_target` (int)
- POSTs to `url_for('calculate_watten', game_id=game.id, player_ids=player_ids)` with:
  - `csrf_token`, `team_count`, `team_0_name`, `team_0_players`, `team_0_score`, `team_1_name`, `team_1_players`, `team_1_score`

- [ ] **Step 1: Create `templates/watten.html`**

```html
{% extends 'base.html' %}
{% block content %}
<div class="watten-page">

  <!-- ===== SETUP SCREEN ===== -->
  <div id="screen-setup">
    <div class="watten-section-label">Teams <span class="watten-hint">· tap one, then add players</span></div>
    <div id="team-cards"></div>

    <div class="watten-section-label">Players <span class="watten-hint">· tap to add to <span id="active-team-name"></span></span></div>
    <div id="roster-cards"></div>

    <div class="add-player-row">
      <input id="draft-input" type="text" placeholder="Add a family member…" autocomplete="off" />
      <button id="add-player-btn" type="button">Add</button>
    </div>

    <button id="start-game-btn" type="button">Give every team a player</button>
  </div>

  <!-- ===== PLAY SCREEN ===== -->
  <div id="screen-play" style="display:none">
    <div id="game-over-banner" class="watten-over-banner" style="display:none">
      <svg width="30" height="22" viewBox="0 0 30 22" style="flex:0 0 auto"><path d="M3 6l5 5 7-9 7 9 5-5-2.4 13H5.4L3 6Z" fill="#e9b021" stroke="#c8941a" stroke-width="1"/><circle cx="3" cy="5" r="2.2" fill="#e9b021"/><circle cx="27" cy="5" r="2.2" fill="#e9b021"/><circle cx="15" cy="2" r="2.2" fill="#e9b021"/></svg>
      <div>
        <div id="winner-name" style="font:800 15.5px Manrope"></div>
        <div id="bummerl-note" style="font:600 12.5px/1.4 Manrope;color:#9c7b2e"></div>
      </div>
    </div>

    <div class="watten-hint-box">Tap a points button to log a round. Clear a score cell to remove that round.</div>

    <div id="score-cards"></div>

    <div class="play-footer">
      <div style="display:flex;gap:10px;width:100%">
        <button id="edit-teams-btn" type="button" class="watten-btn-outline">Teams</button>
        <button id="primary-action-btn" type="button" class="watten-btn-primary">Clear scores</button>
      </div>
      <button id="submit-btn" type="button" class="watten-btn-submit">Submit result</button>
    </div>
  </div>

</div>

<!-- Hidden submission form — populated by JS before submit -->
<form id="submit-form" method="POST"
      action="{{ url_for('calculate_watten', game_id=game.id, player_ids=player_ids) }}"
      style="display:none">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
</form>

<script>
const WIN_TARGET = {{ win_target }};
const DB_PLAYERS = {{ players | tojson }};
const TEAM_COLORS = ['oklch(0.56 0.13 150)', 'oklch(0.57 0.15 28)'];
const POINT_BUTTONS = [-2, 2, 3, 4, 5, 6];
const HUES = [28, 150, 250, 305, 85, 200];

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function initials(name) { return (name || '?').slice(0, 1).toUpperCase(); }

function playerColor(p) {
  if (typeof p.id === 'number') {
    const idx = DB_PLAYERS.findIndex(dp => dp.id === p.id);
    return `oklch(0.64 0.12 ${HUES[idx % HUES.length]})`;
  }
  const n = parseInt(String(p.id).replace('tmp_', ''), 10) || 0;
  return `oklch(0.63 0.12 ${(n * 53) % 360})`;
}

function avStyle(color, size) {
  return `display:inline-flex;align-items:center;justify-content:center;` +
    `width:${size}px;height:${size}px;border-radius:50%;` +
    `background:${color};color:#fff;` +
    `font:700 ${Math.round(size * 0.42)}px Manrope,sans-serif;flex:0 0 auto`;
}

// ---- STATE ----
const halfLen = Math.ceil(DB_PLAYERS.length / 2);
const initAssign = {};
DB_PLAYERS.forEach((p, i) => { initAssign[String(p.id)] = i < halfLen ? 0 : 1; });

let state = {
  screen: 'setup',
  active: 0,
  names: ['Team 1', 'Team 2'],
  assign: initAssign,
  extra: [],
  draft: '',
  rounds: [],
  gameOver: false,
  winner: null,
  submitted: false,
};

function allPlayers() { return [...DB_PLAYERS, ...state.extra]; }
function teamPlayers(i) { return allPlayers().filter(p => state.assign[String(p.id)] === i); }
function dbPlayersInTeam(i) { return DB_PLAYERS.filter(p => state.assign[String(p.id)] === i); }

function teamTotal(i, rounds) {
  return (rounds || state.rounds)
    .filter(r => r.team === i)
    .reduce((a, b) => a + b.pts, 0);
}

function checkWin(rounds) {
  for (let i = 0; i < 2; i++) {
    if (teamTotal(i, rounds) >= WIN_TARGET) return i;
  }
  return null;
}

function startValid() { return [0, 1].every(i => teamPlayers(i).length > 0); }

// ---- ACTIONS (called from onclick / event listeners) ----
function setActive(i) { state.active = i; render(); }

function toggleAssign(pid) {
  const key = String(pid);
  if (state.assign[key] === state.active) { delete state.assign[key]; }
  else { state.assign[key] = state.active; }
  render();
}

function addPlayer() {
  const n = state.draft.trim();
  if (!n) return;
  const id = 'tmp_' + state.extra.length;
  state.extra.push({ id, name: n });
  state.assign[id] = state.active;
  state.draft = '';
  document.getElementById('draft-input').value = '';
  render();
}

function startGame() {
  if (!startValid()) return;
  state.screen = 'play';
  state.rounds = [];
  state.gameOver = false;
  state.winner = null;
  render();
}

function award(teamIdx, pts) {
  if (state.gameOver) return;
  const newRounds = [...state.rounds, { team: teamIdx, pts }];
  const w = checkWin(newRounds);
  state.rounds = newRounds;
  if (w !== null) { state.gameOver = true; state.winner = w; }
  render();
}

function editCell(gi, rawVal) {
  const n = parseInt(rawVal, 10);
  const rounds = [...state.rounds];
  if (rawVal.trim() === '' || isNaN(n)) {
    rounds.splice(gi, 1);
  } else {
    rounds[gi] = { ...rounds[gi], pts: Math.min(40, Math.max(-99, n)) };
  }
  const w = checkWin(rounds);
  state.rounds = rounds;
  state.gameOver = w !== null;
  state.winner = w;
  render();
}

function resetRounds() {
  state.rounds = [];
  state.gameOver = false;
  state.winner = null;
  state.submitted = false;
  render();
}

function rematch() {
  state.rounds = [];
  state.gameOver = false;
  state.winner = null;
  state.submitted = false;
  render();
}

function editTeams() { state.screen = 'setup'; render(); }

function doSubmit() {
  if (!state.gameOver || state.submitted) return;
  const form = document.getElementById('submit-form');
  form.querySelectorAll('input:not([name="csrf_token"])').forEach(el => el.remove());
  function add(name, value) {
    const inp = document.createElement('input');
    inp.type = 'hidden'; inp.name = name; inp.value = value;
    form.appendChild(inp);
  }
  add('team_count', '2');
  [0, 1].forEach(i => {
    add(`team_${i}_name`, state.names[i]);
    add(`team_${i}_players`, dbPlayersInTeam(i).map(p => p.id).join(','));
    add(`team_${i}_score`, teamTotal(i));
  });
  state.submitted = true;
  form.submit();
}

// ---- RENDER ----
function renderSetup() {
  document.getElementById('screen-setup').style.display = '';
  document.getElementById('screen-play').style.display = 'none';
  document.getElementById('active-team-name').textContent = state.names[state.active];

  document.getElementById('team-cards').innerHTML = [0, 1].map(i => {
    const active = state.active === i;
    const color = TEAM_COLORS[i];
    const members = teamPlayers(i);
    const membersHtml = members.map(m =>
      `<span onclick="event.stopPropagation();toggleAssign(${typeof m.id==='number' ? m.id : "'"+m.id+"'"})"
             style="display:inline-flex;align-items:center;gap:7px;background:#f4f6f5;border:1px solid #e6ece8;border-radius:999px;padding:4px 10px 4px 4px;cursor:pointer">
        <span style="${avStyle(playerColor(m),22)}">${esc(initials(m.name))}</span>
        <span style="font:700 13px Manrope">${esc(m.name)}</span>
        <span style="color:#aeb6bb;font:700 14px Manrope;line-height:1">×</span>
      </span>`
    ).join('');
    return `
      <div onclick="setActive(${i})"
           style="background:#fff;border:2px solid ${active?'#1f9d57':'#eef1f0'};border-radius:16px;padding:12px 13px;cursor:pointer;margin-bottom:10px">
        <div style="display:flex;align-items:center;gap:10px">
          <div style="width:16px;height:16px;border-radius:6px;background:${color};flex:0 0 auto"></div>
          <input value="${esc(state.names[i])}"
                 oninput="state.names[${i}]=this.value;document.getElementById('active-team-name').textContent=state.names[state.active]"
                 onclick="event.stopPropagation()"
                 style="flex:1;min-width:0;border:none;background:transparent;font:800 15.5px Manrope;color:#232b36;outline:none;padding:2px 0" />
          ${active ? '<span style="font:800 9.5px Manrope;letter-spacing:.06em;text-transform:uppercase;background:#1f9d57;color:#fff;padding:4px 9px;border-radius:999px;flex:0 0 auto">Selected</span>' : ''}
          <span style="font:700 12px Manrope;color:#9aa3ab;flex:0 0 auto">
            ${members.length ? members.length + (members.length===1?' player':' players') : ''}
          </span>
        </div>
        ${members.length===0 ? '<div style="font:600 12.5px Manrope;color:#b6bdc2;margin-top:9px">No players yet — tap names below</div>' : ''}
        <div style="display:flex;flex-wrap:wrap;gap:7px;margin-top:9px">${membersHtml}</div>
      </div>`;
  }).join('');

  document.getElementById('roster-cards').innerHTML = allPlayers().map(p => {
    const tIdx = state.assign[String(p.id)];
    const assigned = tIdx !== undefined;
    const tColor = assigned ? TEAM_COLORS[tIdx] : null;
    const tName = assigned ? state.names[tIdx] : null;
    return `
      <div onclick="toggleAssign(${typeof p.id==='number' ? p.id : "'"+p.id+"'"})"
           style="display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:14px;
                  border:1px solid #eef1f0;background:#fff;cursor:pointer;min-height:58px;
                  border-left:5px solid ${assigned?tColor:'transparent'};margin-bottom:8px">
        <div style="${avStyle(playerColor(p),38)}">${esc(initials(p.name))}</div>
        <div style="flex:1;min-width:0;font:700 15.5px Manrope">${esc(p.name)}</div>
        <div style="${assigned
          ? `font:800 11.5px Manrope;color:#fff;background:${tColor};padding:6px 11px;border-radius:999px;flex:0 0 auto`
          : 'font:700 12.5px Manrope;color:#b6bdc2;flex:0 0 auto'}">
          ${assigned ? esc(tName) : 'tap to add'}
        </div>
      </div>`;
  }).join('');

  const valid = startValid();
  const btn = document.getElementById('start-game-btn');
  const count = allPlayers().filter(p => state.assign[String(p.id)] !== undefined).length;
  btn.textContent = valid ? `Start game · ${count} players` : 'Give every team a player';
  btn.style.background = valid ? '#1f9d57' : '#cdd4ce';
  btn.style.cursor = valid ? 'pointer' : 'default';
}

function renderPlay() {
  document.getElementById('screen-setup').style.display = 'none';
  document.getElementById('screen-play').style.display = '';

  const banner = document.getElementById('game-over-banner');
  if (state.gameOver && state.winner !== null) {
    banner.style.display = 'flex';
    document.getElementById('winner-name').textContent = `${state.names[state.winner]} wins!`;
    const losers = [0, 1].filter(i => i !== state.winner).map(i => state.names[i]);
    document.getElementById('bummerl-note').textContent =
      `${losers.join(' & ')} ${losers.length > 1 ? 'each take' : 'takes'} a black point.`;
  } else {
    banner.style.display = 'none';
  }

  const dim = state.gameOver;
  document.getElementById('score-cards').innerHTML = [0, 1].map(i => {
    const color = TEAM_COLORS[i];
    const total = teamTotal(i);
    const isWinner = state.gameOver && state.winner === i;
    const pct = Math.min(total / WIN_TARGET, 1) * 100;
    const members = teamPlayers(i);

    const membersHtml = members.map(m =>
      `<span style="${avStyle(playerColor(m),20)}">${esc(initials(m.name))}</span>`
    ).join('');

    const buttonsHtml = POINT_BUTTONS.map(pp => {
      const neg = pp < 0;
      const bd = dim ? '#edf0ee' : (neg ? '#eccfcf' : '#cfe7d9');
      const bg = dim ? '#f4f6f5' : (neg ? '#fbeeee' : '#eef7f1');
      const col = dim ? '#c2c9c4' : (neg ? '#c0492f' : '#1f9d57');
      return `<div onclick="award(${i},${pp})"
                   style="width:46px;height:36px;border-radius:12px;border:1px solid ${bd};
                          background:${bg};color:${col};font:800 17px Manrope;
                          display:inline-flex;align-items:center;justify-content:center;
                          cursor:${dim?'default':'pointer'}">${pp}</div>`;
    }).join('');

    const cellsHtml = state.rounds.map((r, gi) => {
      if (r.team !== i) return '';
      return `<input value="${r.pts}"
                     onchange="editCell(${gi}, this.value)"
                     inputmode="numeric"
                     style="width:46px;height:38px;border:1px solid #e0e5e1;border-radius:10px;
                            text-align:center;font:800 17px Manrope;background:#f7faf8;
                            outline:none;color:${r.pts<0?'#c0492f':'#232b36'}" />`;
    }).join('');

    const noRounds = !state.rounds.some(r => r.team === i);

    return `
      <div style="display:flex;gap:12px;background:${isWinner?'#fffaef':'#fff'};
                  border:1px solid ${isWinner?'#f0dca0':'#eef1f0'};border-radius:18px;
                  padding:13px;margin-bottom:11px">
        <div style="display:flex;flex-direction:column;align-items:center;gap:6px;flex:0 0 auto">
          <div style="font:800 9px Manrope;letter-spacing:.1em;color:#9aa3ab;text-transform:uppercase">Add</div>
          ${buttonsHtml}
        </div>
        <div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:9px">
          <div style="display:flex;align-items:center;gap:9px">
            <div style="width:14px;height:14px;border-radius:5px;background:${color};flex:0 0 auto"></div>
            <div style="min-width:0;flex:1">
              <div style="font:800 15.5px Manrope;line-height:1.1">${esc(state.names[i])}</div>
              <div style="display:flex;gap:4px;margin-top:5px">${membersHtml}</div>
            </div>
            <div style="text-align:right;flex:0 0 auto">
              <span style="font:800 26px Manrope;line-height:1;color:${isWinner?'#cf9a14':'#232b36'}">${total}</span>
              <span style="font:700 12px Manrope;color:#9aa3ab"> /${WIN_TARGET}</span>
            </div>
          </div>
          <div style="height:6px;border-radius:999px;background:#eef1f0;overflow:hidden">
            <div style="height:100%;width:${pct}%;background:${isWinner?'#d9a420':color};border-radius:999px;transition:width 0.2s"></div>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;min-height:38px">
            ${noRounds
              ? '<span style="font:600 12px Manrope;color:#b6bdc2;padding:0 2px">No rounds yet — tap 2 / 3 / 4</span>'
              : cellsHtml}
          </div>
        </div>
      </div>`;
  }).join('');

  // Primary button
  const primBtn = document.getElementById('primary-action-btn');
  if (state.gameOver) {
    primBtn.textContent = 'Start rematch';
    primBtn.style.background = '#1f9d57';
    primBtn.style.color = '#fff';
    primBtn.onclick = rematch;
  } else {
    primBtn.textContent = 'Clear scores';
    primBtn.style.background = '#eef1f0';
    primBtn.style.color = '#56606c';
    primBtn.onclick = resetRounds;
  }

  // Submit button
  const canSubmit = state.gameOver && !state.submitted;
  const subBtn = document.getElementById('submit-btn');
  subBtn.textContent = state.submitted ? 'Submitted ✓' : 'Submit result';
  subBtn.disabled = !canSubmit;
  subBtn.style.background = state.submitted ? '#1f9d57' : (canSubmit ? '#232b36' : '#eef1f0');
  subBtn.style.color = (canSubmit || state.submitted) ? '#fff' : '#b6bdc2';
  subBtn.style.cursor = canSubmit ? 'pointer' : 'default';
}

function render() {
  if (state.screen === 'setup') renderSetup();
  else renderPlay();
}

// ---- EVENT WIRING ----
document.getElementById('draft-input').addEventListener('input', e => { state.draft = e.target.value; });
document.getElementById('draft-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); addPlayer(); }
});
document.getElementById('add-player-btn').addEventListener('click', addPlayer);
document.getElementById('start-game-btn').addEventListener('click', startGame);
document.getElementById('edit-teams-btn').addEventListener('click', editTeams);
document.getElementById('submit-btn').addEventListener('click', doSubmit);
document.getElementById('primary-action-btn').addEventListener('click', resetRounds);

render();
</script>

<style>
.watten-page { max-width: 520px; margin: 0 auto; padding: 0 0 80px; }
.watten-section-label { font: 800 11.5px Manrope, sans-serif; letter-spacing: .1em; color: #9aa3ab; text-transform: uppercase; margin: 0 2px 9px; }
.watten-hint { font-weight: 600; text-transform: none; letter-spacing: 0; }
.add-player-row { display: flex; gap: 8px; margin-top: 14px; }
.add-player-row input {
  flex: 1; height: 46px; border: 1px solid #dde2df; border-radius: 13px;
  padding: 0 14px; font: 600 15px Manrope, sans-serif; outline: none; background: #fff;
}
.add-player-row button {
  height: 46px; padding: 0 18px; border-radius: 13px; background: #232b36;
  color: #fff; font: 700 15px Manrope, sans-serif; border: none; cursor: pointer; flex: 0 0 auto;
}
#start-game-btn {
  width: 100%; height: 56px; border-radius: 16px; color: #fff;
  font: 800 17px Manrope, sans-serif; border: none; margin-top: 16px;
}
.watten-over-banner {
  display: flex; align-items: center; gap: 12px;
  background: #fff7e8; border: 1px solid #f3e2bd; border-radius: 16px;
  padding: 14px 16px; margin-bottom: 14px;
}
.watten-hint-box {
  background: #eef6f1; border-radius: 13px; padding: 11px 13px; margin-bottom: 14px;
  font: 600 12.5px/1.45 Manrope, sans-serif; color: #3f6b53;
}
.play-footer { display: flex; flex-direction: column; gap: 9px; margin-top: 16px; }
.watten-btn-outline {
  flex: 0 0 auto; padding: 0 20px; height: 54px; border-radius: 15px;
  border: 1px solid #dde2df; background: #fff; color: #232b36;
  font: 700 15px Manrope, sans-serif; cursor: pointer;
}
.watten-btn-primary {
  flex: 1; height: 54px; border-radius: 15px; border: none;
  font: 800 15px Manrope, sans-serif; cursor: pointer;
}
.watten-btn-submit {
  width: 100%; height: 50px; border-radius: 15px; border: none;
  font: 800 15px Manrope, sans-serif;
}
</style>

{% endblock %}
```

- [ ] **Step 2: Run the full test suite to verify nothing broke**

```
uv run python -m unittest discover tests -v
```

Expected: All existing tests pass + 6 new WattenGame tests pass.

- [ ] **Step 3: Manual integration test**

```bash
uv run python app.py
```

Verify this flow:
1. Navigate to http://127.0.0.1:5000/ → Watten tile visible
2. Click Watten → select 4 players → Continue
3. Setup screen: two teams pre-populated, player names visible
4. Tap a player to move between teams
5. Type a new name in "Add a family member…" → Add → appears in roster
6. Click "Start game" (only enabled when both teams have ≥1 player)
7. Play screen: click `+2`, `+3`, etc. buttons → score updates, progress bar fills
8. Score cells are editable; clear a cell → round disappears
9. Score a team to 11+ → game over banner appears, "Start rematch" shown
10. "Submit result" → redirects to confirmation page with results table
11. History page shows Watten session

- [ ] **Step 4: Commit**

```bash
git add templates/watten.html
git commit -m "feat: add Watten interactive score tracking template"
```

---

## Self-Review

**Spec coverage:**
- ✅ Team-based setup (2 teams, editable names, player roster assignment)
- ✅ Add new family member (client-side draft input)
- ✅ Start game validation (both teams need ≥1 player)
- ✅ Quick-add buttons: −2, 2, 3, 4, 5, 6
- ✅ Editable score cells (onchange, clear to remove round)
- ✅ Win detection (first to WIN_TARGET)
- ✅ Game over banner + bummerl note
- ✅ Start rematch / Clear scores footer actions
- ✅ Submit result → POST → Flask → confirmation page
- ✅ Logo file at correct path

**Placeholder scan:** No TBDs, no "add appropriate error handling" patterns. All code is complete.

**Type consistency:**
- `WattenGame.process_scores` returns 4-tuple `(bool, dict, dict, str)` — matches `app.py:222` unpack
- `calculate_watten` route passes `players` list + `request.form` to `process_scores` — matches method signature
- `team_0_players` / `team_1_players` in JS `doSubmit` matches `form_data.get(f'team_{i}_players', '')` in WattenGame
- `teamTotal(i)` in JS returns integer total per team — matches `team_{i}_score` read in WattenGame
