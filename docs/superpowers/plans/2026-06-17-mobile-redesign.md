# Mobile & Tablet Interaction Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace broken drag-and-drop player selection and cramped desktop tables with touch-native interactions across all game screens and history.

**Architecture:** Pure template + JS changes; same Flask routes, same form POST field names. History route adds Python-side grouping by `session_id`. No new files except for the style additions.

**Tech Stack:** Flask/Jinja2, vanilla JS, psycopg2, CSS (no build step). Run app with `uv run python app.py`. Run tests with `uv run python -m unittest discover tests`.

---

## File Map

| File | Change |
|---|---|
| `templates/base.html` | Add Manrope font preconnect + stylesheet |
| `static/style.css` | Mobile styles, input font-size fix, new component classes |
| `templates/select_players.html` | Option B: two-list tap-to-move + ↑/↓ reorder |
| `static/select_players.js` | Replace all drag-and-drop with tap handlers |
| `templates/yahtzee.html` | Per-player tabs, tall inputs, live total banner |
| `static/yahtzee.js` | Tab switching + live totals per active player |
| `templates/triominos.html` | Sticky leaderboard + round cards with −/＋ steppers |
| `templates/enter_scores.html` | Uno tap-finishing-order UI (hidden inputs for backend) |
| `app.py` | `get_score_history()` adds `session_id`; `/history` route groups rows by session |
| `templates/history.html` | Session cards, filter chips, winner highlight |

---

## Task 1: Font & Global Mobile CSS

**Files:**
- Modify: `templates/base.html`
- Modify: `static/style.css`

- [ ] **Step 1: Add Manrope font to base.html**

Replace the `<head>` block in `templates/base.html` with:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Family Game Score Tracker</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
</head>
```

- [ ] **Step 2: Add mobile CSS to style.css**

Append to the end of `static/style.css`:

```css
/* ===== MOBILE / TOUCH OVERRIDES ===== */

/* Use Manrope everywhere */
body {
    font-family: 'Manrope', 'Arial', sans-serif;
}

/* Prevent iOS from zooming on input focus (needs 16px font-size) */
input[type="text"],
input[type="number"],
select,
textarea {
    font-size: 16px !important;
}

/* Remove tap highlight flash on interactive elements */
button, .btn-touch, [onclick] {
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
}

/* Responsive: full-width main on phones */
@media (max-width: 768px) {
    main {
        max-width: 100%;
        margin: 0;
        border-radius: 0;
        padding: 12px;
    }
    header h1 {
        font-size: 1.4em;
    }
}

/* Sticky action bar pattern */
.sticky-bottom {
    position: sticky;
    bottom: 0;
    background: #fff;
    padding: 12px 16px 16px;
    border-top: 1px solid #eef1f0;
    z-index: 10;
}

/* Primary action button */
.btn-primary-green {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 56px;
    border-radius: 16px;
    background: #1f9d57;
    color: #fff;
    font: 800 17px 'Manrope', sans-serif;
    border: none;
    cursor: pointer;
    width: 100%;
    text-decoration: none;
    -webkit-tap-highlight-color: transparent;
}
.btn-primary-green:disabled,
.btn-primary-green.disabled {
    background: #cdd4ce;
    cursor: default;
}
.btn-primary-green:hover:not(:disabled):not(.disabled) {
    background: #1a8a4b;
}

/* Avatar circle */
.avatar {
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    color: #fff;
    font-weight: 700;
    flex-shrink: 0;
}

/* Touch-target minimum */
.touch-btn {
    min-width: 44px;
    min-height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
}
```

- [ ] **Step 3: Run tests to confirm no breakage**

```
uv run python -m unittest discover tests
```

Expected: all tests pass (no Python changes yet).

- [ ] **Step 4: Commit**

```bash
git add templates/base.html static/style.css
git commit -m "style: add Manrope font, mobile base styles, iOS input zoom fix"
```

---

## Task 2: Player Selection — Option B (Two Lists, Tap to Move)

**Files:**
- Modify: `templates/select_players.html`
- Modify: `static/select_players.js`

- [ ] **Step 1: Rewrite select_players.html**

Replace the entire content of `templates/select_players.html` with:

```html
{% extends 'base.html' %}
{% block content %}

<section class="player-selection">
  <h2>Select Players for {{ game['name'] }}</h2>

  <!-- PLAYING box -->
  <div class="sp-box sp-box--playing">
    <div class="sp-box__header">
      <span class="sp-box__label sp-box__label--green">PLAYING · <span id="playingCount">0</span></span>
      <span class="sp-box__hint">tap × to remove</span>
    </div>
    <p id="playingEmpty" class="sp-empty">No players selected yet.</p>
    <ul id="selectedPlayers" class="sp-list"></ul>
  </div>

  <!-- AVAILABLE box -->
  <div class="sp-box">
    <div class="sp-box__header">
      <span class="sp-box__label">AVAILABLE · tap to add</span>
    </div>
    <p id="availableEmpty" class="sp-empty" style="display:none">Everyone's in the game.</p>
    <ul id="availablePlayers" class="sp-list">
      {% for player in players %}
      <li class="sp-item sp-item--avail" data-player-id="{{ player['id'] }}" data-player-name="{{ player['name'] }}">
        <span class="avatar sp-avatar" style="background:{{ player.get('color','#1f9d57') }}">{{ player['name'][0].upper() }}</span>
        <span class="sp-name">{{ player['name'] }}</span>
        <span class="sp-add-icon">+</span>
      </li>
      {% endfor %}
    </ul>
  </div>

  <!-- Add new player -->
  <div class="add-player-section">
    <h3>Add New Player</h3>
    <form id="addPlayerForm" method="post" action="{{ url_for('select_players', game_id=game['id']) }}">
      <input type="text" name="new_player_name" placeholder="New player name" required>
      <button type="submit" name="action" value="add_player">Add Player</button>
    </form>
  </div>

  <!-- Submit -->
  <div class="sticky-bottom">
    <form id="selectPlayersForm" method="post">
      <input type="hidden" name="selected_player_ids" id="selectedPlayerIdsInput">
      <button type="submit" id="startGameBtn" class="btn-primary-green disabled" disabled>
        Start game · <span id="startCount">0</span> players
      </button>
    </form>
  </div>
</section>

<style>
.player-selection { padding-bottom: 80px; }
.sp-box {
  background: #fff;
  border: 1px solid #e6ece8;
  border-radius: 18px;
  padding: 13px;
  margin-bottom: 14px;
}
.sp-box--playing { border-color: #b8dfc8; }
.sp-box__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.sp-box__label { font: 800 13px 'Manrope',sans-serif; color: #8b949c; }
.sp-box__label--green { color: #1f9d57; }
.sp-box__hint { font: 600 11.5px 'Manrope',sans-serif; color: #9aa3ab; }
.sp-empty { font: 600 13px 'Manrope',sans-serif; color: #9aa3ab; padding: 10px 2px; margin: 0; }
.sp-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.sp-item {
  display: flex; align-items: center; gap: 10px;
  background: #fafbfb; border: 1px solid #eef1f0; border-radius: 13px;
  padding: 9px 11px; cursor: pointer; user-select: none;
  -webkit-tap-highlight-color: transparent; touch-action: manipulation;
  min-height: 52px;
}
.sp-item--playing { background: #f4faf6; border-color: #dcebe1; }
.sp-avatar { width: 36px; height: 36px; font-size: 15px; }
.sp-name { flex: 1; font: 700 15px 'Manrope',sans-serif; }
.sp-add-icon { width: 30px; height: 30px; border-radius: 9px; background: #e7f5ec; color: #1f9d57; display: flex; align-items: center; justify-content: center; font: 700 21px 'Manrope',sans-serif; flex-shrink: 0; }
.sp-turn { width: 24px; height: 24px; border-radius: 7px; background: #1f9d57; color: #fff; display: flex; align-items: center; justify-content: center; font: 800 13px 'Manrope',sans-serif; flex-shrink: 0; }
.sp-reorder { width: 36px; height: 36px; border-radius: 10px; border: 1px solid #e2e6e3; background: #fff; color: #3c454e; display: flex; align-items: center; justify-content: center; font: 700 16px 'Manrope',sans-serif; cursor: pointer; flex-shrink: 0; -webkit-tap-highlight-color: transparent; touch-action: manipulation; }
.sp-reorder:disabled { opacity: 0.3; }
.sp-remove { width: 36px; height: 36px; border-radius: 10px; border: 1px solid #f2dada; background: #fff; color: #d6685e; display: flex; align-items: center; justify-content: center; font: 700 17px 'Manrope',sans-serif; cursor: pointer; flex-shrink: 0; -webkit-tap-highlight-color: transparent; touch-action: manipulation; }
</style>

<script src="{{ url_for('static', filename='select_players.js') }}"></script>
{% endblock %}
```

- [ ] **Step 2: Rewrite select_players.js**

Replace the entire content of `static/select_players.js` with:

```javascript
(function () {
  // State: ordered array of player objects {id, name}
  let playing = [];

  // Collect all players from the available list as initial source of truth
  const availList = document.getElementById('availablePlayers');
  const selList = document.getElementById('selectedPlayers');
  const hiddenInput = document.getElementById('selectedPlayerIdsInput');
  const startBtn = document.getElementById('startGameBtn');
  const startCount = document.getElementById('startCount');
  const playingCount = document.getElementById('playingCount');
  const playingEmpty = document.getElementById('playingEmpty');
  const availEmpty = document.getElementById('availableEmpty');

  // Initial player data from rendered <li> elements
  const allPlayers = Array.from(availList.querySelectorAll('li')).map(li => ({
    id: li.dataset.playerId,
    name: li.dataset.playerName,
    color: li.querySelector('.sp-avatar').style.background,
    initial: li.querySelector('.sp-avatar').textContent.trim(),
  }));

  function render() {
    const playingIds = new Set(playing.map(p => p.id));

    // Render playing list
    selList.innerHTML = '';
    playing.forEach((p, i) => {
      const li = document.createElement('li');
      li.className = 'sp-item sp-item--playing';
      li.innerHTML = `
        <span class="sp-turn">${i + 1}</span>
        <span class="avatar sp-avatar" style="background:${p.color}">${p.initial}</span>
        <span class="sp-name">${p.name}</span>
        <button class="sp-reorder" data-id="${p.id}" data-dir="-1" ${i === 0 ? 'disabled' : ''} aria-label="Move up">↑</button>
        <button class="sp-reorder" data-id="${p.id}" data-dir="1" ${i === playing.length - 1 ? 'disabled' : ''} aria-label="Move down">↓</button>
        <button class="sp-remove" data-id="${p.id}" aria-label="Remove">×</button>
      `;
      selList.appendChild(li);
    });

    // Render available list
    availList.innerHTML = '';
    allPlayers.filter(p => !playingIds.has(p.id)).forEach(p => {
      const li = document.createElement('li');
      li.className = 'sp-item sp-item--avail';
      li.dataset.playerId = p.id;
      li.dataset.playerName = p.name;
      li.innerHTML = `
        <span class="avatar sp-avatar" style="background:${p.color}">${p.initial}</span>
        <span class="sp-name">${p.name}</span>
        <span class="sp-add-icon">+</span>
      `;
      availList.appendChild(li);
    });

    // Update counts and empty states
    const n = playing.length;
    playingCount.textContent = n;
    startCount.textContent = n;
    playingEmpty.style.display = n === 0 ? '' : 'none';
    availEmpty.style.display = playingIds.size === allPlayers.length ? '' : 'none';

    if (n === 0) {
      startBtn.disabled = true;
      startBtn.classList.add('disabled');
    } else {
      startBtn.disabled = false;
      startBtn.classList.remove('disabled');
    }

    hiddenInput.value = playing.map(p => p.id).join(',');
  }

  function addPlayer(id) {
    const p = allPlayers.find(x => x.id === id);
    if (p && !playing.find(x => x.id === id)) {
      playing.push(p);
      render();
    }
  }

  function removePlayer(id) {
    playing = playing.filter(p => p.id !== id);
    render();
  }

  function movePlayer(id, dir) {
    const i = playing.findIndex(p => p.id === id);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= playing.length) return;
    const tmp = playing[i]; playing[i] = playing[j]; playing[j] = tmp;
    render();
  }

  // Event delegation on available list
  availList.addEventListener('click', e => {
    const li = e.target.closest('li[data-player-id]');
    if (li) addPlayer(li.dataset.playerId);
  });

  // Event delegation on playing list
  selList.addEventListener('click', e => {
    const removeBtn = e.target.closest('.sp-remove');
    if (removeBtn) { removePlayer(removeBtn.dataset.id); return; }
    const reorderBtn = e.target.closest('.sp-reorder');
    if (reorderBtn) { movePlayer(reorderBtn.dataset.id, parseInt(reorderBtn.dataset.dir)); }
  });

  // Guard form submission
  document.getElementById('selectPlayersForm').addEventListener('submit', e => {
    if (playing.length === 0) {
      e.preventDefault();
      alert('Please select at least one player.');
    }
  });

  render();
})();
```

- [ ] **Step 3: Start the app and manually verify**

```
uv run python app.py
```

Open http://127.0.0.1:5000, pick any game, go to player selection. Verify:
- All players appear in Available list
- Tapping a player moves them to Playing with a turn number
- ↑/↓ buttons reorder; first item's ↑ and last item's ↓ are disabled
- × removes player back to Available
- "Start game" button shows count and is disabled until ≥1 player selected
- "Add New Player" form still works (page reloads with new player in Available)

- [ ] **Step 4: Run tests**

```
uv run python -m unittest discover tests
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add templates/select_players.html static/select_players.js
git commit -m "feat: replace drag-and-drop player selection with touch-native tap-to-move (Option B)"
```

---

## Task 3: Yahtzee Score Entry — Per-Player Tabs

**Files:**
- Modify: `templates/yahtzee.html`
- Modify: `static/yahtzee.js`

The form still POSTs to `/calculate_yahtzee/<game_id>/<player_ids>`. Input names must stay `{player_id}_{category}` (e.g. `1_ones`). All players' inputs live in the DOM; inactive tabs are visually hidden but still submitted.

- [ ] **Step 1: Rewrite yahtzee.html**

Replace the entire content of `templates/yahtzee.html` with:

```html
{% extends 'base.html' %}
{% block content %}

<div class="ytz-page">
  <h2 style="margin:0 0 12px">{{ game['name'] }}</h2>

  <form id="yahtzeeForm" action="{{ url_for('calculate_yahtzee', game_id=game['id'], player_ids=player_ids) }}" method="post">

    <!-- Player tabs -->
    <div class="ytz-tabs" id="ytzTabs">
      {% for player in players %}
      <button type="button"
              class="ytz-tab {% if loop.first %}ytz-tab--active{% endif %}"
              data-player-id="{{ player['id'] }}"
              onclick="ytzSetTab('{{ player['id'] }}')">
        <span class="avatar ytz-tab-avatar" style="background:#1f9d57">{{ player['name'][0].upper() }}</span>
        <span>{{ player['name'] }}</span>
      </button>
      {% endfor %}
    </div>

    {% for player in players %}
    <!-- Panel for {{ player['name'] }} -->
    <div class="ytz-panel {% if not loop.first %}ytz-panel--hidden{% endif %}"
         id="panel-{{ player['id'] }}"
         data-player-id="{{ player['id'] }}">

      <!-- Live total banner -->
      <div class="ytz-banner">
        <div>
          <div class="ytz-banner__label">{{ player['name'] }} · Total</div>
          <div class="ytz-banner__sub">
            Upper <span id="upper-{{ player['id'] }}">0</span> ·
            Bonus <span id="bonus-{{ player['id'] }}">0</span>
          </div>
        </div>
        <div class="ytz-banner__total" id="total-{{ player['id'] }}">0</div>
      </div>

      <!-- Upper section -->
      <div class="ytz-section-label">Upper section</div>
      {% for category in ['Ones', 'Twos', 'Threes', 'Fours', 'Fives', 'Sixes'] %}
      <div class="ytz-row">
        <label class="ytz-row__label" for="{{ player['id'] }}_{{ category.lower() }}">{{ category }}</label>
        <input type="number"
               id="{{ player['id'] }}_{{ category.lower() }}"
               name="{{ player['id'] }}_{{ category.lower() }}"
               class="ytz-input score-input"
               data-player="{{ player['id'] }}"
               data-section="upper"
               inputmode="numeric"
               min="0"
               placeholder="0">
      </div>
      {% endfor %}

      <!-- Lower section -->
      <div class="ytz-section-label" style="margin-top:12px">Lower section</div>
      {% for category in ['One Pair', 'Two Pair', 'Three of a Kind', 'Four of a Kind', 'Full House', 'Small Straight', 'Large Straight', 'Chance', 'Yahtzee'] %}
      <div class="ytz-row">
        <label class="ytz-row__label" for="{{ player['id'] }}_{{ category.lower().replace(' ', '_') }}">{{ category }}</label>
        <input type="number"
               id="{{ player['id'] }}_{{ category.lower().replace(' ', '_') }}"
               name="{{ player['id'] }}_{{ category.lower().replace(' ', '_') }}"
               class="ytz-input score-input"
               data-player="{{ player['id'] }}"
               data-section="lower"
               inputmode="numeric"
               min="0"
               placeholder="0">
      </div>
      {% endfor %}

    </div>
    {% endfor %}

    <div class="sticky-bottom">
      <button type="submit" class="btn-primary-green">Submit Scores</button>
    </div>

  </form>
</div>

<style>
.ytz-page { padding-bottom: 80px; }
.ytz-tabs {
  display: flex; gap: 8px; padding: 0 0 12px;
  overflow-x: auto; -webkit-overflow-scrolling: touch;
  position: sticky; top: 0; background: #fff; z-index: 5; padding-top: 4px;
}
.ytz-tab {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 5px;
  padding: 9px 4px; border-radius: 13px; border: 2px solid #eef1f0;
  background: #fff; cursor: pointer; font: 700 13.5px 'Manrope',sans-serif;
  min-width: 80px; -webkit-tap-highlight-color: transparent; touch-action: manipulation;
}
.ytz-tab--active { border-color: #1f9d57; background: #e7f5ec; }
.ytz-tab-avatar { width: 22px; height: 22px; font-size: 10px; }
.ytz-panel--hidden { display: none; }
.ytz-banner {
  display: flex; align-items: center; justify-content: space-between;
  background: #232b36; border-radius: 16px; padding: 14px 16px; margin-bottom: 12px;
}
.ytz-banner__label { font: 700 12px 'Manrope',sans-serif; color: #9aa9b4; letter-spacing: .04em; text-transform: uppercase; }
.ytz-banner__sub { font: 600 12px 'Manrope',sans-serif; color: #aebac3; margin-top: 4px; }
.ytz-banner__total { font: 800 34px 'Manrope',sans-serif; color: #fff; line-height: 1; }
.ytz-section-label { font: 800 11px 'Manrope',sans-serif; letter-spacing: .1em; color: #9aa3ab; text-transform: uppercase; margin: 0 2px 8px; }
.ytz-row {
  display: flex; align-items: center; gap: 12px;
  background: #fff; border: 1px solid #eef1f0; border-radius: 13px;
  padding: 8px 10px 8px 14px; margin-bottom: 8px;
}
.ytz-row__label { flex: 1; font: 700 14.5px 'Manrope',sans-serif; }
.ytz-input {
  width: 78px; height: 48px; border: 1px solid #e0e5e1; border-radius: 11px;
  text-align: center; font: 700 19px 'Manrope',sans-serif; background: #f7faf8;
  outline: none; flex-shrink: 0;
}
</style>

<script src="{{ url_for('static', filename='yahtzee.js') }}"></script>
{% endblock %}
```

- [ ] **Step 2: Rewrite yahtzee.js**

Replace the entire content of `static/yahtzee.js` with:

```javascript
function ytzSetTab(playerId) {
  // Deactivate all tabs and hide all panels
  document.querySelectorAll('.ytz-tab').forEach(t => t.classList.remove('ytz-tab--active'));
  document.querySelectorAll('.ytz-panel').forEach(p => p.classList.add('ytz-panel--hidden'));

  // Activate selected
  document.querySelector(`.ytz-tab[data-player-id="${playerId}"]`).classList.add('ytz-tab--active');
  document.getElementById(`panel-${playerId}`).classList.remove('ytz-panel--hidden');
}

function ytzRecalc(playerId) {
  let upper = 0, lower = 0;
  document.querySelectorAll(`.score-input[data-player="${playerId}"][data-section="upper"]`).forEach(inp => {
    upper += parseInt(inp.value) || 0;
  });
  document.querySelectorAll(`.score-input[data-player="${playerId}"][data-section="lower"]`).forEach(inp => {
    lower += parseInt(inp.value) || 0;
  });

  const bonus = upper >= 63 ? 35 : 0;
  document.getElementById(`upper-${playerId}`).textContent = upper;
  document.getElementById(`bonus-${playerId}`).textContent = bonus;
  document.getElementById(`total-${playerId}`).textContent = upper + bonus + lower;
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.score-input').forEach(inp => {
    inp.addEventListener('input', () => ytzRecalc(inp.dataset.player));
  });
});
```

- [ ] **Step 3: Manually verify Yahtzee**

```
uv run python app.py
```

Open http://127.0.0.1:5000, start a Yahtzee game with 2+ players. Verify:
- Player tabs appear at top; clicking switches the visible scorecard
- Typing a number updates the live total banner immediately
- Upper ≥ 63 → bonus shows 35; otherwise 0
- All players' fields submit correctly (pick a game with 2 players, enter scores, submit, check confirmation)

- [ ] **Step 4: Run tests**

```
uv run python -m unittest discover tests
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add templates/yahtzee.html static/yahtzee.js
git commit -m "feat: yahtzee score entry redesigned with per-player tabs and touch-friendly inputs"
```

---

## Task 4: Triominos Score Entry — Stepper Cards

**Files:**
- Modify: `templates/triominos.html`

Form POST structure unchanged: `score_<player_id>_<round>` inputs.

- [ ] **Step 1: Rewrite triominos.html**

Replace the entire content of `templates/triominos.html` with:

```html
{% extends 'base.html' %}
{% block content %}

<div class="tri-page">
  <h2 style="margin:0 0 0">{{ game.name }}</h2>

  <form id="triominos-form"
        action="{{ url_for('enter_scores', game_id=game.id, player_ids=player_ids) }}"
        method="POST">

    <!-- Sticky leaderboard -->
    <div class="tri-lead" id="triLead">
      {% for player in players %}
      <div class="tri-lead__card">
        <span class="avatar tri-lead__avatar" style="background:#1f9d57">{{ player.name[0].upper() }}</span>
        <div class="tri-lead__name">{{ player.name }}</div>
        <div class="tri-lead__total" id="total_score_{{ player.id }}">0</div>
      </div>
      {% endfor %}
    </div>

    <!-- Round cards -->
    <div id="triRounds" style="display:flex;flex-direction:column;gap:12px;padding:14px 0 18px">

      <!-- Round 1 (initial) -->
      <div class="tri-round" data-round="1">
        <div class="tri-round__label">Round 1</div>
        {% for player in players %}
        <div class="tri-stepper-row">
          <span class="avatar tri-stepper-avatar" style="background:#1f9d57">{{ player.name[0].upper() }}</span>
          <span class="tri-stepper-name">{{ player.name }}</span>
          <button type="button" class="touch-btn tri-btn-dec"
                  data-player="{{ player.id }}" data-round="1"
                  aria-label="Decrease">−</button>
          <input type="number"
                 name="score_{{ player.id }}_1"
                 id="score_{{ player.id }}_1"
                 class="tri-input"
                 value="0"
                 inputmode="numeric"
                 min="0"
                 data-player="{{ player.id }}">
          <button type="button" class="touch-btn tri-btn-inc"
                  data-player="{{ player.id }}" data-round="1"
                  aria-label="Increase">＋</button>
        </div>
        {% endfor %}
      </div>

    </div>

    <!-- Add round button -->
    <button type="button" id="addRoundBtn" class="tri-add-round">＋ Add round</button>

    <!-- Sticky submit -->
    <div class="sticky-bottom">
      <button type="submit" class="btn-primary-green">Save Scores</button>
    </div>

  </form>
</div>

<style>
.tri-page { padding-bottom: 80px; }
.tri-lead {
  display: flex; gap: 9px; padding: 14px 0;
  position: sticky; top: 0; background: #fff; border-bottom: 1px solid #eef1f0; z-index: 5;
}
.tri-lead__card {
  flex: 1; background: #f6f8f7; border: 1px solid #eef1f0;
  border-radius: 13px; padding: 9px 8px; text-align: center;
}
.tri-lead__avatar { width: 32px; height: 32px; font-size: 14px; margin: 0 auto 6px; }
.tri-lead__name { font: 700 12px 'Manrope',sans-serif; color: #56606c; }
.tri-lead__total { font: 800 21px 'Manrope',sans-serif; margin-top: 1px; }
.tri-round {
  background: #fff; border: 1px solid #eef1f0;
  border-radius: 16px; padding: 13px 13px 14px;
}
.tri-round__label { font: 800 12.5px 'Manrope',sans-serif; letter-spacing:.06em; color:#9aa3ab; text-transform:uppercase; margin-bottom:11px; }
.tri-stepper-row { display: flex; align-items: center; gap: 10px; margin-bottom: 9px; }
.tri-stepper-row:last-child { margin-bottom: 0; }
.tri-stepper-avatar { width: 34px; height: 34px; font-size: 14px; }
.tri-stepper-name { flex: 1; font: 700 14.5px 'Manrope',sans-serif; min-width: 0; }
.tri-btn-dec {
  width: 44px; height: 44px; border-radius: 12px;
  border: 1px solid #e0e5e1; background: #fff; color: #56606c;
  font: 700 22px 'Manrope',sans-serif;
}
.tri-btn-inc {
  width: 44px; height: 44px; border-radius: 12px;
  border: 1px solid #cfe7d9; background: #eef7f1; color: #1f9d57;
  font: 700 22px 'Manrope',sans-serif;
}
.tri-input {
  width: 60px; height: 44px; border: 1px solid #e0e5e1;
  border-radius: 11px; text-align: center;
  font: 800 18px 'Manrope',sans-serif; background: #f7faf8; outline: none;
}
.tri-add-round {
  width: 100%; height: 50px; border-radius: 14px;
  border: 1.5px dashed #c7d0ca; background: #fff; color: #46707d;
  font: 700 15px 'Manrope',sans-serif; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 7px;
  margin-bottom: 12px; -webkit-tap-highlight-color: transparent; touch-action: manipulation;
}
</style>

<script>
(function () {
  const playerIds = {{ players | map(attribute='id') | list | tojson }};
  const playerNames = {{ players | map(attribute='name') | list | tojson }};
  let roundCount = 1;

  function getVal(playerId, round) {
    const el = document.getElementById(`score_${playerId}_${round}`);
    return el ? (parseInt(el.value) || 0) : 0;
  }

  function updateTotals() {
    playerIds.forEach(pid => {
      let total = 0;
      for (let r = 1; r <= roundCount; r++) total += getVal(pid, r);
      const el = document.getElementById(`total_score_${pid}`);
      if (el) el.textContent = total;
    });
  }

  function attachInputListeners(round) {
    playerIds.forEach(pid => {
      const inp = document.getElementById(`score_${pid}_${round}`);
      if (inp) inp.addEventListener('input', updateTotals);
    });
  }

  function attachStepperListeners(round) {
    document.querySelectorAll(`.tri-btn-dec[data-round="${round}"], .tri-btn-inc[data-round="${round}"]`).forEach(btn => {
      btn.addEventListener('click', () => {
        const pid = btn.dataset.player;
        const inp = document.getElementById(`score_${pid}_${round}`);
        if (!inp) return;
        const dir = btn.classList.contains('tri-btn-inc') ? 1 : -1;
        inp.value = Math.max(0, (parseInt(inp.value) || 0) + dir);
        updateTotals();
      });
    });
  }

  document.getElementById('addRoundBtn').addEventListener('click', () => {
    roundCount++;
    const r = roundCount;
    const roundsEl = document.getElementById('triRounds');
    const div = document.createElement('div');
    div.className = 'tri-round';
    div.dataset.round = r;
    let html = `<div class="tri-round__label">Round ${r}</div>`;
    playerIds.forEach((pid, i) => {
      html += `
        <div class="tri-stepper-row">
          <span class="avatar tri-stepper-avatar" style="background:#1f9d57">${playerNames[i][0].toUpperCase()}</span>
          <span class="tri-stepper-name">${playerNames[i]}</span>
          <button type="button" class="touch-btn tri-btn-dec" data-player="${pid}" data-round="${r}" aria-label="Decrease">−</button>
          <input type="number" name="score_${pid}_${r}" id="score_${pid}_${r}" class="tri-input" value="0" inputmode="numeric" min="0" data-player="${pid}">
          <button type="button" class="touch-btn tri-btn-inc" data-player="${pid}" data-round="${r}" aria-label="Increase">＋</button>
        </div>`;
    });
    div.innerHTML = html;
    // Insert before the add-round button
    document.getElementById('addRoundBtn').insertAdjacentElement('beforebegin', div);
    attachInputListeners(r);
    attachStepperListeners(r);
  });

  // Wire up initial round
  attachInputListeners(1);
  attachStepperListeners(1);
  updateTotals();
})();
</script>

{% endblock %}
```

- [ ] **Step 2: Manually verify Triominos**

```
uv run python app.py
```

Open http://127.0.0.1:5000, start Triominos with 2+ players. Verify:
- Sticky leaderboard shows player totals updating live
- − and ＋ buttons change the input value (floor 0)
- Typing directly in the input also updates totals
- "Add round" adds a new round card with all players
- Submitting saves correctly (check confirmation page)

- [ ] **Step 3: Run tests**

```
uv run python -m unittest discover tests
```

- [ ] **Step 4: Commit**

```bash
git add templates/triominos.html
git commit -m "feat: triominos score entry redesigned with sticky leaderboard and stepper buttons"
```

---

## Task 5: Uno Score Entry — Tap Finishing Order

**Files:**
- Modify: `templates/enter_scores.html`

Backend still receives `rank_<player_id>` = integer (1 = first out = winner). No backend change.

- [ ] **Step 1: Rewrite enter_scores.html**

Replace the entire content of `templates/enter_scores.html` with:

```html
{% extends 'base.html' %}
{% block content %}

{% if is_uno %}
<!-- ===== UNO TAP-ORDER UI ===== -->
<div class="uno-page">
  <h2 style="margin:0 0 12px">{{ game['name'] }} · Result</h2>

  <div class="uno-hint">Tap each player in the order they went out. Tap again to clear that spot.</div>

  <div class="uno-section-label">Finishing order</div>

  <div id="unoList" class="uno-list">
    {% for player in players %}
    <div class="uno-item" id="uno-item-{{ player['id'] }}" data-player-id="{{ player['id'] }}">
      <div class="uno-place" id="uno-place-{{ player['id'] }}">·</div>
      <span class="avatar uno-avatar" style="background:#1f9d57">{{ player['name'][0].upper() }}</span>
      <span class="uno-name">{{ player['name'] }}</span>
      <span class="uno-medal" id="uno-medal-{{ player['id'] }}">tap</span>
    </div>
    {% endfor %}
  </div>

  <!-- Hidden inputs for form POST -->
  {% for player in players %}
  <input type="hidden" name="rank_{{ player['id'] }}" id="rank-input-{{ player['id'] }}" form="unoForm">
  {% endfor %}

  <div class="sticky-bottom">
    <form id="unoForm" method="post">
      <button type="submit" id="unoSubmitBtn" class="btn-primary-green disabled" disabled>
        Rank all {{ players|length }} players (<span id="unoRanked">0</span>/{{ players|length }})
      </button>
    </form>
  </div>
</div>

<style>
.uno-page { padding-bottom: 80px; }
.uno-hint {
  background: #eef6f1; border-radius: 14px; padding: 12px 14px;
  margin-bottom: 16px; font: 600 13.5px/1.45 'Manrope',sans-serif; color: #3f6b53;
}
.uno-section-label { font: 800 11.5px 'Manrope',sans-serif; letter-spacing:.1em; color:#9aa3ab; text-transform:uppercase; margin: 0 2px 9px; }
.uno-list { display: flex; flex-direction: column; gap: 9px; }
.uno-item {
  display: flex; align-items: center; gap: 13px;
  padding: 11px 13px; border-radius: 16px;
  border: 2px solid #e6e9e8; background: #fff;
  cursor: pointer; user-select: none;
  -webkit-tap-highlight-color: transparent; touch-action: manipulation;
  min-height: 66px;
}
.uno-item--ranked { border-color: #1f9d57; background: #e7f5ec; }
.uno-place {
  width: 36px; height: 36px; border-radius: 10px;
  border: 2px dashed #cfd6d3; color: #cfd6d3;
  display: flex; align-items: center; justify-content: center;
  font: 800 18px 'Manrope',sans-serif; flex-shrink: 0;
}
.uno-place--ranked { border: none; color: #fff; }
.uno-avatar { width: 42px; height: 42px; font-size: 17px; }
.uno-name { flex: 1; font: 700 16px 'Manrope',sans-serif; }
.uno-medal { font: 600 12px 'Manrope',sans-serif; color: #b6bdc2; }
</style>

<script>
(function () {
  const MEDALS = ['#d9a420', '#9aa6ad', '#bd8a5e'];
  const LABELS = ['1st', '2nd', '3rd'];
  const totalPlayers = {{ players|length }};
  let order = []; // array of player id strings in finishing order

  function render() {
    order.forEach((pid, i) => {
      const item = document.getElementById(`uno-item-${pid}`);
      const place = document.getElementById(`uno-place-${pid}`);
      const medal = document.getElementById(`uno-medal-${pid}`);
      const color = i < 3 ? MEDALS[i] : '#1f9d57';
      item.classList.add('uno-item--ranked');
      place.classList.add('uno-place--ranked');
      place.style.background = color;
      place.textContent = i + 1;
      medal.textContent = i < 3 ? LABELS[i] : '';
      medal.style.color = i < 3 ? MEDALS[i] : '#1f9d57';
      // populate hidden input
      document.getElementById(`rank-input-${pid}`).value = i + 1;
    });

    // Reset unranked items
    document.querySelectorAll('.uno-item').forEach(item => {
      const pid = item.dataset.playerId;
      if (!order.includes(pid)) {
        item.classList.remove('uno-item--ranked');
        const place = document.getElementById(`uno-place-${pid}`);
        place.classList.remove('uno-place--ranked');
        place.style.background = '';
        place.textContent = '·';
        document.getElementById(`uno-medal-${pid}`).textContent = 'tap';
        document.getElementById(`uno-medal-${pid}`).style.color = '#b6bdc2';
        document.getElementById(`rank-input-${pid}`).value = '';
      }
    });

    const n = order.length;
    document.getElementById('unoRanked').textContent = n;
    const btn = document.getElementById('unoSubmitBtn');
    if (n === totalPlayers) {
      btn.disabled = false;
      btn.classList.remove('disabled');
      btn.textContent = 'Save result';
    } else {
      btn.disabled = true;
      btn.classList.add('disabled');
      btn.innerHTML = `Rank all ${totalPlayers} players (<span id="unoRanked">${n}</span>/${totalPlayers})`;
    }
  }

  document.getElementById('unoList').addEventListener('click', e => {
    const item = e.target.closest('.uno-item');
    if (!item) return;
    const pid = item.dataset.playerId;
    const idx = order.indexOf(pid);
    if (idx >= 0) {
      order.splice(idx, 1);
    } else {
      order.push(pid);
    }
    render();
  });

  render();
})();
</script>

{% else %}
<!-- ===== GENERIC SCORE ENTRY (non-Uno) ===== -->
<section class="score-entry">
  <h2>Enter Scores for {{ game['name'] }}</h2>
  <form method="post">
    <table class="score-table">
      <thead>
        <tr>
          <th>Player</th>
          <th>Score</th>
        </tr>
      </thead>
      <tbody>
        {% for player in players %}
        <tr>
          <td>{{ player['name'] }}</td>
          <td><input type="number" name="score_{{ player['id'] }}" min="0" required inputmode="numeric"></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    <button type="submit" class="button">Finalize & Save</button>
  </form>
</section>
{% endif %}

{% endblock %}
```

- [ ] **Step 2: Manually verify Uno**

```
uv run python app.py
```

Start an Uno game with 3+ players. Verify:
- Players appear with dashed · placeholder badges
- Tapping assigns rank 1, 2, 3… in order tapped
- Tapping a ranked player removes them and renumbers those after
- Submit button disabled until all ranked; shows progress count
- Submitting saves correctly (check confirmation page)

- [ ] **Step 3: Run tests**

```
uv run python -m unittest discover tests
```

- [ ] **Step 4: Commit**

```bash
git add templates/enter_scores.html
git commit -m "feat: uno score entry redesigned with tap-to-rank finishing order"
```

---

## Task 6: History — Backend Grouping by session_id

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Update get_score_history() to include session_id**

In `app.py`, find `get_score_history()` (line 97) and replace it with:

```python
def get_score_history():
    conn = get_db_connection()
    rows = query_db(conn, '''
        SELECT
            scores.session_id,
            games.name AS game_name,
            players.name AS player_name,
            scores.score,
            scores.total_score,
            scores.timestamp
        FROM scores
        JOIN games ON scores.game_id = games.id
        JOIN players ON scores.player_id = players.id
        ORDER BY scores.timestamp DESC, scores.total_score DESC NULLS LAST
    ''')
    conn.close()
    return rows
```

- [ ] **Step 2: Update /history route to group rows into sessions**

In `app.py`, find `def history()` (line 248) and replace it with:

```python
@app.route('/history')
def history():
    rows = get_score_history()
    # Group flat rows into session objects
    sessions = []
    seen = {}  # session_id -> index in sessions list
    for row in rows:
        row_dict = dict(row)
        sid = str(row_dict['session_id'])
        ts = row_dict['timestamp'].strftime('%d %b · %H:%M')
        if sid not in seen:
            seen[sid] = len(sessions)
            sessions.append({
                'session_id': sid,
                'game': row_dict['game_name'],
                'when': ts,
                'rows': [],
            })
        sessions[seen[sid]]['rows'].append({
            'name': row_dict['player_name'],
            'score': row_dict['score'],
            'total': row_dict['total_score'],
        })
    # Mark winner per session (highest total_score; skip None)
    for s in sessions:
        valid = [r for r in s['rows'] if r['total'] is not None]
        if valid:
            best = max(valid, key=lambda r: r['total'])
            for r in s['rows']:
                r['win'] = (r is best)
        else:
            for r in s['rows']:
                r['win'] = False
    return render_template('history.html', sessions=sessions)
```

- [ ] **Step 3: Run tests**

```
uv run python -m unittest discover tests
```

Expected: all pass (history route is not tested; game logic tests unaffected).

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: history route groups scores by session_id and marks winner per session"
```

---

## Task 7: History — Session Cards Template

**Files:**
- Modify: `templates/history.html`

- [ ] **Step 1: Rewrite history.html**

Replace the entire content of `templates/history.html` with:

```html
{% extends 'base.html' %}
{% block content %}

<div class="hist-page">
  <h2 style="margin:0 0 0">Score History</h2>

  <!-- Filter chips -->
  <div class="hist-chips" id="histChips">
    <button class="hist-chip hist-chip--active" data-filter="All" onclick="histFilter(this)">All</button>
    <button class="hist-chip" data-filter="Yahtzee" onclick="histFilter(this)">Yahtzee</button>
    <button class="hist-chip" data-filter="Uno" onclick="histFilter(this)">Uno</button>
    <button class="hist-chip" data-filter="Triominos" onclick="histFilter(this)">Triominos</button>
  </div>

  {% if sessions %}
  <div id="histList" style="display:flex;flex-direction:column;gap:13px;padding:14px 0 18px">
    {% for s in sessions %}
    {% set game_lower = s.game | lower %}
    {% if game_lower == 'yahtzee' %}{% set badge_color = '#1f9d57' %}{% set badge_init = 'Y' %}
    {% elif game_lower == 'uno' %}{% set badge_color = '#d6685e' %}{% set badge_init = 'U' %}
    {% elif game_lower == 'triominos' %}{% set badge_color = '#4a7fd6' %}{% set badge_init = 'T' %}
    {% else %}{% set badge_color = '#888' %}{% set badge_init = s.game[0] | upper %}
    {% endif %}
    <div class="hist-card" data-game="{{ s.game }}">
      <!-- Card header -->
      <div class="hist-card__header">
        <div class="hist-badge" style="background:{{ badge_color }}">{{ badge_init }}</div>
        <div class="hist-card__meta">
          <div class="hist-card__game">{{ s.game }}</div>
          <div class="hist-card__when">{{ s.when }}</div>
        </div>
      </div>
      <!-- Player rows -->
      {% for r in s.rows %}
      <div class="hist-row {% if r.win %}hist-row--win{% endif %}">
        <span class="avatar hist-row__avatar" style="background:#1f9d57">{{ r.name[0].upper() }}</span>
        <span class="hist-row__name">{{ r.name }}</span>
        {% if r.win %}<span class="hist-winner-pill">Winner</span>{% endif %}
        <span class="hist-row__score">{{ r.total if r.total is not none else r.score }}</span>
      </div>
      {% endfor %}
    </div>
    {% endfor %}
  </div>
  {% else %}
  <p style="color:#9aa3ab;padding:20px 2px">No scores recorded yet.</p>
  {% endif %}

  <div class="sticky-bottom">
    <a href="{{ url_for('index') }}" class="btn-primary-green" style="background:#fff;color:#232b36;border:1px solid #dde2df">Back to Home</a>
  </div>
</div>

<style>
.hist-page { padding-bottom: 80px; }
.hist-chips {
  display: flex; gap: 8px; padding: 13px 0;
  position: sticky; top: 0; background: #fff; border-bottom: 1px solid #eef1f0;
  z-index: 5; overflow-x: auto; -webkit-overflow-scrolling: touch;
}
.hist-chip {
  padding: 8px 15px; border-radius: 999px;
  font: 700 13.5px 'Manrope',sans-serif; cursor: pointer;
  border: 1px solid #e2e6e3; background: #fff; color: #56606c;
  flex-shrink: 0; -webkit-tap-highlight-color: transparent; touch-action: manipulation;
}
.hist-chip--active { border-color: #232b36; background: #232b36; color: #fff; }
.hist-card {
  background: #fff; border: 1px solid #eef1f0;
  border-radius: 16px; overflow: hidden;
}
.hist-card__header {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 14px; border-bottom: 1px solid #f1f4f3;
}
.hist-badge {
  width: 36px; height: 36px; border-radius: 10px;
  color: #fff; display: flex; align-items: center; justify-content: center;
  font: 800 15px 'Manrope',sans-serif; flex-shrink: 0;
}
.hist-card__game { font: 800 15px 'Manrope',sans-serif; }
.hist-card__when { font: 600 12px 'Manrope',sans-serif; color: #9aa3ab; }
.hist-row {
  display: flex; align-items: center; gap: 11px;
  padding: 9px 14px; background: #fff; border-bottom: 1px solid #f4f6f5;
}
.hist-row:last-child { border-bottom: none; }
.hist-row--win { background: #fffaef; }
.hist-row__avatar { width: 30px; height: 30px; font-size: 12px; }
.hist-row__name { flex: 1; font: 700 14.5px 'Manrope',sans-serif; }
.hist-winner-pill {
  font: 800 10px 'Manrope',sans-serif; letter-spacing:.06em; text-transform:uppercase;
  background: #fdf0d2; color: #b07d12; padding: 3px 8px; border-radius: 999px;
}
.hist-row__score { font: 800 16px 'Manrope',sans-serif; color: #232b36; min-width: 46px; text-align: right; }
</style>

<script>
function histFilter(btn) {
  document.querySelectorAll('.hist-chip').forEach(c => c.classList.remove('hist-chip--active'));
  btn.classList.add('hist-chip--active');
  const filter = btn.dataset.filter;
  document.querySelectorAll('.hist-card').forEach(card => {
    card.style.display = (filter === 'All' || card.dataset.game === filter) ? '' : 'none';
  });
}
</script>

{% endblock %}
```

- [ ] **Step 2: Manually verify History**

```
uv run python app.py
```

Open http://127.0.0.1:5000/history. Verify:
- Sessions appear as cards with game badge, timestamp, player rows
- Winner row has gold "Winner" pill and yellow background
- Filter chips show/hide cards by game (All / Yahtzee / Uno / Triominos)
- "Back to Home" button works

- [ ] **Step 3: Run tests**

```
uv run python -m unittest discover tests
```

- [ ] **Step 4: Commit**

```bash
git add templates/history.html
git commit -m "feat: history redesigned with session cards, filter chips, and winner highlight"
```

---

## Done

All 7 tasks complete. Run the full test suite one final time:

```
uv run python -m unittest discover tests
```

Then do a full end-to-end smoke test on a phone or tablet:
1. Home page → pick a game
2. Player selection: tap to add, reorder, start game
3. Score entry (try Yahtzee, Triominos, Uno)
4. Confirmation page
5. History page: filter by game, verify winner highlight
