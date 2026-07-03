import unittest
from werkzeug.datastructures import ImmutableMultiDict
from games.watten import WattenGame


class TestWattenGame(unittest.TestCase):

    def setUp(self):
        self.game = WattenGame()
        self.p4 = [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}]

    def _form(self, t0_score, t1_score, t0_players='1,2', t1_players='3,4'):
        return ImmutableMultiDict([
            ('team_count', '2'),
            ('team_0_name', 'Team A'), ('team_0_players', t0_players), ('team_0_score', str(t0_score)),
            ('team_1_name', 'Team B'), ('team_1_players', t1_players), ('team_1_score', str(t1_score)),
        ])

    def test_winner_gets_rank_1(self):
        success, rankings, total_scores, msg = self.game.process_scores(self.p4, self._form(11, 7))
        self.assertTrue(success)
        self.assertEqual(rankings[1], 1)
        self.assertEqual(rankings[2], 1)
        self.assertEqual(rankings[3], 2)
        self.assertEqual(rankings[4], 2)

    def test_total_scores_match_team_score(self):
        success, rankings, total_scores, msg = self.game.process_scores(self.p4, self._form(11, 7))
        self.assertEqual(total_scores[1], 11)
        self.assertEqual(total_scores[2], 11)
        self.assertEqual(total_scores[3], 7)
        self.assertEqual(total_scores[4], 7)

    def test_loser_team_wins_when_higher_score(self):
        success, rankings, total_scores, msg = self.game.process_scores(self.p4, self._form(3, 11))
        self.assertTrue(success)
        self.assertEqual(rankings[3], 1)
        self.assertEqual(rankings[1], 2)

    def test_missing_team_players_fails(self):
        success, rankings, total_scores, msg = self.game.process_scores(
            self.p4, self._form(11, 7, t0_players=''))
        self.assertFalse(success)
        self.assertIsNone(rankings)

    def test_invalid_team_count_fails(self):
        form = ImmutableMultiDict([('team_count', 'abc')])
        success, rankings, total_scores, msg = self.game.process_scores(self.p4, form)
        self.assertFalse(success)
        self.assertIsNone(rankings)

    def test_one_player_per_team(self):
        players = [{'id': 1}, {'id': 2}]
        success, rankings, total_scores, msg = self.game.process_scores(
            players, self._form(11, 5, t0_players='1', t1_players='2'))
        self.assertTrue(success)
        self.assertEqual(rankings[1], 1)
        self.assertEqual(rankings[2], 2)


if __name__ == '__main__':
    unittest.main()
