"""
Brief Builder Agent
Implements P1-5: BriefBuilderAgent

Generates structured content briefs based on opportunity analysis:
- SERP intent analysis
- Content structure recommendations
- Internal linking targets
- CTA suggestions
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class ContentBrief:
    """
    Structured content brief for content creation
    """
    brief_id: str
    target_keyword: str
    target_page: Optional[str] = None
    
    # Content type and intent
    content_type: str = "blog_post"  # blog_post, landing_page, product_page, faq, comparison
    search_intent: str = "informational"  # informational, commercial, transactional, navigational
    
    # Title suggestions
    suggested_titles: List[str] = field(default_factory=list)
    
    # Structure
    recommended_word_count: int = 1500
    required_sections: List[Dict[str, Any]] = field(default_factory=list)
    optional_sections: List[Dict[str, Any]] = field(default_factory=list)
    
    # SEO elements
    meta_description_suggestions: List[str] = field(default_factory=list)
    secondary_keywords: List[str] = field(default_factory=list)
    
    # Internal linking
    internal_link_targets: List[Dict[str, str]] = field(default_factory=list)  # [{url, anchor_text}]
    hub_page: Optional[str] = None  # Topic cluster hub to link to
    
    # CTA
    primary_cta: Optional[str] = None
    secondary_ctas: List[str] = field(default_factory=list)
    
    # Competitors
    competitor_pages: List[str] = field(default_factory=list)
    competitor_insights: Optional[str] = None
    
    # Media
    suggested_images: List[Dict[str, str]] = field(default_factory=list)
    include_video: bool = False
    include_infographic: bool = False
    
    # Quality requirements
    min_seo_score: int = 70
    required_elements: List[str] = field(default_factory=list)  # FAQ, table, list, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brief_id": self.brief_id,
            "target_keyword": self.target_keyword,
            "target_page": self.target_page,
            "content_type": self.content_type,
            "search_intent": self.search_intent,
            "suggested_titles": self.suggested_titles,
            "recommended_word_count": self.recommended_word_count,
            "required_sections": self.required_sections,
            "optional_sections": self.optional_sections,
            "meta_description_suggestions": self.meta_description_suggestions,
            "secondary_keywords": self.secondary_keywords,
            "internal_link_targets": self.internal_link_targets,
            "hub_page": self.hub_page,
            "primary_cta": self.primary_cta,
            "suggested_images": self.suggested_images,
            "min_seo_score": self.min_seo_score,
            "required_elements": self.required_elements
        }


class BriefBuilderAgent(BaseAgent):
    """
    Brief Builder Agent
    
    Creates structured content briefs based on:
    - Target keyword analysis
    - SERP intent detection
    - Competitor analysis
    - Topic cluster mapping
    """
    
    # Intent patterns for classification
    INTENT_PATTERNS = {
        "transactional": ["buy", "price", "cheap", "discount", "order", "purchase", "shop", "deal"],
        "commercial": ["best", "top", "review", "vs", "compare", "alternative", "versus"],
        "informational": ["how to", "what is", "why", "guide", "tutorial", "learn", "meaning"],
        "navigational": ["login", "official", "website", "contact"]
    }
    
    # Content type recommendations based on intent
    CONTENT_TYPE_MAP = {
        "transactional": "landing_page",
        "commercial": "comparison",
        "informational": "blog_post",
        "navigational": "landing_page"
    }
    
    # Section templates for different content types
    SECTION_TEMPLATES = {
        "blog_post": [
            {"name": "Introduction", "type": "intro", "required": True},
            {"name": "Main Content", "type": "body", "required": True},
            {"name": "Key Takeaways", "type": "summary", "required": False},
            {"name": "FAQ", "type": "faq", "required": False},
            {"name": "Conclusion", "type": "conclusion", "required": True}
        ],
        "comparison": [
            {"name": "Introduction", "type": "intro", "required": True},
            {"name": "Quick Comparison Table", "type": "table", "required": True},
            {"name": "Detailed Analysis", "type": "body", "required": True},
            {"name": "Pros and Cons", "type": "pros_cons", "required": True},
            {"name": "Our Recommendation", "type": "recommendation", "required": True},
            {"name": "FAQ", "type": "faq", "required": False}
        ],
        "landing_page": [
            {"name": "Hero Section", "type": "hero", "required": True},
            {"name": "Value Proposition", "type": "benefits", "required": True},
            {"name": "Features", "type": "features", "required": True},
            {"name": "Social Proof", "type": "testimonials", "required": False},
            {"name": "CTA", "type": "cta", "required": True}
        ],
        "faq": [
            {"name": "Introduction", "type": "intro", "required": True},
            {"name": "Common Questions", "type": "faq", "required": True},
            {"name": "Related Topics", "type": "related", "required": False}
        ]
    }
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute brief building task"""
        task_type = task.get("type", "build_brief")
        
        if task_type == "build_brief":
            return await self._build_brief(task)
        elif task_type == "analyze_intent":
            return await self._analyze_intent(task)
        elif task_type == "suggest_structure":
            return await self._suggest_structure(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _build_brief(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a comprehensive content brief
        
        Task params:
            keyword: Target keyword
            opportunity: Opportunity data (from scoring agent)
            topic_cluster: Optional topic cluster info
            existing_content: Optional existing content to improve
        """
        keyword = task.get("keyword", "")
        opportunity = task.get("opportunity", {})
        topic_cluster = task.get("topic_cluster")
        existing_content = task.get("existing_content")
        
        if not keyword:
            return {"status": "error", "error": "Keyword required"}
        
        logger.info(f"Building brief for keyword: {keyword}")
        
        # 1. Analyze search intent
        intent = self._classify_intent(keyword)
        
        # 2. Determine content type
        content_type = self._determine_content_type(keyword, intent, existing_content)
        
        # 3. Generate title suggestions
        titles = await self._generate_titles(keyword, intent)
        
        # 4. Build section structure
        sections = self._build_sections(content_type, keyword)
        
        # 5. Generate meta descriptions
        meta_descriptions = await self._generate_meta_descriptions(keyword, intent)
        
        # 6. Find internal link targets
        internal_links = await self._find_internal_links(keyword, topic_cluster)
        
        # 7. Determine CTAs
        ctas = self._determine_ctas(intent, content_type)
        
        # 8. Calculate word count
        word_count = self._recommend_word_count(content_type, opportunity)
        
        # 9. Determine required elements
        required_elements = self._determine_required_elements(content_type, intent)
        
        import uuid
        brief = ContentBrief(
            brief_id=str(uuid.uuid4())[:8],
            target_keyword=keyword,
            target_page=opportunity.get("target_page"),
            content_type=content_type,
            search_intent=intent,
            suggested_titles=titles,
            recommended_word_count=word_count,
            required_sections=[s for s in sections if s.get("required")],
            optional_sections=[s for s in sections if not s.get("required")],
            meta_description_suggestions=meta_descriptions,
            secondary_keywords=task.get("secondary_keywords", []),
            internal_link_targets=internal_links,
            hub_page=topic_cluster.get("hub_url") if topic_cluster else None,
            primary_cta=ctas.get("primary"),
            secondary_ctas=ctas.get("secondary", []),
            min_seo_score=70,
            required_elements=required_elements
        )
        
        # Publish event
        await self.publish_event("brief_created", {
            "brief_id": brief.brief_id,
            "keyword": keyword,
            "content_type": content_type
        })
        
        return {
            "status": "success",
            "brief": brief.to_dict()
        }
    
    def _classify_intent(self, keyword: str) -> str:
        """Classify search intent based on keyword patterns"""
        keyword_lower = keyword.lower()
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in keyword_lower:
                    return intent
        
        # Default to informational
        return "informational"
    
    def _determine_content_type(
        self,
        keyword: str,
        intent: str,
        existing_content: Optional[Dict] = None
    ) -> str:
        """Determine best content type"""
        # If updating existing content, keep same type
        if existing_content and existing_content.get("type"):
            return existing_content["type"]
        
        # Check for specific patterns
        keyword_lower = keyword.lower()
        
        if "vs" in keyword_lower or "versus" in keyword_lower or "compare" in keyword_lower:
            return "comparison"
        
        if "how to" in keyword_lower or "guide" in keyword_lower:
            return "blog_post"
        
        if any(w in keyword_lower for w in ["faq", "questions", "answers"]):
            return "faq"
        
        # Use intent-based default
        return self.CONTENT_TYPE_MAP.get(intent, "blog_post")
    
    async def _generate_titles(self, keyword: str, intent: str) -> List[str]:
        """Generate title suggestions using AI"""
        # For now, generate template-based titles
        # In production, this would use AI
        
        templates = {
            "informational": [
                f"The Complete Guide to {keyword.title()}",
                f"{keyword.title()}: Everything You Need to Know",
                f"How to {keyword.title()} (Step-by-Step Guide)"
            ],
            "commercial": [
                f"Best {keyword.title()} in 2026: Top Picks Reviewed",
                f"{keyword.title()} Comparison: Which One is Right for You?",
                f"Top 10 {keyword.title()} Options Compared"
            ],
            "transactional": [
                f"{keyword.title()} - Premium Quality at Best Prices",
                f"Shop {keyword.title()} | Free Shipping Available",
                f"Buy {keyword.title()} Online - Trusted Supplier"
            ]
        }
        
        return templates.get(intent, templates["informational"])
    
    def _build_sections(self, content_type: str, keyword: str) -> List[Dict[str, Any]]:
        """Build section structure based on content type"""
        template = self.SECTION_TEMPLATES.get(content_type, self.SECTION_TEMPLATES["blog_post"])
        
        sections = []
        for section in template:
            sections.append({
                "name": section["name"],
                "type": section["type"],
                "required": section["required"],
                "description": self._get_section_description(section["type"], keyword)
            })
        
        return sections
    
    def _get_section_description(self, section_type: str, keyword: str) -> str:
        """Get description for section type"""
        descriptions = {
            "intro": f"Introduce the topic of {keyword} and set reader expectations",
            "body": f"Comprehensive coverage of {keyword} with detailed information",
            "conclusion": "Summarize key points and provide next steps",
            "faq": f"Answer common questions about {keyword}",
            "table": "Comparison table with key features and specifications",
            "pros_cons": "List advantages and disadvantages clearly",
            "hero": "Compelling headline with value proposition",
            "benefits": "Key benefits for the user",
            "features": "Product/service features with descriptions",
            "cta": "Clear call-to-action with conversion focus"
        }
        return descriptions.get(section_type, "")
    
    async def _generate_meta_descriptions(self, keyword: str, intent: str) -> List[str]:
        """Generate meta description suggestions"""
        templates = {
            "informational": [
                f"Learn everything about {keyword} in this comprehensive guide. Discover tips, best practices, and expert insights.",
                f"Complete guide to {keyword}. Step-by-step instructions, examples, and FAQs answered by experts."
            ],
            "commercial": [
                f"Compare the best {keyword} options. Read our in-depth reviews, pros & cons, and find the perfect choice for you.",
                f"Looking for {keyword}? Our comparison guide helps you make the right choice. Expert reviews inside."
            ],
            "transactional": [
                f"Shop premium {keyword} at competitive prices. Fast shipping, quality guaranteed. Order now!",
                f"Buy {keyword} from a trusted supplier. Bulk discounts available. Request a quote today."
            ]
        }
        return templates.get(intent, templates["informational"])
    
    async def _find_internal_links(
        self,
        keyword: str,
        topic_cluster: Optional[Dict] = None
    ) -> List[Dict[str, str]]:
        """Find relevant internal link targets"""
        links = []
        
        # Add hub page if in a topic cluster
        if topic_cluster and topic_cluster.get("hub_url"):
            links.append({
                "url": topic_cluster["hub_url"],
                "anchor_text": topic_cluster.get("hub_keyword", keyword),
                "type": "hub"
            })
        
        # TODO: Query database for related content
        # This would search for pages with related keywords
        
        return links
    
    def _determine_ctas(self, intent: str, content_type: str) -> Dict[str, Any]:
        """Determine appropriate CTAs"""
        cta_map = {
            "transactional": {
                "primary": "Request a Quote",
                "secondary": ["View Products", "Contact Us", "Download Specs"]
            },
            "commercial": {
                "primary": "Compare Options",
                "secondary": ["Read Reviews", "Get Pricing", "Request Demo"]
            },
            "informational": {
                "primary": "Learn More",
                "secondary": ["Subscribe", "Download Guide", "Share Article"]
            }
        }
        return cta_map.get(intent, cta_map["informational"])
    
    def _recommend_word_count(
        self,
        content_type: str,
        opportunity: Dict
    ) -> int:
        """Recommend word count based on content type and competition"""
        base_counts = {
            "blog_post": 1500,
            "comparison": 2000,
            "landing_page": 800,
            "faq": 1200
        }
        
        base = base_counts.get(content_type, 1500)
        
        # Adjust based on position (higher competition = more content needed)
        position = opportunity.get("current_position", 10)
        if position > 10:
            base = int(base * 1.3)  # Need more content to compete
        
        return base
    
    def _determine_required_elements(
        self,
        content_type: str,
        intent: str
    ) -> List[str]:
        """Determine required content elements"""
        elements = ["H2 headings", "Internal links"]
        
        if content_type == "comparison":
            elements.extend(["Comparison table", "Pros/cons lists"])
        
        if content_type == "blog_post":
            elements.extend(["Images", "FAQ section"])
        
        if intent == "informational":
            elements.append("Step-by-step instructions")
        
        return elements
    
    async def _analyze_intent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze search intent for a keyword"""
        keyword = task.get("keyword", "")
        intent = self._classify_intent(keyword)
        
        return {
            "status": "success",
            "keyword": keyword,
            "intent": intent,
            "recommended_content_type": self.CONTENT_TYPE_MAP.get(intent, "blog_post")
        }
    
    async def _suggest_structure(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest content structure"""
        content_type = task.get("content_type", "blog_post")
        keyword = task.get("keyword", "")
        
        sections = self._build_sections(content_type, keyword)
        
        return {
            "status": "success",
            "content_type": content_type,
            "sections": sections
        }
