import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'familygame.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_score INTEGER,
            session_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
    ''')

    # Add total_score column if it doesn't exist
    try:
        c.execute('ALTER TABLE scores ADD COLUMN total_score INTEGER')
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Add session_id column if it doesn't exist
    try:
        c.execute('ALTER TABLE scores ADD COLUMN session_id TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print('Database initialized.')
    # Print all games for debug
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    print('Games in DB:')
    for row in c.execute('SELECT * FROM games'):
        print(row)
    conn.close() 