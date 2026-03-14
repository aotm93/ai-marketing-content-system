"""
Title-Query Matcher - Validates title relevance to search queries
"""

from typing import Tuple


class TitleQueryMatcher:
    """Validates that generated titles match actual search queries"""

    def calculate_match_score(self, title: str, keyword: str) -> float:
        """
        Calculate how well title matches the search keyword

        Scoring:
        - Exact keyword match: +0.4
        - Word order preserved: +0.3
        - All keyword words present: +0.3

        Returns:
            float: Match score 0.0-1.0
        """
        title_lower = title.lower()
        keyword_lower = keyword.lower()

        score = 0.0

        # Exact keyword match (highest priority)
        if keyword_lower in title_lower:
            score += 0.4

        # Check word order preservation
        keyword_words = keyword_lower.split()
        if self._check_word_order(title_lower, keyword_words):
            score += 0.3

        # Check all keyword words present
        title_words = set(title_lower.split())
        keyword_word_set = set(keyword_words)
        if keyword_word_set.issubset(title_words):
            score += 0.3

        return min(score, 1.0)

    def _check_word_order(self, text: str, words: list) -> bool:
        """Check if words appear in order in text"""
        last_pos = -1
        for word in words:
            pos = text.find(word, last_pos + 1)
            if pos == -1:
                return False
            last_pos = pos
        return True

    def is_match_acceptable(self, title: str, keyword: str, threshold: float = 0.6) -> Tuple[bool, float]:
        """
        Check if title-keyword match is acceptable

        Returns:
            Tuple[bool, float]: (is_acceptable, match_score)
        """
        score = self.calculate_match_score(title, keyword)
        return (score >= threshold, score)
