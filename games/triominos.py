class TriominosGame:
    def __init__(self):
        self.name = "Triominos"

    def process_scores(self, players, form_data):
        """
        Processes the scores for a Triominos game.
        Players enter scores per round, and the total score is the sum.

        Args:
            players: A list of player objects.
            form_data: The form data from the request.

        Returns:
            A tuple containing a boolean indicating success, a dictionary of scores,
            and a flash message.
        """
        print(f"Triominos: Received form_data: {form_data}")
        player_round_scores = {}
        for player in players:
            player_round_scores[player['id']] = []
            # Collect all scores for this player across rounds
            for key, value in form_data.items():
                if key.startswith(f'score_{player["id"]}_') and value.strip().isdigit():
                    player_round_scores[player['id']].append(int(value))
        
        # Calculate total scores for each player
        player_total_scores = {}
        for player_id, scores_list in player_round_scores.items():
            player_total_scores[player_id] = sum(scores_list)
        print(f"Triominos: Calculated player_total_scores: {player_total_scores}")

        # Determine ranking (highest score wins)
        sorted_scores = sorted(player_total_scores.items(), key=lambda item: item[1], reverse=True)
        rankings = {player_id: rank + 1 for rank, (player_id, score) in enumerate(sorted_scores)}

        if not player_total_scores:
            return False, None, "No scores entered. Please enter scores for at least one round."

        return True, rankings, player_total_scores, "Scores saved successfully."