import os
import sqlite3
import uuid

import psycopg2
from dotenv import load_dotenv

from db.init_db import init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, '..', 'familygame.db')


def fetch_sqlite_rows(table):
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f'SELECT * FROM {table}').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def migrate():
    load_dotenv()
    pg_conn = psycopg2.connect(os.environ['DATABASE_URL'])
    init_db(pg_conn)

    cur = pg_conn.cursor()
    cur.execute('TRUNCATE players, games, scores RESTART IDENTITY CASCADE')

    players = fetch_sqlite_rows('players')
    for player in players:
        cur.execute('INSERT INTO players (id, name) VALUES (%s, %s)', (player['id'], player['name']))

    games = fetch_sqlite_rows('games')
    for game in games:
        cur.execute('INSERT INTO games (id, name) VALUES (%s, %s)', (game['id'], game['name']))

    scores = fetch_sqlite_rows('scores')
    for score in scores:
        session_id = score['session_id'] or str(uuid.uuid4())
        cur.execute(
            '''INSERT INTO scores (id, game_id, player_id, score, total_score, session_id, timestamp)
               VALUES (%s, %s, %s, %s, %s, %s, %s)''',
            (score['id'], score['game_id'], score['player_id'], score['score'],
             score['total_score'], session_id, score['timestamp'])
        )

    for table in ('players', 'games', 'scores'):
        cur.execute(f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 1))")

    pg_conn.commit()
    cur.close()
    pg_conn.close()

    print(f"Migrated {len(players)} players, {len(games)} games, {len(scores)} scores.")


if __name__ == '__main__':
    migrate()
