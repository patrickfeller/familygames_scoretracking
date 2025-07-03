import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_fallback_secret_key') # Use environment variable for production

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['DB_PATH'] = os.path.join(BASE_DIR, 'familygame.db')

# --- Database Operations ---
def get_db_connection():
    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    return conn

def get_games():
    conn = get_db_connection()
    games_data = conn.execute('SELECT * FROM games').fetchall()
    conn.close()
    
    # Add logo filenames based on game name
    games_with_logos = []
    for game in games_data:
        game_dict = dict(game)
        # Assuming logo files are named like 'game_name_logo.png' in static/images/
        game_dict['logo_filename'] = f"{game_dict['name'].lower()}_logo.png"
        games_with_logos.append(game_dict)
    return games_with_logos

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

def add_score(game_id, player_scores_map, session_id, player_total_scores_map=None):
    conn = get_db_connection()
    for player_id, score_value in player_scores_map.items():
        total_score_value = player_total_scores_map.get(player_id) if player_total_scores_map else None
        conn.execute(
            'INSERT INTO scores (game_id, player_id, score, total_score, session_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
            (game_id, player_id, score_value, total_score_value, session_id, datetime.now())
        )
    conn.commit()
    conn.close()

def ensure_games():
    # Add initial games if not present
    conn = get_db_connection()
    
    # List of games that should be in the database
    required_games = ['Yahtzee', 'Uno', 'Triominos']  # Add more games here
    
    for game_name in required_games:
        existing = conn.execute('SELECT COUNT(*) FROM games WHERE name = ?', (game_name,)).fetchone()[0]
        if existing == 0:
            conn.execute('INSERT INTO games (name) VALUES (?)', (game_name,))
            
    conn.commit()
    conn.close()

# --- Score History ---
def get_score_history():
    conn = get_db_connection()
    history = conn.execute('''
        SELECT scores.id, games.name AS game_name, players.name AS player_name, scores.score, scores.total_score, scores.timestamp
        FROM scores
        JOIN games ON scores.game_id = games.id
        JOIN players ON scores.player_id = players.id
        ORDER BY scores.timestamp DESC
    ''').fetchall()
    conn.close()
    return history

# --- Setup for Flask 3.x ---
from db.init_db import init_db

with app.app_context():
    init_db()
    ensure_games()

# --- Routes ---
@app.route('/')
def index():
    games = get_games()
    return render_template('index.html', games=games)

@app.route('/select_players/<int:game_id>', methods=['GET', 'POST'])
def select_players(game_id):
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_player':
            new_player_name = request.form.get('new_player_name')
            if new_player_name:
                add_player(new_player_name.strip())
                flash(f'Player "{new_player_name}" added successfully!')
            else:
                flash('New player name cannot be empty.')
            return redirect(url_for('select_players', game_id=game_id))
        else: # This handles the 'Continue with Selected Players' form submission
            selected_player_ids_str = request.form.get('selected_player_ids')
            if selected_player_ids_str:
                sorted_player_ids = [pid for pid in selected_player_ids_str.split(',') if pid]
                if not sorted_player_ids:
                    flash('Please select at least one player.')
                    return redirect(url_for('select_players', game_id=game_id))
                return redirect(url_for('enter_scores', game_id=game_id, player_ids=','.join(sorted_player_ids)))
            else:
                flash('Please select at least one player.')
                return redirect(url_for('select_players', game_id=game_id))
    
    players = get_players()
    game = [g for g in get_games() if g['id'] == game_id][0]
    return render_template('select_players.html', players=players, game=game)

@app.route('/enter_scores/<int:game_id>', methods=['GET', 'POST'])
def enter_scores(game_id):
    player_ids = request.args.get('player_ids', '')
    if not player_ids:
        flash('No players selected.')
        return redirect(url_for('select_players', game_id=game_id))
    player_ids_list = [int(pid) for pid in player_ids.split(',') if pid]
    conn = get_db_connection()
    # Fetch players and store them in a dictionary for easy lookup
    all_players = conn.execute('SELECT * FROM players WHERE id IN (%s)' % ','.join('?'*len(player_ids_list)), player_ids_list).fetchall()
    conn.close()

    player_dict = {player['id']: player for player in all_players}
    
    # Reorder players based on the player_ids_list
    players = [player_dict[pid] for pid in player_ids_list]
    game = [g for g in get_games() if g['id'] == game_id][0]
    game_name = game['name'].lower()

    # Existing logic for Uno and other games
    game_logic = None
    if game_name == 'uno':
        from games.uno import UnoGame
        game_logic = UnoGame()
    elif game_name == 'triominos':
        from games.triominos import TriominosGame
        game_logic = TriominosGame()

    if request.method == 'POST':
        session_id = str(uuid.uuid4())
        if game_logic:
            success, rankings, total_scores, message = game_logic.process_scores(players, request.form)
            print(f"Triominos process_scores returned success: {success}")
            if success:
                add_score(game_id, rankings, session_id, total_scores)
                return redirect(url_for('confirmation', session_id=session_id))
            else:
                flash(message)
        else:
            scores = {}
            for player in players:
                score = request.form.get(f'score_{player["id"]}')
                if score is not None and score.isdigit():
                    scores[player['id']] = int(score)
            if scores:
                add_score(game_id, scores, session_id)
                return redirect(url_for('confirmation', session_id=session_id))
            flash('Please enter scores for all players.')
    
    if game_name == 'yahtzee':
        return render_template('yahtzee.html', players=players, game=game, player_ids=player_ids)
    elif game_name == 'triominos':
        return render_template('triominos.html', players=players, game=game, player_ids=player_ids)
        session_id = str(uuid.uuid4())
        if game_logic:
            success, rankings, total_scores, message = game_logic.process_scores(players, request.form)
            print(f"Triominos process_scores returned success: {success}")
            if success:
                add_score(game_id, rankings, session_id, total_scores)
                return redirect(url_for('confirmation', session_id=session_id))
            else:
                flash(message)
        else:
            scores = {}
            for player in players:
                score = request.form.get(f'score_{player["id"]}')
                if score is not None and score.isdigit():
                    scores[player['id']] = int(score)
            if scores:
                add_score(game_id, scores, session_id)
                return redirect(url_for('confirmation', session_id=session_id))
            flash('Please enter scores for all players.')
    return render_template('enter_scores.html', players=players, game=game, is_uno=game_name == 'uno')

@app.route('/calculate_yahtzee/<int:game_id>/<player_ids>', methods=['POST'])
def calculate_yahtzee(game_id, player_ids):
    from games.yahtzee import YahtzeeGame
    yahtzee_game = YahtzeeGame()
    player_ids_list = [int(pid) for pid in player_ids.split(',') if pid]
    conn = get_db_connection()
    players = conn.execute('SELECT * FROM players WHERE id IN (%s)' % ','.join('?'*len(player_ids_list)), player_ids_list).fetchall()
    conn.close()

    player_scores = {}
    for player in players:
        player_form_data = {cat: request.form.get(f'{player["id"]}_{cat}') for cat in yahtzee_game.categories}
        total_score = yahtzee_game.calculate_score(player_form_data)
        player_scores[player['id']] = total_score

    # Determine ranking
    sorted_scores = sorted(player_scores.items(), key=lambda item: item[1], reverse=True)
    rankings = {player_id: rank + 1 for rank, (player_id, score) in enumerate(sorted_scores)}

    session_id = str(uuid.uuid4())
    add_score(game_id, rankings, session_id, player_scores)
    return redirect(url_for('confirmation', session_id=session_id))

@app.route('/confirmation/<session_id>')
def confirmation(session_id):
    conn = get_db_connection()
    # Get all scores for the given session_id
    results = conn.execute('''
        SELECT p.name, s.score, s.total_score
        FROM scores s
        JOIN players p ON s.player_id = p.id
        WHERE s.session_id = ?
        ORDER BY s.score
    ''', (session_id,)).fetchall()
    
    conn.close()
    return render_template('confirmation.html', results=results)

@app.route('/history')
def history():
    history_raw = get_score_history()
    history_formatted = []
    for row in history_raw:
        row_dict = dict(row)
        # The timestamp is a string from the database, e.g., '2025-07-03 12:32:15.631740'
        # We parse it into a datetime object, then format it as a string.
        dt_object = datetime.strptime(row_dict['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
        row_dict['timestamp'] = dt_object.strftime('%d.%m.%Y %H:%M')
        history_formatted.append(row_dict)
    return render_template('history.html', history=history_formatted)

if __name__ == '__main__':
    app.run(debug=True)