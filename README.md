# Family Game Score Tracker

A modern, extensible web application to track scores for family games (starting with Yahtzee) using Flask, Jinja2, and SQLite3.

## Features
- Select from available games (easily extensible for more games)
- Add/select players from persistent database
- Enter and save scores for each session
- Modern, responsive UI
- Data stored in SQLite3 for persistence

## Project Structure
```
familygame_scoretracking/
├── app.py
├── db/
│   └── init_db.py
├── static/
│   └── style.css
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── select_players.html
│   ├── enter_scores.html
│   └── confirmation.html
├── requirements.txt
└── README.md
```

## Setup Instructions

1. **Clone the repository**

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Initialize the database**
   - The database will be initialized automatically on first run, or you can run:
   ```
   python db/init_db.py
   ```

4. **Run the application**
   ```
   python app.py
   ```
   The app will be available at [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

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
