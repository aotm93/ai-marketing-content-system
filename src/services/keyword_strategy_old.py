"""
Keyword Strategy Service
Implements intelligent keyword generation for new websites with low traffic

Features:
- Product category-based keyword generation
- Long-tail keyword focus
- Semantic diversity checking
- Topic cluster architecture
"""

import logging
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SearchIntent(str, Enum):
    """Search intent types"""
    INFORMATIONAL = "informational"  # How-to, guides, what is
    COMMERCIAL = "commercial"        # Best, review, comparison
    TRANSACTIONAL = "transactional"  # Buy, price, wholesale
    NAVIGATIONAL = "navigational"    # Brand, specific product


@dataclass
class KeywordCandidate:
    """Keyword candidate with metadata"""
    keyword: str
    intent: SearchIntent
    category: str
    difficulty_estimate: str  # low, medium, high
    is_long_tail: bool
    semantic_group: str  # For avoiding cannibalization


class ProductCategoryKeywordGenerator:
    """
    Generates keywords based on product categories
    Optimized for new websites with low traffic
    """

    def __init__(self):
        """Initialize with product categories and keyword templates"""

        # Water bottle product categories
        self.product_categories = {
            "material": ["glass", "plastic", "stainless steel", "aluminum", "silicone", "copper"],
            "type": ["insulated", "collapsible", "filtered", "smart", "sports", "kids"],
            "use_case": ["hiking", "gym", "office", "travel", "cycling", "running"],
            "feature": ["leak proof", "BPA free", "dishwasher safe", "wide mouth", "straw lid"],
            "size": ["500ml", "750ml", "1 liter", "32oz", "64oz"],
            "brand_type": ["eco friendly", "luxury", "budget", "wholesale", "bulk"]
        }

        # Long-tail keyword templates (low competition, high intent)
        self.keyword_templates = {
            SearchIntent.INFORMATIONAL: [
                "how to clean {material} water bottle",
                "benefits of {material} water bottles",
                "are {feature} water bottles safe",
                "what is the best water bottle for {use_case}",
                "{material} vs {material} water bottle comparison",
                "how to choose water bottle for {use_case}",
                "why use {type} water bottle",
                "water bottle maintenance tips for {material}",
            ],
            SearchIntent.COMMERCIAL: [
                "best {material} water bottle for {use_case}",
                "top {type} water bottles {year}",
                "{material} water bottle reviews",
                "best {feature} water bottle under $30",
                "{type} water bottle comparison",
                "most durable {material} water bottles",
                "best wholesale water bottles for business",
                "{size} water bottle recommendations",
            ],
            SearchIntent.TRANSACTIONAL: [
                "buy {material} water bottles wholesale",
                "{type} water bottle bulk order",
                "custom water bottles with logo",
                "wholesale {material} bottles supplier",
                "cheap {feature} water bottles bulk",
                "water bottle manufacturer {material}",
            ]
        }

        logger.info("Initialized ProductCategoryKeywordGenerator")

    def generate_keyword_pool(
        self,
        limit: int = 100,
        intent_mix: Optional[Dict[SearchIntent, float]] = None
    ) -> List[KeywordCandidate]:
        """
        Generate a diverse pool of keywords

        Args:
            limit: Maximum number of keywords to generate
            intent_mix: Distribution of intents (e.g., {INFORMATIONAL: 0.5, COMMERCIAL: 0.4, TRANSACTIONAL: 0.1})

        Returns:
            List of keyword candidates
        """
        if intent_mix is None:
            # Default mix for new websites: focus on informational + commercial
            intent_mix = {
                SearchIntent.INFORMATIONAL: 0.5,  # 50% educational content
                SearchIntent.COMMERCIAL: 0.4,     # 40% comparison/review
                SearchIntent.TRANSACTIONAL: 0.1   # 10% transactional
            }

        keywords = []
        current_year = "2026"

        for intent, ratio in intent_mix.items():
            target_count = int(limit * ratio)
            templates = self.keyword_templates.get(intent, [])

            for template in templates:
                if len(keywords) >= limit:
                    break

                # Generate variations using product categories
                variations = self._generate_template_variations(template, current_year)

                for variation in variations[:target_count]:
                    if len(keywords) >= limit:
                        break

                    keywords.append(KeywordCandidate(
                        keyword=variation["keyword"],
                        intent=intent,
                        category=variation["category"],
                        difficulty_estimate="low" if len(variation["keyword"].split()) >= 4 else "medium",
                        is_long_tail=len(variation["keyword"].split()) >= 4,
                        semantic_group=variation["semantic_group"]
                    ))

        logger.info(f"Generated {len(keywords)} keyword candidates")
        return keywords

    def _generate_template_variations(self, template: str, year: str) -> List[Dict[str, Any]]:
        """Generate keyword variations from template"""
        variations = []

        # Extract placeholders from template
        import re
        placeholders = re.findall(r'\{(\w+)\}', template)

        if not placeholders:
            return [{"keyword": template, "category": "general", "semantic_group": "general"}]

        # Generate combinations
        for placeholder in placeholders:
            if placeholder == "year":
                continue  # Handle year separately

            category_values = self.product_categories.get(placeholder, [placeholder])

            for value in category_values[:3]:  # Limit to 3 per category to avoid explosion
                keyword = template.replace(f"{{{placeholder}}}", value)
                keyword = keyword.replace("{year}", year)

                # Determine semantic group (for diversity checking)
                semantic_group = f"{placeholder}_{value}"

                variations.append({
                    "keyword": keyword,
                    "category": placeholder,
                    "semantic_group": semantic_group
                })

        return variations

    def filter_by_semantic_diversity(
        self,
        candidates: List[KeywordCandidate],
        selected_keywords: List[str],
        min_diversity_score: float = 0.3
    ) -> List[KeywordCandidate]:
        """
        Filter keywords to ensure semantic diversity
        Prevents selecting too similar keywords on the same day

        Args:
            candidates: Available keyword candidates
            selected_keywords: Already selected keywords today
            min_diversity_score: Minimum diversity threshold (0-1)

        Returns:
            Filtered list of diverse candidates
        """
        if not selected_keywords:
            return candidates

        # Extract semantic groups from selected keywords
        selected_groups = set()
        for kw in selected_keywords:
            # Simple semantic grouping by main topic words
            words = set(kw.lower().split())
            selected_groups.update(words)

        diverse_candidates = []
        for candidate in candidates:
            # Calculate diversity score
            candidate_words = set(candidate.keyword.lower().split())
            overlap = len(candidate_words & selected_groups)
            diversity_score = 1 - (overlap / len(candidate_words)) if candidate_words else 0

            if diversity_score >= min_diversity_score:
                diverse_candidates.append(candidate)

        logger.info(f"Filtered to {len(diverse_candidates)} diverse candidates from {len(candidates)}")
        return diverse_candidates


def get_keyword_strategy() -> ProductCategoryKeywordGenerator:
    """Get singleton instance of keyword strategy"""
    return ProductCategoryKeywordGenerator()
