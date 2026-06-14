# Vercel + Supabase Deployment — Design

## Goal

Deploy the Flask app to Vercel as a serverless function, with Supabase
Postgres replacing the local SQLite database (`familygame.db`) — for
production, local development, and tests alike.

## Architecture Overview

- `sqlite3` → `psycopg2`. SQL stays mostly the same (raw queries), with
  syntax adapted: `?` → `%s` placeholders, schema rewritten as Postgres DDL.
- One database backend everywhere: dev, tests (isolated `test` schema), and
  production all connect to the same Supabase Postgres instance via a
  `DATABASE_URL` env var (different values per environment — see below).
- `app.py` remains the single Flask entry point. A `vercel.json` is added so
  Vercel can run it as a serverless function; no `api/` restructuring.
- A one-time migration script copies existing `familygame.db` data
  (players/games/scores) into Supabase, preserving IDs and fixing up
  sequences afterwards.

Two phases:
1. **DB layer migration** — Postgres schema, `app.py` rewrite, data
   migration script, test suite against a `test` schema.
2. **Vercel deployment config** — `vercel.json`, dependencies, env var docs.

## 1. Database Schema (`db/init_db.py`)

Rewritten for Postgres with idempotent `CREATE TABLE IF NOT EXISTS`. The old
SQLite `ALTER TABLE ADD COLUMN` try/except hacks are removed — this is a
fresh schema so `total_score` and `session_id` are defined directly:

```sql
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS games (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS scores (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    score INTEGER NOT NULL,
    total_score INTEGER,
    session_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

`init_db()` is refactored to take an open connection and just run this DDL
(see "Test Suite" below for why — it's reused for the `test` schema, fixing
the current duplication between `db/init_db.py` and
`tests/test_game_logic.py::create_test_tables()`).

## 2. Connection Layer (`app.py`)

`psycopg2` replaces `sqlite3`:

- `get_db_connection()` connects via `psycopg2.connect(DATABASE_URL)`. If
  `app.config['DB_SCHEMA']` is set, it runs `SET search_path TO <schema>`
  right after connecting (used by tests; unset in dev/prod → `public`).
- Two small helpers replace the `conn.execute(...).fetchall()` convenience
  that `sqlite3` offered directly on the connection object:

  ```python
  def query_db(conn, query, args=(), one=False):
      cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
      cur.execute(query, args)
      rv = cur.fetchall()
      cur.close()
      return (rv[0] if rv else None) if one else rv

  def execute_db(conn, query, args=()):
      cur = conn.cursor()
      cur.execute(query, args)
      cur.close()
  ```

  `RealDictCursor` returns dict-like rows, so existing `dict(row)` and
  `row['id']`-style access throughout `app.py` and the game logic plugins
  keep working unchanged.
- All `?` placeholders become `%s`. Dynamic `IN (...)` clauses build with
  `','.join(['%s'] * n)` instead of `'?' * n`.
- **`history()` fix**: psycopg2 returns real `datetime` objects for
  `TIMESTAMP` columns (not strings like SQLite). The `strptime` parse step is
  removed; `row_dict['timestamp']` is formatted directly via
  `.strftime('%d.%m.%Y %H:%M')`.
- `init_db()` and `ensure_games()` keep running at app import time, same as
  today — idempotent and cheap enough for this traffic level.
- `SECRET_KEY` env var handling is unchanged in code; production deployments
  must set a real `SECRET_KEY` in Vercel (see env var summary below).

### Connection string (`DATABASE_URL`)

- **Local dev & tests**: Supabase **direct** connection (port 5432). Needed
  because `SET search_path` (used for test isolation) is a session-level
  feature that doesn't reliably work through PgBouncer transaction-mode
  pooling.
- **Vercel production**: Supabase **pooled** connection string (port 6543,
  "Transaction" mode). Recommended because each request opens/closes a
  connection (same pattern as today), and serverless functions can spin up
  many concurrent connections quickly.

Both are the *same env var name* (`DATABASE_URL`) with different values per
environment — standard practice, no code branching needed.

## 3. Data Migration Script (`db/migrate_to_supabase.py`)

One-time script, run locally after the Postgres schema exists on Supabase:

1. Connects to both the local `familygame.db` (SQLite) and Supabase
   (`DATABASE_URL`, direct connection).
2. `TRUNCATE players, games, scores RESTART IDENTITY CASCADE` on the Supabase
   side first — guards against ID collisions if `ensure_games()` already
   inserted `Yahtzee`/`Uno`/`Triominos` with different IDs during earlier
   testing against Supabase.
3. Copies `players`, `games`, `scores` row-by-row, **preserving original
   IDs** so `scores.player_id` / `scores.game_id` foreign keys stay valid.
4. Any `scores` row with `session_id IS NULL` (possible leftover from before
   that column existed in SQLite) gets a freshly generated UUID, since the
   new schema makes the column `NOT NULL`.
5. After all inserts, resets the `SERIAL` sequences, e.g.:
   `SELECT setval('players_id_seq', (SELECT MAX(id) FROM players))` — and
   the same for `games_id_seq` and `scores_id_seq`.

**Run order for first deploy**: create schema (`db/init_db.py` against
Supabase) → run migration script → then start/deploy the app.

## 4. Test Suite (`tests/test_game_logic.py`)

- Tests connect to the same Supabase Postgres (`DATABASE_URL`, direct
  connection), but operate inside a dedicated `test` schema for isolation
  from real data.
- `setUpClass`/`setUp` set `app.config['DB_SCHEMA'] = 'test'`, so
  `get_db_connection()` issues `SET search_path TO test` after connecting.
- `create_test_tables()` runs `CREATE SCHEMA IF NOT EXISTS test`, then calls
  the shared `init_db(conn)` against that schema — eliminating the schema
  duplication the current code has between `db/init_db.py` and
  `create_test_tables()`.
- `setUp()` truncates `players`/`games`/`scores` in the `test` schema before
  each test (replaces today's `DELETE FROM ...`).
- Same caveat as today: importing `app` still runs `init_db()` /
  `ensure_games()` against the real `public` schema once at module load (now
  against Supabase instead of the local SQLite file) — harmless and
  idempotent, just as it is now.

## 5. Vercel Deployment Config

- **`vercel.json`** — routes all requests to `app.py` via `@vercel/python`.
  Flask continues to serve `/static/*` and render templates itself (simplest
  option for this traffic level; no separate static-asset routing).
- **`requirements.txt`** — generated from `pyproject.toml`/`uv.lock` (e.g.
  `uv export --no-hashes --format requirements-txt`), since Vercel's Python
  builder expects it. New dependencies: `psycopg2-binary`, `python-dotenv`.
- **`.python-version`** stays at `3.11` — supported by Vercel's Python
  runtime, no change needed.
- **Local dev**: `.env` (gitignored) + `.env.example` documenting
  `DATABASE_URL` (direct connection) and `SECRET_KEY`. `python-dotenv` loads
  `.env` near the top of `app.py`.
- **README** updated with the new setup flow: create Supabase schema → run
  migration script → configure `.env` → `uv sync` → run/test locally →
  deployment notes for Vercel env vars.
- The local `familygame.db` SQLite file becomes unused after migration
  (already gitignored; can be deleted once migration is verified).

## Environment Variables Summary

| Var | Local (`.env`) | Vercel (production) |
|---|---|---|
| `DATABASE_URL` | Supabase direct connection (port 5432) | Supabase pooled connection (port 6543, transaction mode) |
| `SECRET_KEY` | any dev value | a real secret, set in Vercel dashboard |

`DATABASE_URL` and `SECRET_KEY` for Vercel must be set manually in the Vercel
project dashboard (Project Settings → Environment Variables) — this is a
manual step for the user, not something the implementation can automate.

## Out of Scope / Follow-ups

- No ORM/SQLAlchemy — raw SQL via `psycopg2` stays, matching the existing
  architecture.
- No use of the Supabase REST client or Row Level Security policies — the
  app connects directly to Postgres with a database role, bypassing
  PostgREST/RLS entirely (same trust model as the current single-file
  SQLite app).
- Static asset serving via Vercel's CDN/edge routing (rather than through
  the Flask function) is not part of this design; can be revisited later if
  performance becomes a concern.
- Deleting the now-unused `familygame.db` file and its `.gitignore` entry is
  left as a manual cleanup step after migration is verified.
