"""
Website Content Analyzer Service
Analyzes existing website content to understand business domain and generate relevant keywords

Features:
- Extract product categories from existing posts
- Identify industry terminology and themes
- Analyze customer journey stages
- Generate context-aware keyword suggestions
"""

import logging
import re
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass, field
from collections import Counter

from src.services.product_knowledge import (
    CategoryInsight,
    ProductInsight,
    ProductKnowledgeExtractor,
)

logger = logging.getLogger(__name__)


CATEGORY_STOPWORDS = {
    "a", "an", "and", "any", "best", "bulk", "custom", "for", "free", "how",
    "in", "my", "of", "or", "our", "the", "their", "these", "this", "those",
    "to", "top", "your"
}


@dataclass
class WebsiteProfile:
    """Website business profile extracted from content analysis"""
    product_categories: List[str]  # e.g., ["cosmetic bottles", "pump bottles", "cream jars"]
    industry_terms: List[str]      # e.g., ["packaging", "wholesale", "bulk order"]
    content_themes: List[str]      # e.g., ["sustainability", "custom branding", "quality"]
    target_audience: str           # e.g., "B2B wholesale buyers"
    business_type: str             # e.g., "packaging supplier"
    sample_keywords: List[str]     # Actual keywords found in content
    customer_pain_points: List[str] = field(default_factory=list)
    category_details: List[CategoryInsight] = field(default_factory=list)
    tag_details: List[CategoryInsight] = field(default_factory=list)
    product_records: List[ProductInsight] = field(default_factory=list)


class WebsiteAnalyzer:
    """
    Analyzes website content to understand business domain
    Uses existing posts to generate intelligent keyword strategies
    """

    def __init__(self, wordpress_client):
        """
        Initialize analyzer with WordPress client

        Args:
            wordpress_client: WordPressClient instance for fetching content
        """
        self.wp_client = wordpress_client
        self._cached_profile: Optional[WebsiteProfile] = None
        self.product_extractor = ProductKnowledgeExtractor()
        logger.info("WebsiteAnalyzer initialized")

    async def analyze_website(self, max_posts: int = 50) -> WebsiteProfile:
        """
        Analyze website content to build business profile

        Args:
            max_posts: Maximum number of posts to analyze

        Returns:
            WebsiteProfile with extracted business intelligence
        """
        logger.info(f"Starting website analysis (max {max_posts} posts)")

        # Fetch recent published posts
        posts = await self.wp_client.get_posts(
            per_page=min(max_posts, 100),
            status="publish"
        )

        if not posts:
            logger.warning("No published posts found, returning default profile")
            return self._get_default_profile()

        logger.info(f"Analyzing {len(posts)} posts")

        # Extract text content from all posts
        all_titles = []
        all_content = []
        all_excerpts = []

        for post in posts:
            title = self._clean_html(post.get("title", {}).get("rendered", ""))
            content = self._clean_html(post.get("content", {}).get("rendered", ""))
            excerpt = self._clean_html(post.get("excerpt", {}).get("rendered", ""))

            all_titles.append(title)
            all_content.append(content)
            all_excerpts.append(excerpt)

        category_details, tag_details, product_records = await self._analyze_catalog(max_posts)

        # Analyze content
        product_categories = self._extract_product_categories(all_titles, all_content)
        product_categories.extend(category.name for category in category_details)
        product_categories.extend(
            category_name
            for product in product_records
            for category_name in product.category_names
        )
        product_categories = self._dedupe_preserve_order(product_categories)[:20]

        industry_terms = self._extract_industry_terms(all_titles, all_content)
        industry_terms.extend(
            tag.name if isinstance(tag, CategoryInsight) else str(tag)
            for tag in tag_details
        )
        industry_terms.extend(
            term
            for product in product_records
            for term in [product.material, product.use_case, product.closure_type]
            if term
        )
        industry_terms = self._dedupe_preserve_order(industry_terms)[:25]

        content_themes = self._extract_themes(all_titles, all_content)
        target_audience = self._identify_target_audience(all_content)
        business_type = self._identify_business_type(all_titles, all_content)
        sample_keywords = self._extract_sample_keywords(all_titles)
        sample_keywords.extend([product.name for product in product_records[:10]])
        sample_keywords = self._dedupe_preserve_order(sample_keywords)[:20]
        customer_pain_points = self._derive_customer_pain_points(product_records, category_details)

        profile = WebsiteProfile(
            product_categories=product_categories,
            industry_terms=industry_terms,
            content_themes=content_themes,
            target_audience=target_audience,
            business_type=business_type,
            sample_keywords=sample_keywords,
            customer_pain_points=customer_pain_points,
            category_details=category_details,
            tag_details=tag_details,
            product_records=product_records,
        )

        self._cached_profile = profile
        logger.info(f"Website analysis complete: {len(product_categories)} categories, "
                   f"{len(industry_terms)} industry terms")

        return profile

    async def _analyze_catalog(self, max_items: int) -> tuple[List[CategoryInsight], List[CategoryInsight], List[ProductInsight]]:
        """Fetch structured category, tag, and product data when available."""
        category_details: List[CategoryInsight] = []
        tag_details: List[CategoryInsight] = []
        product_records: List[ProductInsight] = []

        category_terms = []
        tag_terms = []
        try:
            category_terms = await self.wp_client.get_taxonomy_terms("product_cat", per_page=100)
        except Exception as exc:
            logger.debug(f"Product category fetch unavailable: {exc}")
            try:
                category_terms = await self.wp_client.get_categories(per_page=100)
            except Exception as inner_exc:
                logger.debug(f"Fallback category fetch unavailable: {inner_exc}")

        try:
            tag_terms = await self.wp_client.get_taxonomy_terms("product_tag", per_page=100)
        except Exception as exc:
            logger.debug(f"Product tag fetch unavailable: {exc}")
            try:
                tag_terms = await self.wp_client.get_tags(per_page=100)
            except Exception as inner_exc:
                logger.debug(f"Fallback tag fetch unavailable: {inner_exc}")

        category_details = self.product_extractor.build_category_insights(category_terms)
        category_lookup = {category.id: category for category in category_details if category.id is not None}
        tag_details = self.product_extractor.build_category_insights(tag_terms)[:20]
        tag_lookup = {tag.id: tag.name for tag in tag_details if tag.id is not None}

        product_endpoint_candidates = ["product", "products"]
        try:
            types = await self.wp_client.get_post_types()
            product_endpoint_candidates = [
                endpoint for endpoint in product_endpoint_candidates if endpoint in types
            ] or product_endpoint_candidates
        except Exception as exc:
            logger.debug(f"Could not inspect post types: {exc}")

        raw_products: List[Dict[str, Any]] = []
        for endpoint in product_endpoint_candidates:
            try:
                raw_products = await self.wp_client.get_content_items(
                    endpoint,
                    per_page=min(max_items, 100),
                    status="publish",
                )
                if raw_products:
                    logger.info(f"Catalog scan found {len(raw_products)} items from '{endpoint}'")
                    break
            except Exception as exc:
                logger.debug(f"Product endpoint '{endpoint}' unavailable: {exc}")

        for item in raw_products:
            product = self.product_extractor.extract_product_insight(
                item,
                category_lookup=category_lookup,
                tag_lookup=tag_lookup,
            )
            if product.name:
                product_records.append(product)

        return category_details, tag_details, product_records[:max_items]

    def _clean_html(self, html_text: str) -> str:
        """Remove HTML tags and clean text"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_product_categories(self, titles: List[str], contents: List[str]) -> List[str]:
        """
        Extract product categories from content
        Uses pattern matching and frequency analysis
        """
        categories = []

        # Common packaging product patterns
        product_patterns = [
            r'\b(?:[a-z0-9-]+\s+){0,2}bottles?\b',
            r'\b(?:[a-z0-9-]+\s+){0,2}jars?\b',
            r'\b(?:[a-z0-9-]+\s+){0,2}containers?\b',
            r'\b(?:[a-z0-9-]+\s+){0,2}tubes?\b',
            r'\b(?:[a-z0-9-]+\s+){0,2}pumps?\b',
            r'\b(?:[a-z0-9-]+\s+){0,2}caps?\b',
            r'\b(?:[a-z0-9-]+\s+){0,2}packaging\b',
            r'\b(?:[a-z0-9-]+\s+){0,2}dispensers?\b',
        ]

        all_text = ' '.join(titles + contents).lower()

        for pattern in product_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches:
                category = self._normalize_category_phrase(match)
                if category:
                    categories.append(category)

        # Count frequency and return top categories
        category_counts = Counter(categories)
        top_categories = [cat for cat, count in category_counts.most_common(15)]

        logger.info(f"Extracted {len(top_categories)} product categories")
        return top_categories

    def _normalize_category_phrase(self, phrase: str) -> str:
        """Normalize extracted noun phrases and remove low-value fragments."""
        cleaned = re.sub(r'[^a-z0-9\s-]', ' ', phrase.lower())
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if not cleaned:
            return ""

        words = cleaned.split()
        if not words:
            return ""

        head = words[-1]
        modifiers = [
            word for word in words[:-1]
            if len(word) > 2 and word not in CATEGORY_STOPWORDS
        ]

        if head in CATEGORY_STOPWORDS:
            return ""

        if not modifiers and head in {"packaging"}:
            return ""

        normalized = " ".join(modifiers + [head]).strip()
        if len(normalized) < 4:
            return ""

        return normalized

    def _extract_industry_terms(self, titles: List[str], contents: List[str]) -> List[str]:
        """Extract industry-specific terminology"""
        industry_keywords = [
            'wholesale', 'bulk', 'supplier', 'manufacturer', 'packaging',
            'custom', 'private label', 'OEM', 'ODM', 'MOQ',
            'cosmetic', 'beauty', 'skincare', 'health', 'wellness',
            'eco-friendly', 'sustainable', 'recyclable', 'biodegradable',
            'FDA approved', 'BPA free', 'food grade', 'pharmaceutical',
            'branding', 'logo', 'customization', 'design'
        ]

        all_text = ' '.join(titles + contents).lower()
        found_terms = []

        for term in industry_keywords:
            if term.lower() in all_text:
                found_terms.append(term)

        logger.info(f"Found {len(found_terms)} industry terms")
        return found_terms[:20]  # Limit to top 20

    def _extract_themes(self, titles: List[str], contents: List[str]) -> List[str]:
        """Extract content themes and topics"""
        theme_keywords = {
            'quality': ['quality', 'premium', 'high-quality', 'durable', 'reliable'],
            'sustainability': ['eco', 'sustainable', 'green', 'recyclable', 'environment'],
            'customization': ['custom', 'personalized', 'branding', 'logo', 'design'],
            'innovation': ['innovative', 'new', 'advanced', 'technology', 'modern'],
            'safety': ['safe', 'FDA', 'certified', 'approved', 'compliant'],
            'cost': ['affordable', 'competitive', 'price', 'cost-effective', 'value']
        }

        all_text = ' '.join(titles + contents).lower()
        found_themes = []

        for theme, keywords in theme_keywords.items():
            if any(kw in all_text for kw in keywords):
                found_themes.append(theme)

        return found_themes

    def _identify_target_audience(self, contents: List[str]) -> str:
        """Identify target audience from content"""
        all_text = ' '.join(contents).lower()

        b2b_indicators = ['wholesale', 'bulk', 'supplier', 'manufacturer', 'distributor', 'business']
        b2c_indicators = ['buy now', 'shop', 'cart', 'customer', 'consumer']

        b2b_count = sum(1 for indicator in b2b_indicators if indicator in all_text)
        b2c_count = sum(1 for indicator in b2c_indicators if indicator in all_text)

        if b2b_count > b2c_count:
            return "B2B wholesale buyers"
        elif b2c_count > b2b_count:
            return "B2C consumers"
        else:
            return "Mixed B2B/B2C"

    def _identify_business_type(self, titles: List[str], contents: List[str]) -> str:
        """Identify business type from content"""
        all_text = ' '.join(titles + contents).lower()

        if 'packaging' in all_text and ('supplier' in all_text or 'manufacturer' in all_text):
            return "packaging supplier"
        elif 'cosmetic' in all_text or 'beauty' in all_text:
            return "cosmetic packaging supplier"
        else:
            return "product supplier"

    def _extract_sample_keywords(self, titles: List[str]) -> List[str]:
        """Extract actual keywords from post titles"""
        # Clean and extract meaningful phrases from titles
        keywords = []
        for title in titles[:20]:  # Use first 20 titles
            # Remove common words
            cleaned = re.sub(r'\b(the|a|an|and|or|but|in|on|at|to|for|of|with|by)\b', '', title.lower())
            cleaned = cleaned.strip()
            if len(cleaned) > 10:  # Only meaningful phrases
                keywords.append(cleaned)

        return keywords[:15]  # Return top 15

    def _derive_customer_pain_points(
        self,
        product_records: List[ProductInsight],
        category_details: List[CategoryInsight],
    ) -> List[str]:
        """Derive recurring buyer pain points from catalog signals."""
        pain_points = [
            "finding the right bottle or jar specification for the product application",
            "comparing MOQ, lead time, and customization options before bulk ordering",
            "checking material, closure, and decoration compatibility before finalizing samples",
        ]

        if any(product.certifications for product in product_records):
            pain_points.append("confirming certifications and compliance requirements before purchase")
        if any(product.neck_finish for product in product_records):
            pain_points.append("verifying neck finish and closure fitment to avoid compatibility issues")
        if category_details:
            pain_points.append(f"shortlisting the best option across {len(category_details)} packaging categories")

        return self._dedupe_preserve_order(pain_points)[:6]

    def _dedupe_preserve_order(self, items: List[str]) -> List[str]:
        """Return unique non-empty strings while preserving order."""
        seen = set()
        deduped = []
        for item in items:
            normalized = (item or "").strip()
            if normalized and normalized.lower() not in seen:
                seen.add(normalized.lower())
                deduped.append(normalized)
        return deduped

    def _get_default_profile(self) -> WebsiteProfile:
        """Return default profile when no content is available"""
        return WebsiteProfile(
            product_categories=["bottles", "jars", "containers"],
            industry_terms=["packaging", "wholesale", "supplier"],
            content_themes=["quality", "customization"],
            target_audience="B2B wholesale buyers",
            business_type="packaging supplier",
            sample_keywords=[],
            customer_pain_points=[
                "comparing MOQ and lead time across suppliers",
                "choosing the right packaging format for the product",
                "evaluating customization and compliance requirements",
            ],
        )

    async def get_cached_profile(self) -> Optional[WebsiteProfile]:
        """Get cached profile if available"""
        return self._cached_profile
