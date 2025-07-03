
class UnoGame:
    def __init__(self):
        self.name = "Uno"

    def process_scores(self, players, form_data):
        """
        Processes the final rankings for an Uno game.

        Args:
            players: A list of player objects.
            form_data: The form data from the request.

        Returns:
            A tuple containing a boolean indicating success, a dictionary of scores,
            and a flash message.
        """
        rankings = {}
        for player in players:
            rank = form_data.get(f'rank_{player["id"]}')
            if rank is None or not rank.isdigit():
                return False, None, "Please enter a valid unique ranking for each player (1 for 1st, 2 for 2nd, etc.)."
            rankings[player['id']] = int(rank)

        if len(set(rankings.values())) != len(players):
            return False, None, "Each player must have a unique ranking."
        
        return True, rankings, None, "Scores saved successfully."
