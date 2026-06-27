import unittest
import uuid

import psycopg2
from psycopg2 import sql

from app import app, get_db_connection, query_db, execute_db, add_player, add_score
from db.init_db import init_db
from games.uno import UnoGame
from games.yahtzee import YahtzeeGame

TEST_SCHEMA = 'test'


class TestGameLogic(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = app.test_client()
        cls.app.testing = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['DB_SCHEMA'] = TEST_SCHEMA

        conn = psycopg2.connect(app.config['DATABASE_URL'])
        cur = conn.cursor()
        cur.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(TEST_SCHEMA)))
        cur.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(TEST_SCHEMA)))
        conn.commit()
        init_db(conn)
        cur.close()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        del app.config['DB_SCHEMA']

    def setUp(self):
        # Clear tables before each test (scores first: FK references games/players)
        conn = get_db_connection()
        execute_db(conn, 'DELETE FROM scores')
        execute_db(conn, 'DELETE FROM players')
        execute_db(conn, 'DELETE FROM games')
        conn.commit()
        conn.close()

    def test_uno_game_process_scores_valid(self):
        uno_game = UnoGame()
        # Add test players
        add_player('Alice')
        add_player('Bob')
        conn = get_db_connection()
        players = query_db(conn, 'SELECT * FROM players')
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
        players = query_db(conn, 'SELECT * FROM players')
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
        players = query_db(conn, 'SELECT * FROM players')
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
        # Expected: (1+2+3+4+5+6) + 35 (bonus) + (10+12+15+20+25+30+40+20+50) = 21 + 35 + 222 = 278
        self.assertEqual(total_score, 278)

    def test_yahtzee_game_calculate_score_with_bonus(self):
        yahtzee_game = YahtzeeGame()
        form_data = {
            'ones': '6', 'twos': '6', 'threes': '6', 'fours': '6', 'fives': '6', 'sixes': '6',  # 36 points each, total 216
            'one_pair': '0', 'two_pair': '0', 'three_of_a_kind': '0', 'four_of_a_kind': '0',
            'full_house': '0', 'small_straight': '0', 'large_straight': '0', 'chance': '0', 'yahtzee': '0'
        }
        total_score = yahtzee_game.calculate_score(form_data)
        # Expected: 216 (upper) + 35 (bonus) = 251
        self.assertEqual(total_score, 251)

    def test_add_player(self):
        add_player('Charlie')
        conn = get_db_connection()
        player = query_db(conn, 'SELECT * FROM players WHERE name = %s', ('Charlie',), one=True)
        conn.close()
        self.assertIsNotNone(player)
        self.assertEqual(player['name'], 'Charlie')

    def test_add_player_duplicate(self):
        add_player('David')
        add_player('David')  # Try to add again
        conn = get_db_connection()
        players = query_db(conn, 'SELECT * FROM players WHERE name = %s', ('David',))
        conn.close()
        self.assertEqual(len(players), 1)  # Should only be one entry

    def test_add_score(self):
        # Add game and player
        conn = get_db_connection()
        execute_db(conn, 'INSERT INTO games (name) VALUES (%s)', ('Test Game',))
        conn.commit()
        game = query_db(conn, 'SELECT id FROM games WHERE name = %s', ('Test Game',), one=True)
        game_id = game['id']
        conn.close()

        add_player('Eve')
        conn = get_db_connection()
        player = query_db(conn, 'SELECT id FROM players WHERE name = %s', ('Eve',), one=True)
        player_id = player['id']
        conn.close()

        player_scores_map = {player_id: 100}
        player_total_scores_map = {player_id: 100}
        session_id = str(uuid.uuid4())
        add_score(game_id, player_scores_map, session_id, player_total_scores_map)

        conn = get_db_connection()
        score_entry = query_db(
            conn,
            'SELECT * FROM scores WHERE game_id = %s AND player_id = %s AND session_id = %s',
            (game_id, player_id, session_id),
            one=True
        )
        conn.close()

        self.assertIsNotNone(score_entry)
        self.assertEqual(score_entry['score'], 100)
        self.assertEqual(score_entry['total_score'], 100)
        self.assertEqual(score_entry['session_id'], session_id)
        self.assertIsNotNone(score_entry['timestamp'])

    def test_add_score_no_total_score(self):
        # Add game and player
        conn = get_db_connection()
        execute_db(conn, 'INSERT INTO games (name) VALUES (%s)', ('Another Game',))
        conn.commit()
        game = query_db(conn, 'SELECT id FROM games WHERE name = %s', ('Another Game',), one=True)
        game_id = game['id']
        conn.close()

        add_player('Frank')
        conn = get_db_connection()
        player = query_db(conn, 'SELECT id FROM players WHERE name = %s', ('Frank',), one=True)
        player_id = player['id']
        conn.close()

        player_scores_map = {player_id: 50}
        session_id = str(uuid.uuid4())
        add_score(game_id, player_scores_map, session_id)  # No total_score_map

        conn = get_db_connection()
        score_entry = query_db(
            conn,
            'SELECT * FROM scores WHERE game_id = %s AND player_id = %s AND session_id = %s',
            (game_id, player_id, session_id),
            one=True
        )
        conn.close()

        self.assertIsNotNone(score_entry)
        self.assertEqual(score_entry['score'], 50)
        self.assertIsNone(score_entry['total_score'])
        self.assertEqual(score_entry['session_id'], session_id)
        self.assertIsNotNone(score_entry['timestamp'])


if __name__ == '__main__':
    unittest.main()
