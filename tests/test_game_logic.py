import unittest
import os
import sqlite3
from datetime import datetime
import uuid
from app import app, get_db_connection, add_player, add_score
from games.uno import UnoGame
from games.yahtzee import YahtzeeGame

# Set up a test database
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), 'test_familygame.db')

class TestGameLogic(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure a clean test database before all tests
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        cls.app = app.test_client()
        cls.app.testing = True
        cls.conn = sqlite3.connect(TEST_DB_PATH)
        cls.conn.row_factory = sqlite3.Row
        cls.cursor = cls.conn.cursor()
        cls.create_test_tables()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    @staticmethod
    def create_test_tables():
        conn = sqlite3.connect(TEST_DB_PATH)
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
                session_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id),
                FOREIGN KEY (player_id) REFERENCES players(id)
            )
        ''')
        conn.commit()
        conn.close()

    def setUp(self):
        # Clear tables before each test
        conn = sqlite3.connect(TEST_DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM players')
        c.execute('DELETE FROM games')
        c.execute('DELETE FROM scores')
        conn.commit()
        conn.close()

        # Override DB_PATH for testing
        app.config['DB_PATH'] = TEST_DB_PATH

    def tearDown(self):
        pass # DB_PATH is set in setUp and doesn't need to be restored

    def test_uno_game_process_scores_valid(self):
        uno_game = UnoGame()
        # Add test players
        add_player('Alice')
        add_player('Bob')
        conn = get_db_connection()
        players = conn.execute('SELECT * FROM players').fetchall()
        conn.close()

        form_data = {
            f'rank_{players[0]["id"]}': '1',
            f'rank_{players[1]["id"]}': '2'
        }
        success, scores, message = uno_game.process_scores(players, form_data)
        self.assertTrue(success)
        self.assertIn(players[0]['id'], scores)
        self.assertIn(players[1]['id'], scores)
        self.assertEqual(scores[players[0]['id']], 1)
        self.assertEqual(scores[players[1]['id']], 2)
        self.assertEqual(message, "Scores saved successfully.")

    def test_uno_game_process_scores_invalid_duplicate_rank(self):
        uno_game = UnoGame()
        add_player('Alice')
        add_player('Bob')
        conn = get_db_connection()
        players = conn.execute('SELECT * FROM players').fetchall()
        conn.close()

        form_data = {
            f'rank_{players[0]["id"]}': '1',
            f'rank_{players[1]["id"]}': '1'
        }
        success, scores, message = uno_game.process_scores(players, form_data)
        self.assertFalse(success)
        self.assertIsNone(scores)
        self.assertEqual(message, "Please enter a valid unique ranking for each player (1 for 1st, 2 for 2nd, etc.).")

    def test_uno_game_process_scores_invalid_missing_rank(self):
        uno_game = UnoGame()
        add_player('Alice')
        add_player('Bob')
        conn = get_db_connection()
        players = conn.execute('SELECT * FROM players').fetchall()
        conn.close()

        form_data = {
            f'rank_{players[0]["id"]}': '1',
            # Missing rank for Bob
        }
        success, scores, message = uno_game.process_scores(players, form_data)
        self.assertFalse(success)
        self.assertIsNone(scores)
        self.assertEqual(message, "Please enter a valid unique ranking for each player (1 for 1st, 2 for 2nd, etc.).")

    def test_yahtzee_game_calculate_score(self):
        yahtzee_game = YahtzeeGame()
        form_data = {
            'ones': '1', 'twos': '2', 'threes': '3', 'fours': '4', 'fives': '5', 'sixes': '6',
            'one_pair': '10', 'two_pair': '12', 'three_of_a_kind': '15', 'four_of_a_kind': '20',
            'full_house': '25', 'small_straight': '30', 'large_straight': '40', 'chance': '20', 'yahtzee': '50'
        }
        total_score = yahtzee_game.calculate_score(form_data)
        print(f"Yahtzee Test 1: Calculated Total Score: {total_score}")
        # Expected: (1+2+3+4+5+6) + 35 (bonus) + (10+12+15+20+25+30+40+20+50) = 21 + 35 + 222 = 278
        self.assertEqual(total_score, 278)

    def test_yahtzee_game_calculate_score_with_bonus(self):
        yahtzee_game = YahtzeeGame()
        form_data = {
            'ones': '6', 'twos': '6', 'threes': '6', 'fours': '6', 'fives': '6', 'sixes': '6', # 36 points each, total 216
            'one_pair': '0', 'two_pair': '0', 'three_of_a_kind': '0', 'four_of_a_kind': '0',
            'full_house': '0', 'small_straight': '0', 'large_straight': '0', 'chance': '0', 'yahtzee': '0'
        }
        total_score = yahtzee_game.calculate_score(form_data)
        print(f"Yahtzee Test 2: Calculated Total Score: {total_score}")
        # Expected: 216 (upper) + 35 (bonus) = 251
        self.assertEqual(total_score, 251)

    def test_add_player(self):
        add_player('Charlie')
        conn = get_db_connection()
        player = conn.execute('SELECT * FROM players WHERE name = "Charlie"').fetchone()
        conn.close()
        self.assertIsNotNone(player)
        self.assertEqual(player['name'], 'Charlie')

    def test_add_player_duplicate(self):
        add_player('David')
        add_player('David') # Try to add again
        conn = get_db_connection()
        players = conn.execute('SELECT * FROM players WHERE name = "David"').fetchall()
        conn.close()
        self.assertEqual(len(players), 1) # Should only be one entry

    def test_add_score(self):
        # Add game and player
        conn = get_db_connection()
        conn.execute('INSERT INTO games (name) VALUES (?)', ('Test Game',))
        game_id = conn.execute('SELECT id FROM games WHERE name = "Test Game"').fetchone()[0]
        conn.close()

        add_player('Eve')
        conn = get_db_connection()
        player_id = conn.execute('SELECT id FROM players WHERE name = "Eve"').fetchone()[0]
        conn.close()

        player_scores_map = {player_id: 100}
        player_total_scores_map = {player_id: 100}
        session_id = str(uuid.uuid4())
        add_score(game_id, player_scores_map, session_id, player_total_scores_map)

        conn = get_db_connection()
        score_entry = conn.execute('SELECT * FROM scores WHERE game_id = ? AND player_id = ? AND session_id = ?', (game_id, player_id, session_id)).fetchone()
        conn.close()

        self.assertIsNotNone(score_entry)
        self.assertEqual(score_entry['score'], 100)
        self.assertEqual(score_entry['total_score'], 100)
        self.assertEqual(score_entry['session_id'], session_id)
        self.assertIsNotNone(score_entry['timestamp'])

    def test_add_score_no_total_score(self):
        # Add game and player
        conn = get_db_connection()
        conn.execute('INSERT INTO games (name) VALUES (?)', ('Another Game',))
        game_id = conn.execute('SELECT id FROM games WHERE name = "Another Game"').fetchone()[0]
        conn.close()

        add_player('Frank')
        conn = get_db_connection()
        player_id = conn.execute('SELECT id FROM players WHERE name = "Frank"').fetchone()[0]
        conn.close()

        player_scores_map = {player_id: 50}
        session_id = str(uuid.uuid4())
        add_score(game_id, player_scores_map, session_id) # No total_score_map

        conn = get_db_connection()
        score_entry = conn.execute('SELECT * FROM scores WHERE game_id = ? AND player_id = ? AND session_id = ?', (game_id, player_id, session_id)).fetchone()
        conn.close()

        self.assertIsNotNone(score_entry)
        self.assertEqual(score_entry['score'], 50)
        self.assertIsNone(score_entry['total_score'])
        self.assertEqual(score_entry['session_id'], session_id)
        self.assertIsNotNone(score_entry['timestamp'])

if __name__ == '__main__':
    unittest.main()
