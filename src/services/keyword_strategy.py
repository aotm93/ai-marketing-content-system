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
import re
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.services.product_knowledge import ProductCatalogMatcher

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
    page_type: str = "category_support"
    target_category: Optional[str] = None
    target_category_url: Optional[str] = None
    target_category_slug: Optional[str] = None
    target_tag: Optional[str] = None
    target_tag_url: Optional[str] = None
    target_tag_slug: Optional[str] = None
    primary_taxonomy_type: Optional[str] = None
    primary_taxonomy_name: Optional[str] = None
    primary_taxonomy_slug: Optional[str] = None
    primary_taxonomy_url: Optional[str] = None
    route_target_type: Optional[str] = None
    route_target_name: Optional[str] = None
    route_target_url: Optional[str] = None
    supporting_products: List[Dict[str, Any]] = field(default_factory=list)
    supporting_tags: List[str] = field(default_factory=list)
    decision_questions: List[str] = field(default_factory=list)
    commercial_facts: List[str] = field(default_factory=list)
    commercial_score: float = 0.0
    routing_score: float = 0.0
    required_sections: List[str] = field(default_factory=list)
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
        self.catalog_matcher = ProductCatalogMatcher()
        logger.info("ContentAwareKeywordGenerator initialized")

    PRODUCT_TERM_PATTERN = re.compile(
        r"(fine mist spray bottle|spray bottle|foam bottle|pump bottle|dropper bottle|"
        r"lotion bottle|bottle|jar|container|tube|sprayer|pump|foamer)",
        re.IGNORECASE,
    )
    CAPACITY_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s*(ml|l|oz|g)\b", re.IGNORECASE)
    DESCRIPTOR_DROP_TERMS = {"empty", "wholesale", "container", "containers"}

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

        if getattr(self.website_profile, "category_details", None) or getattr(self.website_profile, "product_records", None):
            catalog_keywords = self._generate_catalog_keywords(limit=max(limit // 2, 12))
            keywords.extend(catalog_keywords)

        # Generate keywords for each journey stage
        for stage, stage_ratio in journey_mix.items():
            stage_limit = int(limit * stage_ratio)
            stage_keywords = self._generate_stage_keywords(stage, stage_limit, intent_mix)
            keywords.extend(stage_keywords)

        keywords = self._deduplicate_candidates(keywords)

        # Enrich with real search volume data from API
        keywords = self._enrich_with_api_data(keywords)

        # Sort by routing value first so selected topics map cleanly to landing pages.
        keywords.sort(
            key=lambda k: (
                k.routing_score,
                k.commercial_score,
                k.search_volume or 0,
                1 if k.is_long_tail else 0,
            ),
            reverse=True,
        )

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

    def _generate_catalog_keywords(self, limit: int) -> List[KeywordCandidate]:
        """Generate product/category-backed topics with direct commercial context."""
        profile = self.website_profile
        categories = getattr(profile, "category_details", [])[:6]
        tags = getattr(profile, "tag_details", [])[:6]
        products = getattr(profile, "product_records", [])[:10]

        candidates: List[KeywordCandidate] = []

        for category in categories:
            category_name = category.name
            candidates.extend([
                self._build_candidate(
                    keyword=f"{category_name} wholesale",
                    intent=SearchIntent.TRANSACTIONAL,
                    journey_stage=CustomerJourneyStage.DECISION,
                    category=category_name,
                    semantic_group=f"catalog_{category.slug or category_name}",
                ),
                self._build_candidate(
                    keyword=f"{category_name} supplier",
                    intent=SearchIntent.COMMERCIAL,
                    journey_stage=CustomerJourneyStage.CONSIDERATION,
                    category=category_name,
                    semantic_group=f"catalog_{category.slug or category_name}",
                ),
                self._build_candidate(
                    keyword=f"{category_name} MOQ and lead time",
                    intent=SearchIntent.TRANSACTIONAL,
                    journey_stage=CustomerJourneyStage.DECISION,
                    category=category_name,
                    semantic_group=f"catalog_ops_{category.slug or category_name}",
                ),
            ])
            if len(candidates) >= limit:
                break

        for product in products:
            descriptor = self._build_product_keyword_descriptor(product)
            if not descriptor:
                continue

            candidates.extend([
                self._build_candidate(
                    keyword=f"{descriptor} wholesale",
                    intent=SearchIntent.TRANSACTIONAL,
                    journey_stage=CustomerJourneyStage.DECISION,
                    category=product.category_names[0] if product.category_names else "product",
                    semantic_group=f"product_{product.slug or descriptor}",
                ),
                self._build_candidate(
                    keyword=f"{descriptor} supplier MOQ",
                    intent=SearchIntent.TRANSACTIONAL,
                    journey_stage=CustomerJourneyStage.DECISION,
                    category=product.category_names[0] if product.category_names else "product",
                    semantic_group=f"product_ops_{product.slug or descriptor}",
                ),
            ])
            if product.use_case:
                candidates.append(
                    self._build_candidate(
                        keyword=f"{descriptor} for {product.use_case.lower()}",
                        intent=SearchIntent.COMMERCIAL,
                        journey_stage=CustomerJourneyStage.CONSIDERATION,
                        category=product.category_names[0] if product.category_names else "product",
                        semantic_group=f"use_case_{product.slug or descriptor}",
                    )
                )

            if len(candidates) >= limit:
                break

        for tag in tags:
            tag_name = getattr(tag, "name", str(tag))
            tag_slug = getattr(tag, "slug", tag_name)
            if not tag_name:
                continue

            candidates.extend([
                self._build_candidate(
                    keyword=f"{tag_name} packaging wholesale",
                    intent=SearchIntent.COMMERCIAL,
                    journey_stage=CustomerJourneyStage.CONSIDERATION,
                    category=tag_name,
                    semantic_group=f"tag_{tag_slug}",
                ),
                self._build_candidate(
                    keyword=f"{tag_name} bottle supplier",
                    intent=SearchIntent.TRANSACTIONAL,
                    journey_stage=CustomerJourneyStage.DECISION,
                    category=tag_name,
                    semantic_group=f"tag_ops_{tag_slug}",
                ),
            ])
            if len(candidates) >= limit:
                break

        return self._deduplicate_candidates(candidates)[:limit]

    def _build_candidate(
        self,
        keyword: str,
        intent: SearchIntent,
        journey_stage: CustomerJourneyStage,
        category: str,
        semantic_group: str,
    ) -> KeywordCandidate:
        """Build a keyword candidate enriched with category/product context."""
        catalog_match = self.catalog_matcher.match_topic(
            keyword,
            getattr(self.website_profile, "category_details", []),
            getattr(self.website_profile, "product_records", []),
            getattr(self.website_profile, "tag_details", []),
        )

        commercial_score = min(
            1.0,
            0.35
            + (0.15 if (catalog_match.target_category_name or catalog_match.target_tag_name) else 0)
            + min(len(catalog_match.supporting_products), 3) * 0.12
            + min(len(catalog_match.commercial_facts), 4) * 0.08,
        )
        route_target_type, route_target_name, route_target_url = self._infer_route_target(keyword, catalog_match)
        routing_score = self._score_routing_priority(catalog_match, route_target_type, keyword)

        return KeywordCandidate(
            keyword=keyword,
            intent=intent,
            journey_stage=journey_stage,
            category=category,
            difficulty_estimate="low" if len(keyword.split()) >= 4 else "medium",
            is_long_tail=len(keyword.split()) >= 4,
            semantic_group=semantic_group,
            page_type=catalog_match.page_type,
            target_category=catalog_match.target_category_name,
            target_category_url=catalog_match.target_category_url,
            target_category_slug=catalog_match.target_category_slug,
            target_tag=catalog_match.target_tag_name,
            target_tag_url=catalog_match.target_tag_url,
            target_tag_slug=catalog_match.target_tag_slug,
            primary_taxonomy_type=catalog_match.primary_taxonomy_type,
            primary_taxonomy_name=catalog_match.primary_taxonomy_name,
            primary_taxonomy_slug=catalog_match.primary_taxonomy_slug,
            primary_taxonomy_url=catalog_match.primary_taxonomy_url,
            route_target_type=route_target_type,
            route_target_name=route_target_name,
            route_target_url=route_target_url,
            supporting_products=catalog_match.supporting_products,
            supporting_tags=catalog_match.supporting_tags,
            decision_questions=catalog_match.decision_questions,
            commercial_facts=catalog_match.commercial_facts,
            commercial_score=round(commercial_score, 2),
            routing_score=round(routing_score, 2),
            required_sections=self._default_required_sections(catalog_match.page_type),
        )

    def _infer_route_target(self, keyword: str, catalog_match) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Pick the most natural landing page for the article CTA path."""
        supporting_products = catalog_match.supporting_products or []
        if self._is_product_led_keyword(keyword, supporting_products):
            product = supporting_products[0]
            return "product", product.get("name"), product.get("url")

        if catalog_match.primary_taxonomy_name:
            return (
                catalog_match.primary_taxonomy_type,
                catalog_match.primary_taxonomy_name,
                catalog_match.primary_taxonomy_url,
            )

        if supporting_products:
            product = supporting_products[0]
            return "product", product.get("name"), product.get("url")

        return None, None, None

    def _is_product_led_keyword(self, keyword: str, supporting_products: List[Dict[str, Any]]) -> bool:
        """Detect product-specific queries that should land on a product page first."""
        if not keyword or not supporting_products:
            return False

        keyword_lower = keyword.lower()
        if any(term in keyword_lower for term in ["sku", "part number", "30ml", "50ml", "100ml"]):
            return True

        product = supporting_products[0]
        product_name = (product.get("name") or "").lower()
        if product_name and product_name in keyword_lower:
            return True

        product_terms = [
            str(product.get("capacity", "")).lower(),
            str(product.get("material", "")).lower(),
            str(product.get("closure_type", "")).lower(),
        ]
        matched_terms = [term for term in product_terms if term and term in keyword_lower]
        return len(matched_terms) >= 2

    def _score_routing_priority(self, catalog_match, route_target_type: Optional[str], keyword: str) -> float:
        """Reward topics that route cleanly into catalog landing pages."""
        score = 0.2
        if catalog_match.primary_taxonomy_type == "tag":
            score += 0.26
        elif catalog_match.primary_taxonomy_type == "category":
            score += 0.22

        if route_target_type == "product":
            score += 0.28

        if catalog_match.primary_taxonomy_url:
            score += 0.08
        if catalog_match.supporting_products:
            score += min(len(catalog_match.supporting_products), 3) * 0.06
        if catalog_match.decision_questions:
            score += min(len(catalog_match.decision_questions), 4) * 0.04
        if catalog_match.commercial_facts:
            score += min(len(catalog_match.commercial_facts), 4) * 0.025
        if len(keyword.split()) >= 4:
            score += 0.04
        return min(score, 1.0)

    def _build_product_keyword_descriptor(self, product) -> str:
        """Create a compact, SEO-friendly product descriptor without repeated prefixes."""
        capacity_phrase = self._extract_capacity_phrase(product)
        material = self._normalize_acronym_token(getattr(product, "material", ""))
        product_term = self._extract_product_term_phrase(product)

        parts: List[str] = []
        for part in [capacity_phrase, material, product_term]:
            normalized = part.strip()
            if normalized and normalized.lower() not in self.DESCRIPTOR_DROP_TERMS and normalized not in parts:
                parts.append(normalized)

        if not parts:
            name = (getattr(product, "name", "") or "").strip()
            parts = [token for token in name.split()[:6] if token]

        descriptor = " ".join(parts)
        descriptor = re.sub(r"\s+", " ", descriptor).strip()
        return descriptor[:120]

    def _extract_capacity_phrase(self, product) -> str:
        """Build a single capacity phrase from explicit and inferred capacity values."""
        raw_values: List[str] = []
        if getattr(product, "capacity", None):
            raw_values.append(str(product.capacity))

        name = str(getattr(product, "name", "") or "")
        for amount, unit in self.CAPACITY_PATTERN.findall(name):
            raw_values.append(f"{amount}{unit.lower()}")

        normalized = []
        for value in raw_values:
            compact = re.sub(r"\s+", "", value.lower())
            match = self.CAPACITY_PATTERN.search(compact)
            if not match:
                continue
            normalized_value = f"{match.group(1)}{match.group(2).lower()}"
            if normalized_value not in normalized:
                normalized.append(normalized_value)

        if not normalized:
            return ""
        if len(normalized) == 1:
            return normalized[0]

        first_match = self.CAPACITY_PATTERN.search(normalized[0])
        if first_match:
            shared_unit = first_match.group(2).lower()
            numeric_values = []
            for item in normalized:
                match = self.CAPACITY_PATTERN.search(item)
                if not match or match.group(2).lower() != shared_unit:
                    numeric_values = []
                    break
                numeric_values.append(float(match.group(1)))
            if len(numeric_values) >= 2:
                return f"{self._format_number(min(numeric_values))}-{self._format_number(max(numeric_values))}{shared_unit}"

        return "/".join(normalized[:2])

    def _extract_product_term_phrase(self, product) -> str:
        """Infer the core product term (e.g. spray bottle, foam bottle)."""
        closure = str(getattr(product, "closure_type", "") or "")
        name = str(getattr(product, "name", "") or "")
        if not (closure or name):
            return ""

        # Prefer product-name matches so we keep a noun like "bottle" instead of only "pump".
        match = self.PRODUCT_TERM_PATTERN.search(name)
        if not match and closure:
            match = self.PRODUCT_TERM_PATTERN.search(closure)
        if match:
            term = match.group(1)
            if term.lower() in {"pump", "sprayer", "foamer"}:
                noun_match = re.search(
                    r"(?:[a-z]+\s+){0,2}(bottle|jar|container|tube)",
                    name,
                    re.IGNORECASE,
                )
                if noun_match:
                    return self._normalize_acronym_token(noun_match.group(0))
            return self._normalize_acronym_token(term)

        tokens = [token for token in name.split() if token]
        return self._normalize_acronym_token(" ".join(tokens[-2:])) if tokens else ""

    def _normalize_acronym_token(self, text: str) -> str:
        """Preserve packaging acronyms while keeping other tokens readable."""
        if not text:
            return ""
        acronyms = {"hdpe", "ldpe", "pet", "pvc", "pp", "abs", "oem", "odm"}
        words = []
        for raw in text.split():
            cleaned = raw.strip()
            if not cleaned:
                continue
            if cleaned.lower() in acronyms:
                words.append(cleaned.upper())
            else:
                words.append(cleaned.capitalize())
        return " ".join(words)

    def _format_number(self, value: float) -> str:
        """Render float values without trailing .0."""
        if value.is_integer():
            return str(int(value))
        return str(round(value, 2)).rstrip("0").rstrip(".")

    def _default_required_sections(self, page_type: str) -> List[str]:
        """Map page types to required content sections."""
        mapping = {
            "category_support": ["summary", "selection_criteria", "faq"],
            "product_selection": ["summary", "comparison_table", "buyer_checklist", "faq"],
            "spec_comparison": ["summary", "comparison_table", "trade_offs", "faq"],
            "wholesale_faq": ["summary", "moq_and_lead_time", "customization", "faq"],
        }
        return mapping.get(page_type, ["summary", "faq"])

    def _deduplicate_candidates(self, candidates: List[KeywordCandidate]) -> List[KeywordCandidate]:
        """Deduplicate keyword candidates by normalized keyword."""
        seen = set()
        deduped = []
        for candidate in candidates:
            normalized = candidate.keyword.lower().strip()
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(candidate)
        return deduped

    def infer_route_counts_from_keywords(self, keywords: List[str]) -> Dict[str, int]:
        """Estimate how today's published keywords are distributed across route types."""
        counts = {"category": 0, "tag": 0, "product": 0}
        if not self.website_profile:
            return counts

        for keyword in keywords or []:
            match = self.catalog_matcher.match_topic(
                keyword,
                getattr(self.website_profile, "category_details", []),
                getattr(self.website_profile, "product_records", []),
                getattr(self.website_profile, "tag_details", []),
            )
            route_type, _, _ = self._infer_route_target(keyword, match)
            if route_type in counts:
                counts[route_type] += 1
        return counts

    def balance_route_coverage(
        self,
        candidates: List[KeywordCandidate],
        selected_keywords: List[str],
        recent_keywords_7d: Optional[List[str]] = None,
    ) -> List[KeywordCandidate]:
        """Boost underrepresented route types so the site distributes internal traffic more evenly."""
        if not candidates:
            return candidates

        route_counts_today = self.infer_route_counts_from_keywords(selected_keywords)
        route_counts_week = self.infer_route_counts_from_keywords(recent_keywords_7d or selected_keywords)

        for candidate in candidates:
            route_type = candidate.route_target_type or candidate.primary_taxonomy_type or "category"
            boost = self._route_balance_boost(route_type, route_counts_today, strong=0.12, light=0.06)
            boost += self._route_balance_boost(route_type, route_counts_week, strong=0.1, light=0.05)
            candidate.routing_score = round(min(1.0, candidate.routing_score + boost), 2)

        candidates.sort(
            key=lambda k: (
                k.routing_score,
                k.commercial_score,
                k.search_volume or 0,
                1 if k.is_long_tail else 0,
            ),
            reverse=True,
        )
        return candidates

    def _route_balance_boost(
        self,
        route_type: str,
        route_counts: Dict[str, int],
        strong: float,
        light: float,
    ) -> float:
        """Return a boost when a route type is underrepresented in a given time window."""
        if not route_counts:
            return 0.0

        least_count = min(route_counts.values())
        route_count = route_counts.get(route_type, 0)
        if route_count == least_count:
            return strong
        if route_count == least_count + 1:
            return light
        return 0.0

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

                keywords.append(self._build_candidate(
                    keyword=keyword,
                    intent=SearchIntent.INFORMATIONAL,
                    journey_stage=CustomerJourneyStage.AWARENESS,
                    category=category,
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

                keywords.append(self._build_candidate(
                    keyword=keyword,
                    intent=SearchIntent.COMMERCIAL,
                    journey_stage=CustomerJourneyStage.CONSIDERATION,
                    category=category,
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

                keywords.append(self._build_candidate(
                    keyword=keyword,
                    intent=SearchIntent.TRANSACTIONAL,
                    journey_stage=CustomerJourneyStage.DECISION,
                    category=category,
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
                semantic_group="default",
                page_type="wholesale_faq",
                commercial_score=0.4,
                required_sections=self._default_required_sections("wholesale_faq"),
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
