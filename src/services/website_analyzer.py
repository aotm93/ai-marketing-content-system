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
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class WebsiteProfile:
    """Website business profile extracted from content analysis"""
    product_categories: List[str]  # e.g., ["cosmetic bottles", "pump bottles", "cream jars"]
    industry_terms: List[str]      # e.g., ["packaging", "wholesale", "bulk order"]
    content_themes: List[str]      # e.g., ["sustainability", "custom branding", "quality"]
    target_audience: str           # e.g., "B2B wholesale buyers"
    business_type: str             # e.g., "packaging supplier"
    sample_keywords: List[str]     # Actual keywords found in content


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

        # Analyze content
        product_categories = self._extract_product_categories(all_titles, all_content)
        industry_terms = self._extract_industry_terms(all_titles, all_content)
        content_themes = self._extract_themes(all_titles, all_content)
        target_audience = self._identify_target_audience(all_content)
        business_type = self._identify_business_type(all_titles, all_content)
        sample_keywords = self._extract_sample_keywords(all_titles)

        profile = WebsiteProfile(
            product_categories=product_categories,
            industry_terms=industry_terms,
            content_themes=content_themes,
            target_audience=target_audience,
            business_type=business_type,
            sample_keywords=sample_keywords
        )

        self._cached_profile = profile
        logger.info(f"Website analysis complete: {len(product_categories)} categories, "
                   f"{len(industry_terms)} industry terms")

        return profile

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
            r'\b(\w+\s+)?bottles?\b',
            r'\b(\w+\s+)?jars?\b',
            r'\b(\w+\s+)?containers?\b',
            r'\b(\w+\s+)?tubes?\b',
            r'\b(\w+\s+)?pumps?\b',
            r'\b(\w+\s+)?caps?\b',
            r'\b(\w+\s+)?packaging\b',
            r'\b(\w+\s+)?dispensers?\b',
        ]

        all_text = ' '.join(titles + contents).lower()

        for pattern in product_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    category = ' '.join(filter(None, match)).strip()
                else:
                    category = match.strip()
                if category and len(category) > 2:
                    categories.append(category)

        # Count frequency and return top categories
        category_counts = Counter(categories)
        top_categories = [cat for cat, count in category_counts.most_common(15)]

        logger.info(f"Extracted {len(top_categories)} product categories")
        return top_categories

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

    def _get_default_profile(self) -> WebsiteProfile:
        """Return default profile when no content is available"""
        return WebsiteProfile(
            product_categories=["bottles", "jars", "containers"],
            industry_terms=["packaging", "wholesale", "supplier"],
            content_themes=["quality", "customization"],
            target_audience="B2B wholesale buyers",
            business_type="packaging supplier",
            sample_keywords=[]
        )

    async def get_cached_profile(self) -> Optional[WebsiteProfile]:
        """Get cached profile if available"""
        return self._cached_profile

