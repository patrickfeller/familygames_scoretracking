import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'familygame.db')

# --- Database Operations ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_games():
    conn = get_db_connection()
    games = conn.execute('SELECT * FROM games').fetchall()
    conn.close()
    return games

def get_players():
    conn = get_db_connection()
    players = conn.execute('SELECT * FROM players').fetchall()
    conn.close()
    return players

def add_player(name):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO players (name) VALUES (?)', (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Player already exists
    conn.close()

def add_score(game_id, player_scores):
    conn = get_db_connection()
    for player_id, score in player_scores.items():
        conn.execute(
            'INSERT INTO scores (game_id, player_id, score, timestamp) VALUES (?, ?, ?, ?)',
            (game_id, player_id, score, datetime.now())
        )
    conn.commit()
    conn.close()

def ensure_games():
    # Add initial games if not present
    conn = get_db_connection()
    existing = conn.execute('SELECT COUNT(*) FROM games').fetchone()[0]
    if existing == 0:
        conn.executemany('INSERT INTO games (name) VALUES (?)', [
            ('Yahtzee',),
            # Add more games here as needed
        ])
        conn.commit()
    conn.close()

# --- Setup for Flask 3.x ---
from db.init_db import init_db
init_db()
ensure_games()

# --- Routes ---
@app.route('/')
def index():
    games = get_games()
    return render_template('index.html', games=games)

@app.route('/select_players/<int:game_id>', methods=['GET', 'POST'])
def select_players(game_id):
    players = get_players()
    if request.method == 'POST':
        selected = request.form.getlist('players')
        new_player = request.form.get('new_player')
        if new_player:
            add_player(new_player.strip())
            players = get_players()  # Refresh
            selected.append(str(players[-1]['id']))
        if selected:
            return redirect(url_for('enter_scores', game_id=game_id, player_ids=','.join(selected)))
        flash('Please select or add at least one player.')
    game = [g for g in get_games() if g['id'] == game_id][0]
    return render_template('select_players.html', players=players, game=game)

@app.route('/enter_scores/<int:game_id>', methods=['GET', 'POST'])
def enter_scores(game_id):
    player_ids = request.args.get('player_ids', '')
    if not player_ids:
        flash('No players selected.')
        return redirect(url_for('select_players', game_id=game_id))
    player_ids = [int(pid) for pid in player_ids.split(',') if pid]
    conn = get_db_connection()
    players = conn.execute('SELECT * FROM players WHERE id IN (%s)' % ','.join('?'*len(player_ids)), player_ids).fetchall()
    conn.close()
    game = [g for g in get_games() if g['id'] == game_id][0]
    if request.method == 'POST':
        scores = {}
        for player in players:
            score = request.form.get(f'score_{player["id"]}')
            if score is not None and score.isdigit():
                scores[player['id']] = int(score)
        if scores:
            add_score(game_id, scores)
            return redirect(url_for('confirmation'))
        flash('Please enter scores for all players.')
    return render_template('enter_scores.html', players=players, game=game)

@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')

if __name__ == '__main__':
    app.run(debug=True) 