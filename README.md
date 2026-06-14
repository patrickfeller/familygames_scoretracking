# Family Game Score Tracker

A modern, extensible web application to track scores for family games (starting with Yahtzee) using Flask, Jinja2, and Supabase Postgres.

## Features
- Select from available games (easily extensible for more games)
- Add/select players from a persistent database
- Enter and save scores for each session
- Modern, responsive UI
- Data stored in Supabase Postgres for persistence

## Project Structure
```
familygame_scoretracking/
├── app.py
├── db/
│   ├── init_db.py
│   └── migrate_to_supabase.py
├── games/
├── static/
├── templates/
├── tests/
├── vercel.json
├── requirements.txt
└── README.md
```

## Setup Instructions

1. **Clone the repository**

2. **Install dependencies**
   ```
   uv sync
   ```

3. **Configure environment**

   Copy `.env.example` to `.env` and fill in:
   - `DATABASE_URL` — your Supabase Postgres **direct** connection string (Project Settings → Database → Connection string, port 5432)
   - `SECRET_KEY` — any value for local development

4. **Initialize the database schema**
   ```
   uv run python db/init_db.py
   ```
   This creates the `players`, `games`, and `scores` tables in Supabase if they don't exist. It also runs automatically on app startup.

5. **(Optional) Migrate existing local data**

   If you have an existing `familygame.db` SQLite file with data you want to keep:
   ```
   uv run python db/migrate_to_supabase.py
   ```

6. **Run the application**
   ```
   uv run python app.py
   ```
   The app will be available at [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## Running Tests

```
uv run python -m unittest discover tests
```

Tests run against a dedicated `test` schema in the same Supabase database — make sure `DATABASE_URL` is set in `.env`.

## Deploying to Vercel

1. Push this repository to the Git provider connected to your Vercel project.
2. In the Vercel project's Environment Variables settings, add:
   - `DATABASE_URL` — your Supabase **pooled "Transaction" mode** connection string (port 6543)
   - `SECRET_KEY` — a real secret value
3. Vercel will build and deploy using `vercel.json` and `requirements.txt`.

## Usage
- Select a game from the home page
- Select existing players or add new ones
- Enter scores for each player and save the session
- Confirmation will be shown after saving

## Extending for More Games
- Add new games by inserting them into the `games` table (see `ensure_games()` in `app.py`)
- The app is designed to support multiple games via the `game_id` field
- For custom scoring logic or UI, add new templates and route logic as needed

## License
MIT License
