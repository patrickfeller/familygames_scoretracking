import os
import uuid
from datetime import datetime

import psycopg2
import psycopg2.extras
from psycopg2 import sql
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL')

# --- Database Operations ---
def get_db_connection():
    conn = psycopg2.connect(app.config['DATABASE_URL'])
    schema = app.config.get('DB_SCHEMA')
    if schema:
        cur = conn.cursor()
        cur.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)))
        conn.commit()
        cur.close()
    return conn

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

def get_games():
    conn = get_db_connection()
    games_data = query_db(conn, 'SELECT * FROM games')
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
    players = query_db(conn, 'SELECT * FROM players')
    conn.close()
    return players

def add_player(name):
    conn = get_db_connection()
    try:
        execute_db(conn, 'INSERT INTO players (name) VALUES (%s)', (name,))
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()  # Player already exists
    conn.close()

def add_score(game_id, player_scores_map, session_id, player_total_scores_map=None):
    conn = get_db_connection()
    for player_id, score_value in player_scores_map.items():
        total_score_value = player_total_scores_map.get(player_id) if player_total_scores_map else None
        execute_db(
            conn,
            'INSERT INTO scores (game_id, player_id, score, total_score, session_id, timestamp) VALUES (%s, %s, %s, %s, %s, %s)',
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
        existing = query_db(conn, 'SELECT COUNT(*) AS count FROM games WHERE name = %s', (game_name,), one=True)
        if existing['count'] == 0:
            execute_db(conn, 'INSERT INTO games (name) VALUES (%s)', (game_name,))

    conn.commit()
    conn.close()

# --- Score History ---
def get_score_history():
    conn = get_db_connection()
    rows = query_db(conn, '''
        SELECT
            scores.session_id,
            games.name AS game_name,
            players.name AS player_name,
            scores.score,
            scores.total_score,
            scores.timestamp
        FROM scores
        JOIN games ON scores.game_id = games.id
        JOIN players ON scores.player_id = players.id
        ORDER BY scores.timestamp DESC, scores.total_score DESC NULLS LAST
    ''')
    conn.close()
    return rows

# --- Setup ---
from db.init_db import init_db

with app.app_context():
    _setup_conn = get_db_connection()
    init_db(_setup_conn)
    _setup_conn.close()
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
        else:  # This handles the 'Continue with Selected Players' form submission
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
    placeholders = ','.join(['%s'] * len(player_ids_list))
    all_players = query_db(conn, f'SELECT * FROM players WHERE id IN ({placeholders})', player_ids_list)
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
    return render_template('enter_scores.html', players=players, game=game, is_uno=game_name == 'uno')

@app.route('/calculate_yahtzee/<int:game_id>/<player_ids>', methods=['POST'])
def calculate_yahtzee(game_id, player_ids):
    from games.yahtzee import YahtzeeGame
    yahtzee_game = YahtzeeGame()
    player_ids_list = [int(pid) for pid in player_ids.split(',') if pid]
    conn = get_db_connection()
    placeholders = ','.join(['%s'] * len(player_ids_list))
    players = query_db(conn, f'SELECT * FROM players WHERE id IN ({placeholders})', player_ids_list)
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
    results = query_db(conn, '''
        SELECT p.name, s.score, s.total_score
        FROM scores s
        JOIN players p ON s.player_id = p.id
        WHERE s.session_id = %s
        ORDER BY s.score
    ''', (session_id,))

    conn.close()
    return render_template('confirmation.html', results=results)

@app.route('/ranking')
def ranking():
    conn = get_db_connection()
    rows = query_db(conn, '''
        SELECT
            p.name            AS player_name,
            g.name            AS game_name,
            EXTRACT(YEAR FROM s.timestamp)::int AS year,
            COALESCE(SUM(s.total_score), 0)::bigint AS total_points,
            COUNT(DISTINCT CASE WHEN s.score = 1 THEN s.session_id END) AS wins,
            COUNT(DISTINCT s.session_id) AS games_played
        FROM scores s
        JOIN players p ON s.player_id = p.id
        JOIN games  g ON s.game_id  = g.id
        GROUP BY p.name, g.name, EXTRACT(YEAR FROM s.timestamp)::int
        ORDER BY g.name, year DESC, total_points DESC
    ''')
    conn.close()

    stats = {}      # stats[game][year][player] = [pts, wins, games]
    years_set = set()
    for row in rows:
        g = row['game_name']
        y = str(int(row['year']))
        n = row['player_name']
        years_set.add(y)
        stats.setdefault(g, {}).setdefault(y, {})[n] = [
            int(row['total_points']), int(row['wins']), int(row['games_played'])
        ]

    years = sorted(years_set, reverse=True)
    games = sorted(stats.keys())
    return render_template('ranking.html', stats=stats, years=years, games=games)

@app.route('/history')
def history():
    rows = get_score_history()
    # Group flat rows into session objects
    sessions = []
    seen = {}  # session_id -> index in sessions list
    for row in rows:
        row_dict = dict(row)
        sid = str(row_dict['session_id'])
        ts = row_dict['timestamp'].strftime('%d %b · %H:%M')
        if sid not in seen:
            seen[sid] = len(sessions)
            sessions.append({
                'session_id': sid,
                'game': row_dict['game_name'],
                'when': ts,
                'rows': [],
            })
        sessions[seen[sid]]['rows'].append({
            'name': row_dict['player_name'],
            'score': row_dict['score'],
            'total': row_dict['total_score'],
        })
    # Mark winner per session (highest total_score; skip None)
    for s in sessions:
        valid = [r for r in s['rows'] if r['total'] is not None]
        if valid:
            best = max(valid, key=lambda r: r['total'])
            for r in s['rows']:
                r['win'] = (r is best)
        else:
            for r in s['rows']:
                r['win'] = False
    return render_template('history.html', sessions=sessions)

if __name__ == '__main__':
    app.run(debug=True)
