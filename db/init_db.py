import os

import psycopg2
from dotenv import load_dotenv


def init_db(conn):
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id SERIAL PRIMARY KEY,
            game_id INTEGER NOT NULL REFERENCES games(id),
            player_id INTEGER NOT NULL REFERENCES players(id),
            score INTEGER NOT NULL,
            total_score INTEGER,
            session_id TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('ALTER TABLE players ENABLE ROW LEVEL SECURITY')
    cur.execute('ALTER TABLE games ENABLE ROW LEVEL SECURITY')
    cur.execute('ALTER TABLE scores ENABLE ROW LEVEL SECURITY')
    conn.commit()
    cur.close()


if __name__ == '__main__':
    load_dotenv()
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    init_db(conn)
    print('Database initialized.')

    cur = conn.cursor()
    cur.execute('SELECT * FROM games')
    print('Games in DB:')
    for row in cur.fetchall():
        print(row)
    cur.close()
    conn.close()
