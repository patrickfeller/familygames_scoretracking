# Fullscreen Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a header button, present on every page, that toggles native browser fullscreen (Fullscreen API) on/off.

**Architecture:** A single icon button lives in `templates/base.html`'s `<header>`, styled in `static/style.css`. A new global script `static/main.js` (loaded from `base.html`, `defer`) feature-detects `document.documentElement.requestFullscreen`, unhides the button only when supported, and toggles fullscreen via `requestFullscreen()` / `exitFullscreen()`. The button's `aria-pressed` attribute drives an SVG icon swap (expand ⇄ compress) purely in CSS, kept in sync with the real fullscreen state via the `fullscreenchange` event (so it also updates if the user exits with Esc).

**Tech Stack:** Vanilla JS (no build step, matches `select_players.js`/`yahtzee.js`), plain CSS, inline SVG icons (no external assets/network calls).

## Global Constraints

- No new dependencies, no build step — project has no `package.json`/JS tooling (confirmed: none present).
- Fullscreen API is **not supported for arbitrary elements in iOS Safari** (only `<video>`). The button must feature-detect and stay `hidden` on unsupported browsers rather than throw or show a dead control.
- Must not break the existing DB-backed Flask test client tests in `tests/test_game_logic.py` (uses `test` schema, `WTF_CSRF_ENABLED = False`).
- Follow existing template convention: page-specific scripts are plain `<script src="...">` tags with `url_for('static', filename=...)`, no inline JS in templates.

---

### Task 1: Fullscreen toggle button markup + styling

**Files:**
- Modify: `templates/base.html:13-27` (header block)
- Modify: `static/style.css:12-41` (header/nav rules)
- Test: `tests/test_game_logic.py` (add one method to existing `TestGameLogic`)

**Interfaces:**
- Produces: a `<button id="fullscreenToggle" class="fullscreen-toggle" aria-pressed="false" hidden>` element in every rendered page (via `base.html`), containing two inline `<svg>` children with classes `icon-expand` and `icon-compress`. Task 2's `main.js` looks up this exact `id` and toggles `hidden`/`aria-pressed` on it.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_game_logic.py`, inside `class TestGameLogic` (anywhere after `setUp`):

```python
    def test_base_template_includes_fullscreen_toggle(self):
        response = self.app.get('/')
        self.assertIn(b'id="fullscreenToggle"', response.data)
        self.assertIn(b'aria-pressed="false"', response.data)
        self.assertIn(b'main.js', response.data)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_game_logic.TestGameLogic.test_base_template_includes_fullscreen_toggle -v`
Expected: FAIL — `AssertionError: b'id="fullscreenToggle"' not found in ...`

- [ ] **Step 3: Add the button markup to `base.html`**

Replace the `<header>` block (`templates/base.html:13-27`):

```html
    <header>
        <button type="button" id="fullscreenToggle" class="fullscreen-toggle" aria-label="Enter fullscreen" aria-pressed="false" hidden>
            <svg class="icon-expand" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M8 3H5a2 2 0 0 0-2 2v3"/>
                <path d="M21 8V5a2 2 0 0 0-2-2h-3"/>
                <path d="M3 16v3a2 2 0 0 0 2 2h3"/>
                <path d="M16 21h3a2 2 0 0 0 2-2v-3"/>
            </svg>
            <svg class="icon-compress" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M8 3v3a2 2 0 0 1-2 2H3"/>
                <path d="M21 8h-3a2 2 0 0 1-2-2V3"/>
                <path d="M3 16h3a2 2 0 0 1 2 2v3"/>
                <path d="M16 21v-3a2 2 0 0 1 2-2h3"/>
            </svg>
        </button>
        <h1>Family Game Score Tracker</h1>
        <nav>
            <a href="{{ url_for('index') }}">Home</a>
            <a href="{{ url_for('history') }}">Score History</a>
            <a href="{{ url_for('ranking') }}">Rankings</a>
            {% if session.get('authenticated') %}
            <form method="post" action="{{ url_for('logout') }}" style="display:inline">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <button type="submit" class="nav-logout">Logout</button>
            </form>
            {% endif %}
        </nav>
    </header>
```

Also add the deferred script tag in `<head>` (after `templates/base.html:10`, right after the `style.css` link):

```html
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <script src="{{ url_for('static', filename='main.js') }}" defer></script>
```

- [ ] **Step 4: Add styling to `static/style.css`**

Modify the header rule at `static/style.css:12-18` to add `position: relative` (anchor for the absolutely-positioned button):

```css
header {
    background-color: #2c3e50;
    color: #ecf0f1;
    padding: 15px 0;
    text-align: center;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    position: relative;
}
```

Then append after the `nav a:hover` rule (`static/style.css:39-41`):

```css
.fullscreen-toggle {
    position: absolute;
    top: 15px;
    right: 15px;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 1px solid rgba(236, 240, 241, 0.4);
    border-radius: 8px;
    color: #ecf0f1;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
}

.fullscreen-toggle:hover {
    background: rgba(236, 240, 241, 0.15);
}

.fullscreen-toggle[hidden] {
    display: none;
}

.fullscreen-toggle .icon-compress {
    display: none;
}

.fullscreen-toggle[aria-pressed="true"] .icon-expand {
    display: none;
}

.fullscreen-toggle[aria-pressed="true"] .icon-compress {
    display: block;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run python -m unittest tests.test_game_logic.TestGameLogic.test_base_template_includes_fullscreen_toggle -v`
Expected: PASS

Note: the button stays `hidden` via the HTML attribute until Task 2's script removes it — this is expected and intentional (no-JS / unsupported-browser fallback is "no button" rather than a dead button).

- [ ] **Step 6: Commit**

```bash
git add templates/base.html static/style.css tests/test_game_logic.py
git commit -m "feat: add fullscreen toggle button markup and styling"
```

---

### Task 2: Fullscreen toggle behavior (`main.js`)

**Files:**
- Create: `static/main.js`

**Interfaces:**
- Consumes: `#fullscreenToggle` button and its `.icon-expand`/`.icon-compress` children, produced by Task 1.
- Produces: nothing consumed by later tasks — this is the final piece of the feature.

- [ ] **Step 1: Write `static/main.js`**

```javascript
(function () {
    var btn = document.getElementById('fullscreenToggle');
    if (!btn) {
        return;
    }

    var supportsFullscreen = !!(document.documentElement.requestFullscreen);
    if (!supportsFullscreen) {
        return;
    }

    btn.hidden = false;

    function isFullscreen() {
        return !!document.fullscreenElement;
    }

    function updateButtonState() {
        var active = isFullscreen();
        btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        btn.setAttribute('aria-label', active ? 'Exit fullscreen' : 'Enter fullscreen');
    }

    btn.addEventListener('click', function () {
        if (isFullscreen()) {
            document.exitFullscreen();
        } else {
            document.documentElement.requestFullscreen().catch(function () {
                // User gesture requirement not met, or denied by browser — no-op.
            });
        }
    });

    document.addEventListener('fullscreenchange', updateButtonState);

    updateButtonState();
})();
```

There is no failing-test step here: the project has no JS test runner (`package.json` absent, confirmed in Global Constraints), and `document.documentElement.requestFullscreen()` requires a real browser + user gesture, which `unittest`/Flask's test client cannot exercise. Verification is manual (Step 2).

- [ ] **Step 2: Manually verify in a real browser**

Run: `uv run python app.py`

Open `http://127.0.0.1:5000/` in a desktop browser (Chrome or Firefox — both support the Fullscreen API on arbitrary elements; Safari on iOS will correctly hide the button per the Global Constraints note).

Check:
- Toggle button is visible top-right of the header.
- Click it → page enters fullscreen (browser chrome/tab bar hidden), icon swaps from expand to compress, `aria-label` becomes "Exit fullscreen".
- Click it again → exits fullscreen, icon reverts, `aria-label` becomes "Enter fullscreen".
- Press `Esc` while fullscreen → browser exits fullscreen natively, and the icon still reverts correctly (confirms the `fullscreenchange` listener, not just the click handler, drives the icon state).
- Navigate to another page (e.g. History) while fullscreen is inactive → button still present and working (confirms it's wired in `base.html`, not a page-specific template).

- [ ] **Step 3: Commit**

```bash
git add static/main.js
git commit -m "feat: wire fullscreen toggle behavior"
```

---

## Self-Review Notes

- **Spec coverage:** button toggles native fullscreen (Task 2), placed in header on all pages (Task 1 modifies shared `base.html`), adjustments to existing CSS (`header { position: relative }`) and new script wiring are both covered.
- **iOS Safari limitation:** called out in Global Constraints and re-verified as a manual-check expectation in Task 2 Step 2, rather than silently ignored.
- **No placeholders:** every step has complete, runnable code — no TBD/"add error handling" style gaps.
- **Type/name consistency:** `#fullscreenToggle` id and `icon-expand`/`icon-compress` classes are identical across Task 1 (HTML/CSS) and Task 2 (JS `getElementById('fullscreenToggle')`).
