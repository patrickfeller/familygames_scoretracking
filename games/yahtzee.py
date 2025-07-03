
class YahtzeeGame:
    def __init__(self):
        self.name = "Yahtzee"
        self.categories = [
            'ones', 'twos', 'threes', 'fours', 'fives', 'sixes',
            'one_pair', 'two_pair', 'three_of_a_kind', 'four_of_a_kind',
            'full_house', 'small_straight', 'large_straight', 'chance', 'yahtzee'
        ]

    def calculate_score(self, form_data):
        """
        Calculates the total score for a Yahtzee game based on the form data.

        Args:
            form_data: The form data from the request.

        Returns:
            The total score.
        """
        scores = {cat: int(form_data.get(cat, 0) or 0) for cat in self.categories}

        upper_section_score = sum(scores[cat] for cat in self.categories[:6])
        upper_section_bonus = 35 if upper_section_score >= 63 else 0

        lower_section_score = sum(scores[cat] for cat in self.categories[6:])
        
        total_score = upper_section_score + upper_section_bonus + lower_section_score
        return total_score
