class WattenGame:
    def __init__(self):
        self.name = "Watten"

    def process_scores(self, players, form_data):
        try:
            team_count = int(form_data.get('team_count', 2))
        except (ValueError, TypeError):
            return False, None, None, "Invalid team count."

        team_scores = {}
        team_members = {}
        valid_ids = {p['id'] for p in players}
        for i in range(team_count):
            try:
                score = int(form_data.get(f'team_{i}_score', 0))
            except (ValueError, TypeError):
                return False, None, None, f"Invalid score for team {i + 1}."
            raw = form_data.get(f'team_{i}_players', '')
            pids = [int(x) for x in raw.split(',')
                    if x.strip().lstrip('-').isdigit() and int(x) > 0 and int(x) in valid_ids]
            team_scores[i] = score
            team_members[i] = pids

        for i in range(team_count):
            if not team_members[i]:
                return False, None, None, f"Team {i + 1} has no players."

        sorted_teams = sorted(range(team_count), key=lambda i: team_scores[i], reverse=True)
        team_rank = {ti: rank + 1 for rank, ti in enumerate(sorted_teams)}

        rankings = {}
        total_scores = {}
        for ti in range(team_count):
            for pid in team_members[ti]:
                rankings[pid] = team_rank[ti]
                total_scores[pid] = team_scores[ti]

        return True, rankings, total_scores, "Scores saved successfully."
