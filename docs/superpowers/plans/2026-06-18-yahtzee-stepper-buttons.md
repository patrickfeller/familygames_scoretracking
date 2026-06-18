# Yahtzee Stepper Buttons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add +/− stepper buttons to every Yahtzee score input that cycle only through valid values defined in `docs/superpowers/specs/yahtzee_spec.json`.

**Architecture:** Each `<input>` in `yahtzee.html` gets a − button before and a + button after. A JS map (`VALID_VALUES`) holds the allowed values per category (arrays for discrete sets, expanded ranges for min/max specs). Buttons cycle through that array; manual input is validated on blur to snap to the nearest valid value.

**Tech Stack:** Jinja2 templates, vanilla JS, CSS

## Global Constraints

- Valid values come from `docs/superpowers/specs/yahtzee_spec.json` — hardcoded into JS as a constant (no runtime fetch)
- Every category implicitly allows `0` (un-scored)
- Array-type categories (e.g. Ones `[1,2,3,4,5]`): valid set is `[0, ...specValues]`
- Range-type categories (e.g. Two Pair `{min:6, max:22}`): valid set is `[0, 6, 7, 8, ..., 22]`
- Stepper buttons must not submit the form (all `type="button"`)
- Reuse the visual style of Triominos stepper buttons but with `ytz-` prefixed class names

---

### Task 1: Add stepper buttons to yahtzee template + CSS

**Files:**
- Modify: `templates/yahtzee.html:42-72` (both upper and lower `{% for %}` loops)
- Modify: `static/style.css:534-537` (after existing `.ytz-row` rules)

**Interfaces:**
- Consumes: nothing
- Produces: `data-category` attribute on every `.score-input`; `.ytz-btn-dec` and `.ytz-btn-inc` buttons with `data-player` and `data-category` attributes that Task 2's JS hooks into

- [ ] **Step 1: Add `data-category` + stepper buttons to upper section loop**

In `templates/yahtzee.html`, replace lines 42–55 (the upper section `{% for %}` block):

```html
      {% for category in ['Ones', 'Twos', 'Threes', 'Fours', 'Fives', 'Sixes'] %}
      <div class="ytz-row">
        <label class="ytz-row__label" for="{{ player['id'] }}_{{ category.lower() }}">{{ category }}</label>
        <button type="button" class="touch-btn ytz-btn-dec"
                data-player="{{ player['id'] }}" data-category="{{ category.lower() }}"
                aria-label="Decrease {{ category }}">−</button>
        <input type="number"
               id="{{ player['id'] }}_{{ category.lower() }}"
               name="{{ player['id'] }}_{{ category.lower() }}"
               class="ytz-input score-input"
               data-player="{{ player['id'] }}"
               data-section="upper"
               data-category="{{ category.lower() }}"
               inputmode="numeric"
               min="0"
               placeholder="0">
        <button type="button" class="touch-btn ytz-btn-inc"
                data-player="{{ player['id'] }}" data-category="{{ category.lower() }}"
                aria-label="Increase {{ category }}">＋</button>
      </div>
      {% endfor %}
```

- [ ] **Step 2: Add `data-category` + stepper buttons to lower section loop**

In `templates/yahtzee.html`, replace lines 58–72 (the lower section `{% for %}` block):

```html
      {% for category in ['One Pair', 'Two Pair', 'Three of a Kind', 'Four of a Kind', 'Full House', 'Small Straight', 'Large Straight', 'Chance', 'Yahtzee'] %}
      <div class="ytz-row">
        <label class="ytz-row__label" for="{{ player['id'] }}_{{ category.lower().replace(' ', '_') }}">{{ category }}</label>
        <button type="button" class="touch-btn ytz-btn-dec"
                data-player="{{ player['id'] }}" data-category="{{ category.lower().replace(' ', '_') }}"
                aria-label="Decrease {{ category }}">−</button>
        <input type="number"
               id="{{ player['id'] }}_{{ category.lower().replace(' ', '_') }}"
               name="{{ player['id'] }}_{{ category.lower().replace(' ', '_') }}"
               class="ytz-input score-input"
               data-player="{{ player['id'] }}"
               data-section="lower"
               data-category="{{ category.lower().replace(' ', '_') }}"
               inputmode="numeric"
               min="0"
               placeholder="0">
        <button type="button" class="touch-btn ytz-btn-inc"
                data-player="{{ player['id'] }}" data-category="{{ category.lower().replace(' ', '_') }}"
                aria-label="Increase {{ category }}">＋</button>
      </div>
      {% endfor %}
```

- [ ] **Step 3: Add CSS for ytz stepper buttons**

In `static/style.css`, add after the existing `.ytz-row .ytz-input` rule (after line 537):

```css
.ytz-btn-dec { width: 44px; height: 44px; border-radius: 12px; border: 1px solid #e0e5e1; background: #fff; color: #56606c; font: 700 22px 'Manrope',sans-serif; padding: 0; flex-shrink: 0; }
.ytz-btn-inc { width: 44px; height: 44px; border-radius: 12px; border: 1px solid #cfe7d9; background: #eef7f1; color: #1f9d57; font: 700 22px 'Manrope',sans-serif; padding: 0; flex-shrink: 0; }
```

- [ ] **Step 4: Verify layout renders correctly**

Run: `uv run python app.py`

Open browser → pick Yahtzee → select a player → verify:
- Each score row shows: label, − button, input, + button
- Buttons are styled (grey −, green +)
- Layout doesn't overflow on mobile-width viewport (375px)
- Buttons don't submit the form when clicked

Expected: buttons visible, non-functional (JS not wired yet)

- [ ] **Step 5: Commit**

```bash
git add templates/yahtzee.html static/style.css
git commit -m "feat(yahtzee): add stepper buttons to score inputs"
```

---

### Task 2: Add stepper JS logic with valid-value constraints

**Files:**
- Modify: `static/yahtzee.js` (add valid-values map, stepper function, blur validation, event wiring)

**Interfaces:**
- Consumes: `.ytz-btn-dec` / `.ytz-btn-inc` buttons with `data-player` and `data-category` attributes (from Task 1); `.score-input` elements with `data-category` attribute (from Task 1)
- Produces: `ytzStep(playerId, category, direction)` function; stepper click handlers; blur validation on all `.score-input` fields

- [ ] **Step 1: Add VALID_VALUES constant and helper**

At the top of `static/yahtzee.js`, before the existing `ytzSetTab` function, add:

```js
const seq = (a, b) => Array.from({length: b - a + 1}, (_, i) => a + i);

const VALID_VALUES = {
  ones:              [0, 1, 2, 3, 4, 5],
  twos:              [0, 2, 4, 6, 8, 10],
  threes:            [0, 3, 6, 9, 12, 15],
  fours:             [0, 4, 8, 12, 16, 20],
  fives:             [0, 5, 10, 15, 20, 25],
  sixes:             [0, 6, 12, 18, 24, 30],
  one_pair:          [0, 2, 4, 6, 8, 10, 12],
  two_pair:          [0, ...seq(6, 22)],
  three_of_a_kind:   [0, 3, 6, 9, 12, 15, 18],
  four_of_a_kind:    [0, 4, 8, 12, 16, 20, 24],
  full_house:        [0, 25, 30],
  small_straight:    [0, 30, 35],
  large_straight:    [0, 40, 45],
  chance:            [0, ...seq(5, 30)],
  yahtzee:           [0, 50, 55],
};
```

- [ ] **Step 2: Add ytzStep and snapToValid functions**

After the `VALID_VALUES` constant, add:

```js
function snapToValid(category, value) {
  const values = VALID_VALUES[category];
  if (!values) return value;
  if (values.includes(value)) return value;
  return values.reduce((best, v) => {
    const d1 = Math.abs(best - value), d2 = Math.abs(v - value);
    return d2 < d1 || (d2 === d1 && v > best) ? v : best;
  }, values[0]);
}

function ytzStep(playerId, category, direction) {
  const input = document.getElementById(`${playerId}_${category}`);
  if (!input) return;
  const values = VALID_VALUES[category];
  if (!values) return;

  const current = parseInt(input.value) || 0;
  let idx = values.indexOf(current);
  if (idx === -1) {
    idx = values.reduce((best, v, i) =>
      Math.abs(v - current) < Math.abs(values[best] - current) ? i : best, 0);
  }
  const newIdx = Math.max(0, Math.min(idx + direction, values.length - 1));
  input.value = values[newIdx];
  ytzRecalc(playerId);
}
```

- [ ] **Step 3: Wire up stepper click handlers and blur validation**

Inside the existing `document.addEventListener('DOMContentLoaded', function () { ... })` block in `yahtzee.js`, after the existing `.score-input` `input` listener loop, add:

```js
  // Stepper buttons
  document.querySelectorAll('.ytz-btn-dec, .ytz-btn-inc').forEach(btn => {
    btn.addEventListener('click', () => {
      const dir = btn.classList.contains('ytz-btn-inc') ? 1 : -1;
      ytzStep(btn.dataset.player, btn.dataset.category, dir);
    });
  });

  // Snap manual input to nearest valid value on blur
  document.querySelectorAll('.score-input').forEach(inp => {
    inp.addEventListener('blur', () => {
      if (inp.value === '') return;
      const cat = inp.dataset.category;
      const val = parseInt(inp.value) || 0;
      const snapped = snapToValid(cat, val);
      if (snapped !== val) inp.value = snapped;
      ytzRecalc(inp.dataset.player);
    });
  });
```

- [ ] **Step 4: Verify the complete yahtzee.js file**

The full `static/yahtzee.js` should now be:

```js
const seq = (a, b) => Array.from({length: b - a + 1}, (_, i) => a + i);

const VALID_VALUES = {
  ones:              [0, 1, 2, 3, 4, 5],
  twos:              [0, 2, 4, 6, 8, 10],
  threes:            [0, 3, 6, 9, 12, 15],
  fours:             [0, 4, 8, 12, 16, 20],
  fives:             [0, 5, 10, 15, 20, 25],
  sixes:             [0, 6, 12, 18, 24, 30],
  one_pair:          [0, 2, 4, 6, 8, 10, 12],
  two_pair:          [0, ...seq(6, 22)],
  three_of_a_kind:   [0, 3, 6, 9, 12, 15, 18],
  four_of_a_kind:    [0, 4, 8, 12, 16, 20, 24],
  full_house:        [0, 25, 30],
  small_straight:    [0, 30, 35],
  large_straight:    [0, 40, 45],
  chance:            [0, ...seq(5, 30)],
  yahtzee:           [0, 50, 55],
};

function snapToValid(category, value) {
  const values = VALID_VALUES[category];
  if (!values) return value;
  if (values.includes(value)) return value;
  return values.reduce((best, v) => {
    const d1 = Math.abs(best - value), d2 = Math.abs(v - value);
    return d2 < d1 || (d2 === d1 && v > best) ? v : best;
  }, values[0]);
}

function ytzStep(playerId, category, direction) {
  const input = document.getElementById(`${playerId}_${category}`);
  if (!input) return;
  const values = VALID_VALUES[category];
  if (!values) return;

  const current = parseInt(input.value) || 0;
  let idx = values.indexOf(current);
  if (idx === -1) {
    idx = values.reduce((best, v, i) =>
      Math.abs(v - current) < Math.abs(values[best] - current) ? i : best, 0);
  }
  const newIdx = Math.max(0, Math.min(idx + direction, values.length - 1));
  input.value = values[newIdx];
  ytzRecalc(playerId);
}

function ytzSetTab(playerId) {
  document.querySelectorAll('.ytz-tab').forEach(t => t.classList.remove('ytz-tab--active'));
  document.querySelectorAll('.ytz-panel').forEach(p => p.classList.add('ytz-panel--hidden'));

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

  // Stepper buttons
  document.querySelectorAll('.ytz-btn-dec, .ytz-btn-inc').forEach(btn => {
    btn.addEventListener('click', () => {
      const dir = btn.classList.contains('ytz-btn-inc') ? 1 : -1;
      ytzStep(btn.dataset.player, btn.dataset.category, dir);
    });
  });

  // Snap manual input to nearest valid value on blur
  document.querySelectorAll('.score-input').forEach(inp => {
    inp.addEventListener('blur', () => {
      if (inp.value === '') return;
      const cat = inp.dataset.category;
      const val = parseInt(inp.value) || 0;
      const snapped = snapToValid(cat, val);
      if (snapped !== val) inp.value = snapped;
      ytzRecalc(inp.dataset.player);
    });
  });
});
```

- [ ] **Step 5: Manual testing**

Run: `uv run python app.py`

Open browser → Yahtzee → select player(s) → verify:

1. **Ones row:** click + → shows 1, 2, 3, 4, 5; click + at 5 → stays 5; click − → 4, 3, 2, 1, 0; click − at 0 → stays 0
2. **Sixes row:** click + → shows 6, 12, 18, 24, 30; values skip non-multiples
3. **Two Pair row:** click + → shows 6, 7, 8, ..., 22; every integer in range
4. **Full House row:** click + → shows 25, 30; only two non-zero values
5. **Yahtzee row:** click + → shows 50, 55
6. **Blur validation:** type "7" in Fours, click elsewhere → snaps to 8
7. **Blur validation:** type "3" in Two Pair, click elsewhere → snaps to 0 (nearest)
8. **Live totals:** steppers update the banner total in real time
9. **Multi-player:** switch tabs, verify stepper works per-player independently
10. **Submit:** fill in some values via steppers, submit → scores saved correctly

- [ ] **Step 6: Commit**

```bash
git add static/yahtzee.js
git commit -m "feat(yahtzee): add stepper logic with valid-value constraints per spec"
```
