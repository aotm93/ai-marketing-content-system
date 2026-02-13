"""
Keyword Strategy Service
Implements intelligent keyword generation based on website content analysis

Features:
- Content-aware keyword generation (learns from existing website content)
- Customer journey mapping (awareness → consideration → decision)
- Long-tail keyword focus
- Semantic diversity checking
- B2B buyer journey optimization
"""

import logging
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SearchIntent(str, Enum):
    """Search intent types"""
    INFORMATIONAL = "informational"  # How-to, guides, what is
    COMMERCIAL = "commercial"        # Best, review, comparison
    TRANSACTIONAL = "transactional"  # Buy, price, wholesale
    NAVIGATIONAL = "navigational"    # Brand, specific product


class CustomerJourneyStage(str, Enum):
    """Customer journey stages"""
    AWARENESS = "awareness"          # Problem recognition
    CONSIDERATION = "consideration"  # Solution exploration
    DECISION = "decision"           # Product selection


@dataclass
class KeywordCandidate:
    """Keyword candidate with metadata"""
    keyword: str
    intent: SearchIntent
    journey_stage: CustomerJourneyStage
    category: str
    difficulty_estimate: str  # low, medium, high
    is_long_tail: bool
    semantic_group: str  # For avoiding cannibalization
    # Real data from API (optional, populated when API is available)
    search_volume: Optional[int] = None
    difficulty_score: Optional[int] = None  # 0-100 numeric score


class ContentAwareKeywordGenerator:
    """
    Generates keywords based on website content analysis
    Adapts to business domain automatically
    """

    def __init__(self, website_profile=None):
        """
        Initialize with website profile

        Args:
            website_profile: WebsiteProfile from website analyzer (optional)
        """
        self.website_profile = website_profile
        logger.info("ContentAwareKeywordGenerator initialized")

    def set_website_profile(self, profile):
        """Update website profile"""
        self.website_profile = profile
        logger.info("Website profile updated")

    def generate_keyword_pool(
        self,
        limit: int = 100,
        intent_mix: Optional[Dict[SearchIntent, float]] = None,
        journey_mix: Optional[Dict[CustomerJourneyStage, float]] = None
    ) -> List[KeywordCandidate]:
        """
        Generate diverse keyword pool based on website content

        Args:
            limit: Maximum number of keywords
            intent_mix: Distribution of search intents
            journey_mix: Distribution of customer journey stages

        Returns:
            List of keyword candidates
        """
        if not self.website_profile:
            logger.warning("No website profile available, using default keywords")
            return self._generate_default_keywords(limit)

        # Default mix for B2B: focus on awareness + consideration
        if intent_mix is None:
            intent_mix = {
                SearchIntent.INFORMATIONAL: 0.4,
                SearchIntent.COMMERCIAL: 0.4,
                SearchIntent.TRANSACTIONAL: 0.2
            }

        if journey_mix is None:
            journey_mix = {
                CustomerJourneyStage.AWARENESS: 0.3,
                CustomerJourneyStage.CONSIDERATION: 0.4,
                CustomerJourneyStage.DECISION: 0.3
            }

        keywords = []

        # Generate keywords for each journey stage
        for stage, stage_ratio in journey_mix.items():
            stage_limit = int(limit * stage_ratio)
            stage_keywords = self._generate_stage_keywords(stage, stage_limit, intent_mix)
            keywords.extend(stage_keywords)

        # Enrich with real search volume data from API
        keywords = self._enrich_with_api_data(keywords)

        # Sort by search volume (descending) if available
        keywords.sort(key=lambda k: (k.search_volume or 0), reverse=True)

        logger.info(f"Generated {len(keywords)} content-aware keywords")
        return keywords[:limit]

    def _enrich_with_api_data(self, keywords: List[KeywordCandidate]) -> List[KeywordCandidate]:
        """
        Enrich keywords with real search volume and difficulty data from API.
        Falls back to estimates if API is unavailable.
        """
        try:
            # Import here to avoid circular dependencies
            import asyncio
            from src.integrations.keyword_client import KeywordClient

            client = KeywordClient(provider='dataforseo')

            # Check if API credentials are configured
            if not client.api_key:
                logger.debug("No API key configured, skipping enrichment")
                return keywords

            # Get unique keywords to query
            unique_keywords = list({k.keyword for k in keywords})

            # Query API for first keyword to get suggestions (limit API calls)
            if unique_keywords:
                # Check if we're already in an event loop
                try:
                    loop = asyncio.get_running_loop()
                    # If we get here, we're in an async context - can't nest loops
                    logger.debug("Already in event loop, using estimate-based enrichment to avoid loop nesting")
                    # Skip API call and use estimates
                    for kw in keywords:
                        kw.difficulty_score = self._estimate_to_score(kw.difficulty_estimate)
                    return keywords
                except RuntimeError:
                    # No loop running, safe to create one and make API call
                    pass
                
                try:
                    # Run async call in sync context (only if no loop is running)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # Get keyword suggestions for the first seed keyword
                    opportunities = loop.run_until_complete(
                        client.get_keyword_suggestions(unique_keywords[0], limit=min(len(unique_keywords), 50))
                    )
                    loop.close()

                    # Create lookup map
                    api_data = {opp.keyword.lower(): opp for opp in opportunities}

                    # Enrich keywords with API data
                    for kw in keywords:
                        keyword_lower = kw.keyword.lower()
                        if keyword_lower in api_data:
                            opp = api_data[keyword_lower]
                            kw.search_volume = opp.volume
                            kw.difficulty_score = opp.difficulty
                            # Update difficulty estimate based on numeric score
                            if opp.difficulty < 30:
                                kw.difficulty_estimate = "low"
                            elif opp.difficulty < 60:
                                kw.difficulty_estimate = "medium"
                            else:
                                kw.difficulty_estimate = "high"
                        else:
                            # Map difficulty_estimate to numeric score as fallback
                            kw.difficulty_score = self._estimate_to_score(kw.difficulty_estimate)

                except Exception as e:
                    logger.warning(f"Could not enrich keywords with API data: {e}")
                    # Fallback: map estimates to scores
                    for kw in keywords:
                        kw.difficulty_score = self._estimate_to_score(kw.difficulty_estimate)
            else:
                # No keywords to enrich, just map estimates
                for kw in keywords:
                    kw.difficulty_score = self._estimate_to_score(kw.difficulty_estimate)

        except ImportError as e:
            logger.debug(f"Could not import KeywordClient: {e}")
            # Fallback: map estimates to scores
            for kw in keywords:
                kw.difficulty_score = self._estimate_to_score(kw.difficulty_estimate)
        except Exception as e:
            logger.warning(f"Error enriching keywords: {e}")
            # Fallback: map estimates to scores
            for kw in keywords:
                kw.difficulty_score = self._estimate_to_score(kw.difficulty_estimate)

        return keywords

    def _estimate_to_score(self, estimate: str) -> int:
        """Convert difficulty estimate string to numeric score."""
        mapping = {
            "low": 25,
            "medium": 50,
            "high": 75
        }
        return mapping.get(estimate.lower(), 50)

    def _generate_stage_keywords(
        self,
        stage: CustomerJourneyStage,
        limit: int,
        intent_mix: Dict[SearchIntent, float]
    ) -> List[KeywordCandidate]:
        """Generate keywords for specific customer journey stage"""

        if stage == CustomerJourneyStage.AWARENESS:
            return self._generate_awareness_keywords(limit, intent_mix)
        elif stage == CustomerJourneyStage.CONSIDERATION:
            return self._generate_consideration_keywords(limit, intent_mix)
        else:  # DECISION
            return self._generate_decision_keywords(limit, intent_mix)

    def _generate_awareness_keywords(
        self,
        limit: int,
        intent_mix: Dict[SearchIntent, float]
    ) -> List[KeywordCandidate]:
        """
        Generate awareness stage keywords (problem recognition)
        Customer doesn't know about your product yet
        """
        keywords = []
        profile = self.website_profile

        # Extract product categories from profile
        categories = profile.product_categories[:5] if profile.product_categories else ["packaging"]
        themes = profile.content_themes[:3] if profile.content_themes else ["quality"]

        # Awareness templates (problem-focused)
        awareness_templates = [
            "how to choose {category}",
            "what is {category}",
            "benefits of {category}",
            "{category} guide",
            "understanding {category}",
            "{theme} {category} explained",
            "why {category} matters",
            "{category} for beginners"
        ]

        for template in awareness_templates:
            if len(keywords) >= limit:
                break

            for category in categories:
                if len(keywords) >= limit:
                    break

                keyword = template.replace("{category}", category)

                # Add theme variation
                if "{theme}" in template and themes:
                    keyword = keyword.replace("{theme}", themes[0])

                keywords.append(KeywordCandidate(
                    keyword=keyword,
                    intent=SearchIntent.INFORMATIONAL,
                    journey_stage=CustomerJourneyStage.AWARENESS,
                    category=category,
                    difficulty_estimate="low" if len(keyword.split()) >= 4 else "medium",
                    is_long_tail=len(keyword.split()) >= 4,
                    semantic_group=f"awareness_{category}"
                ))

        return keywords[:limit]

    def _generate_consideration_keywords(
        self,
        limit: int,
        intent_mix: Dict[SearchIntent, float]
    ) -> List[KeywordCandidate]:
        """
        Generate consideration stage keywords (solution exploration)
        Customer is researching options
        """
        keywords = []
        profile = self.website_profile

        categories = profile.product_categories[:5] if profile.product_categories else ["packaging"]
        industry_terms = profile.industry_terms[:5] if profile.industry_terms else ["wholesale"]

        # Consideration templates (solution-focused)
        consideration_templates = [
            "types of {category}",
            "{category} options",
            "{category} comparison",
            "{industry_term} {category}",
            "{category} for {industry_term}",
            "choosing {category} supplier",
            "{category} materials",
            "{category} features"
        ]

        for template in consideration_templates:
            if len(keywords) >= limit:
                break

            for category in categories:
                if len(keywords) >= limit:
                    break

                keyword = template.replace("{category}", category)

                # Add industry term variation
                if "{industry_term}" in template and industry_terms:
                    keyword = keyword.replace("{industry_term}", industry_terms[0])

                keywords.append(KeywordCandidate(
                    keyword=keyword,
                    intent=SearchIntent.COMMERCIAL,
                    journey_stage=CustomerJourneyStage.CONSIDERATION,
                    category=category,
                    difficulty_estimate="low" if len(keyword.split()) >= 4 else "medium",
                    is_long_tail=len(keyword.split()) >= 4,
                    semantic_group=f"consideration_{category}"
                ))

        return keywords[:limit]

    def _generate_decision_keywords(
        self,
        limit: int,
        intent_mix: Dict[SearchIntent, float]
    ) -> List[KeywordCandidate]:
        """
        Generate decision stage keywords (product selection)
        Customer is ready to buy/contact supplier
        """
        keywords = []
        profile = self.website_profile

        categories = profile.product_categories[:5] if profile.product_categories else ["packaging"]
        industry_terms = profile.industry_terms[:5] if profile.industry_terms else ["wholesale"]

        # Decision templates (product-focused)
        decision_templates = [
            "best {category} supplier",
            "{category} manufacturer",
            "buy {category} wholesale",
            "{category} bulk order",
            "custom {category}",
            "{industry_term} {category} supplier",
            "{category} with logo",
            "affordable {category}"
        ]

        for template in decision_templates:
            if len(keywords) >= limit:
                break

            for category in categories:
                if len(keywords) >= limit:
                    break

                keyword = template.replace("{category}", category)

                # Add industry term variation
                if "{industry_term}" in template and industry_terms:
                    keyword = keyword.replace("{industry_term}", industry_terms[0])

                keywords.append(KeywordCandidate(
                    keyword=keyword,
                    intent=SearchIntent.TRANSACTIONAL,
                    journey_stage=CustomerJourneyStage.DECISION,
                    category=category,
                    difficulty_estimate="medium",
                    is_long_tail=len(keyword.split()) >= 4,
                    semantic_group=f"decision_{category}"
                ))

        return keywords[:limit]

    def _generate_default_keywords(self, limit: int) -> List[KeywordCandidate]:
        """Generate default keywords when no profile available"""
        default_keywords = [
            "packaging bottles wholesale",
            "cosmetic containers supplier",
            "bulk packaging jars",
            "custom bottles with logo",
            "wholesale pump bottles"
        ]

        keywords = []
        for kw in default_keywords[:limit]:
            keywords.append(KeywordCandidate(
                keyword=kw,
                intent=SearchIntent.TRANSACTIONAL,
                journey_stage=CustomerJourneyStage.DECISION,
                category="general",
                difficulty_estimate="medium",
                is_long_tail=len(kw.split()) >= 4,
                semantic_group="default"
            ))

        return keywords

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


def get_keyword_strategy(website_profile=None) -> ContentAwareKeywordGenerator:
    """
    Get keyword strategy instance

    Args:
        website_profile: Optional WebsiteProfile from analyzer

    Returns:
        ContentAwareKeywordGenerator instance
    """
    return ContentAwareKeywordGenerator(website_profile)
