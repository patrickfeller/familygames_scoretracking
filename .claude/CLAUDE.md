# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Install dependencies: `uv sync`
- Configure environment: copy `.env.example` to `.env` and set `DATABASE_URL` (Supabase Postgres connection string) and `SECRET_KEY`
- Run the app: `uv run python app.py` (serves at http://127.0.0.1:5000/, Flask debug mode on)
- Run all tests: `uv run python -m unittest discover tests` (runs against the `test` schema in the same Supabase database, see Testing notes)
- Run one test module: `uv run python -m unittest tests.test_game_logic`
- Run a single test: `uv run python -m unittest tests.test_game_logic.TestGameLogic.test_yahtzee_game_calculate_score`
- (Re)initialize the DB schema manually: `uv run python db/init_db.py` (also runs automatically on app startup, against the `public` schema)

## Architecture

### Database
- Supabase Postgres, accessed via `psycopg2` (no more SQLite/`familygame.db`).
- `app.config['DATABASE_URL']` (from the `DATABASE_URL` env var, loaded via `python-dotenv`) is the connection string `get_db_connection()` uses. Locally and in tests this is Supabase's **direct** connection (port 5432); Vercel production uses the **pooled "Transaction" mode** connection (port 6543).
- `query_db(conn, sql, args, one=False)` and `execute_db(conn, sql, args)` in `app.py` are thin `psycopg2` helpers replacing sqlite3's `conn.execute(...).fetchall()` convenience; rows come back as `psycopg2.extras.RealDictCursor` dicts.
- Three tables: `players`, `games`, `scores`. `scores.score` is the per-round/raw value; `scores.total_score` is nullable and holds the computed game total used for ranking/display. `scores.session_id` (UUID, `NOT NULL`) groups all rows from one save into a single "confirmation" view.
- `ensure_games()` in `app.py` seeds the `games` table with `Yahtzee`, `Uno`, `Triominos` on every startup — add new games to its `required_games` list.
- `db/migrate_to_supabase.py` is a one-time script that copied the original local `familygame.db` data into Supabase (preserving IDs and fixing up sequences). Not needed for new setups.

### Request flow (all routes in `app.py`, no blueprints)
1. `/` (`index`) — lists games via `get_games()`; each game's logo file is derived as `static/images/<name-lower>_logo.png`.
2. `/select_players/<game_id>` (`select_players`) — pick/add players; submits a comma-joined `selected_player_ids` to step 3.
3. `/enter_scores/<game_id>?player_ids=...` (`enter_scores`) — dispatches on the game name (lowercased):
   - `yahtzee` → renders `templates/yahtzee.html`, whose form posts to a separate route, `/calculate_yahtzee/<game_id>/<player_ids>`.
   - `triominos` → renders `templates/triominos.html`; POST is handled here via `TriominosGame.process_scores()`.
   - `uno` → renders generic `templates/enter_scores.html` with `is_uno=True`; POST handled here via `UnoGame.process_scores()`.
   - anything else → generic `templates/enter_scores.html`; POST stores raw `score_<player_id>` values directly.
4. `/confirmation/<session_id>` — shows all `scores` rows for that session's UUID.
5. `/history` — full score history joined across `games`/`players`.

### Game logic plugins (`games/`)
Each game is a standalone class (no shared base class); `app.py` imports them ad hoc per route and calls whichever method that game implements:
- `games/yahtzee.py` (`YahtzeeGame.calculate_score(form_data)`) — returns one total (upper section + 35 bonus if upper >= 63 + lower section). Only used by `/calculate_yahtzee`.
- `games/uno.py` (`UnoGame.process_scores(players, form_data)`) — requires a unique integer rank per player; returns `(success, rankings, total_scores, message)`.
- `games/triominos.py` (`TriominosGame.process_scores(players, form_data)`) — sums per-round `score_<player_id>_<round>` fields, ranks players by total (highest wins).

When adding a new game: add its name to `ensure_games()`'s `required_games`, add `static/images/<name>_logo.png`, branch on the lowercased name in `enter_scores`, and add a game class following the `calculate_score` (one-shot total) or `process_scores` (rank + save) pattern.

### Frontend
- Server-rendered Jinja templates extending `templates/base.html`; no JS build step/bundler.
- Per-game client-side behavior lives in `static/<game>.js`, e.g. `yahtzee.js` does live subtotal/bonus/total calculation plus row/column/cell highlighting; `select_players.js` implements drag-and-drop player selection.
- `confetti.browser.min.js` is loaded from a CDN in `base.html`.

## Testing notes
- `tests/test_game_logic.py` runs against a dedicated `test` schema in the same Supabase Postgres database. `setUpClass` creates the `test` schema and runs the shared `init_db(conn)` against it; `app.config['DB_SCHEMA'] = 'test'` makes `get_db_connection()` issue `SET search_path TO test` on every connection it opens.
- `setUp` truncates `players`/`games`/`scores` (in that FK-safe order: `scores` first) in the `test` schema before each test.
- `init_db(conn)` is shared between `db/init_db.py` and the test setup — a single source of truth for the schema, no more keeping two definitions in sync.
- Importing `app` still runs `init_db()`/`ensure_games()` at module load time against the real `public` schema (before any test overrides `DB_SCHEMA`) — harmless and idempotent, same as before.
