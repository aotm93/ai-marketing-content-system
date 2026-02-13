"""
SEO Context Models

Unified SEO context for synchronizing all SEO elements.
Ensures title, content, meta description, and keywords are aligned.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from src.models.content_intelligence import (
    ContentTopic, ResearchResult, ContentOutline, 
    OptimizedTitle, HookType, ResearchSource
)


class InternalLinkOpportunity(BaseModel):
    """Internal linking opportunity with relevance score"""
    target_url: str
    target_title: str
    anchor_text_suggestions: List[str]
    relevance_score: float = Field(ge=0, le=1)
    context_paragraph: str  # Where to insert the link


class SEOElementStatus(str, Enum):
    """Status of SEO element generation"""
    PENDING = "pending"
    GENERATED = "generated"
    OPTIMIZED = "optimized"
    PUBLISHED = "published"


class SEOContext(BaseModel):
    """
    Unified SEO context object ensuring all elements are synchronized.
    
    This is the central object passed through the entire content generation pipeline,
    ensuring title, content, meta, and keywords are aligned.
    """
    
    # ========== Core Identification ==========
    content_id: Optional[str] = None  # Unique ID for tracking
    created_at: datetime = Field(default_factory=datetime.now)
    
    # ========== Source Information ==========
    source: str = Field(..., description="Source of the topic: GSC, KeywordAPI, ContentIntelligence, Emergency")
    industry: str = Field(default="general")
    target_audience: str = Field(default="b2b")
    
    # ========== Keyword Strategy ==========
    target_keyword: str = Field(..., description="Primary target keyword/focus keyword")
    semantic_keywords: List[str] = Field(default_factory=list, description="LSI keywords for content")
    related_keywords: List[str] = Field(default_factory=list)
    keyword_difficulty: Optional[float] = None
    search_volume: Optional[int] = None
    
    # ========== Title Strategy (SYNCHRONIZED) ==========
    # These fields ensure title consistency across all elements
    topic_title: str = Field(..., description="Original topic title from Content Intelligence")
    optimized_titles: List[OptimizedTitle] = Field(default_factory=list, description="HookOptimizer generated variants")
    selected_title: Optional[str] = Field(None, description="Final selected title - MUST be used for H1")
    selected_title_variant: str = Field("A", description="A/B test variant identifier")
    title_hook_type: Optional[HookType] = None
    title_ctr_estimate: Optional[float] = None
    
    # ========== Research Data ==========
    research_result: Optional[ResearchResult] = None
    outline: Optional[ContentOutline] = None
    value_score: Optional[float] = None
    business_intent: Optional[float] = None
    
    # ========== Content Elements ==========
    content_html: Optional[str] = None
    content_word_count: Optional[int] = None
    content_sections: List[Dict[str, Any]] = Field(default_factory=list)
    
    # ========== Meta Elements (SYNCHRONIZED with Title) ==========
    meta_title: Optional[str] = Field(None, description="SEO Title - usually same as selected_title")
    meta_description: Optional[str] = Field(None, description="Must align with title hook type")
    meta_title_length: Optional[int] = None
    meta_description_length: Optional[int] = None
    
    # ========== URL & Structure ==========
    slug: Optional[str] = None
    categories: List[str] = Field(default_factory=lambda: ["Blog", "Guides"])
    tags: List[str] = Field(default_factory=list)
    
    # ========== Internal Linking (Strategy-based) ==========
    internal_links: List[InternalLinkOpportunity] = Field(default_factory=list)
    existing_posts_context: List[str] = Field(default_factory=list)
    
    # ========== Media ==========
    featured_image_url: Optional[str] = None
    featured_image_alt: Optional[str] = None
    featured_image_bytes: Optional[bytes] = None
    
    # ========== Publishing ==========
    status: SEOElementStatus = Field(default=SEOElementStatus.PENDING)
    auto_publish: bool = Field(default=False)
    wordpress_post_id: Optional[int] = None
    wordpress_url: Optional[str] = None
    
    # ========== Performance Tracking ==========
    generation_metrics: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
    
    def select_best_title(self, strategy: str = "ctr") -> str:
        """
        Select the best title based on strategy.
        
        Args:
            strategy: "ctr" | "balanced" | "experimental"
        
        Returns:
            Selected title string
        """
        if not self.optimized_titles:
            return self.topic_title
        
        if strategy == "ctr":
            # Select highest CTR
            best = max(self.optimized_titles, key=lambda x: x.expected_ctr)
        elif strategy == "balanced":
            # Prefer data/problem hooks if close to max
            max_ctr = max(t.expected_ctr for t in self.optimized_titles)
            candidates = [t for t in self.optimized_titles 
                         if t.expected_ctr >= max_ctr * 0.95]
            # Prefer data/problem hooks
            priority_hooks = [HookType.DATA, HookType.PROBLEM]
            for hook in priority_hooks:
                for c in candidates:
                    if c.hook_type == hook:
                        best = c
                        break
                else:
                    continue
                break
            else:
                best = candidates[0]
        else:  # experimental
            # Try uncommon hooks
            uncommon = [HookType.CONTROVERSY, HookType.STORY]
            for t in self.optimized_titles:
                if t.hook_type in uncommon:
                    best = t
                    break
            else:
                best = max(self.optimized_titles, key=lambda x: x.expected_ctr)
        
        self.selected_title = best.title
        self.title_hook_type = best.hook_type
        self.title_ctr_estimate = best.expected_ctr
        self.selected_title_variant = best.test_variant
        
        return best.title
    
    def validate_synchronization(self) -> Dict[str, Any]:
        """
        Validate that all SEO elements are synchronized.
        
        Returns:
            Validation report with issues and suggestions
        """
        issues = []
        warnings = []
        
        # Check 1: Title consistency
        if self.selected_title and self.topic_title:
            if self.selected_title.lower() != self.topic_title.lower():
                # This is OK if it's an optimized variant
                if not any(t.title == self.selected_title for t in self.optimized_titles):
                    warnings.append({
                        "type": "title_mismatch",
                        "message": f"Selected title '{self.selected_title}' differs from topic title '{self.topic_title}' but is not in optimized variants",
                        "severity": "medium"
                    })
        
        # Check 2: Content must use selected title as H1
        if self.content_html and self.selected_title:
            h1_pattern = f"<h1[^>]*>{self.selected_title}</h1>"
            if h1_pattern.lower() not in self.content_html.lower():
                issues.append({
                    "type": "h1_mismatch",
                    "message": f"Content H1 does not match selected title '{self.selected_title}'",
                    "severity": "high"
                })
        
        # Check 3: Meta description should align with hook type
        if self.meta_description and self.title_hook_type:
            hook_alignment = self._check_meta_hook_alignment()
            if not hook_alignment["aligned"]:
                warnings.append({
                    "type": "meta_hook_misalignment",
                    "message": f"Meta description doesn't align with {self.title_hook_type.value} hook type",
                    "suggestion": hook_alignment["suggestion"],
                    "severity": "medium"
                })
        
        # Check 4: Keyword density in content
        if self.content_html and self.target_keyword:
            word_count = len(self.content_html.split())
            keyword_count = self.content_html.lower().count(self.target_keyword.lower())
            if word_count > 0:
                density = (keyword_count / word_count) * 100
                if density < 0.5:
                    warnings.append({
                        "type": "low_keyword_density",
                        "message": f"Keyword density {density:.2f}% is below 0.5%",
                        "severity": "low"
                    })
                elif density > 3.0:
                    issues.append({
                        "type": "high_keyword_density",
                        "message": f"Keyword density {density:.2f}% exceeds 3% (keyword stuffing)",
                        "severity": "high"
                    })
        
        # Check 5: Meta lengths
        if self.meta_title and len(self.meta_title) > 60:
            warnings.append({
                "type": "long_meta_title",
                "message": f"Meta title {len(self.meta_title)} chars exceeds 60 (will be truncated)",
                "severity": "low"
            })
        
        if self.meta_description and len(self.meta_description) > 160:
            warnings.append({
                "type": "long_meta_description",
                "message": f"Meta description {len(self.meta_description)} chars exceeds 160",
                "severity": "low"
            })
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": max(0, 100 - len(issues) * 20 - len(warnings) * 5)
        }
    
    def _check_meta_hook_alignment(self) -> Dict[str, str]:
        """Check if meta description aligns with title hook type"""
        if not self.meta_description:
            return {"aligned": False, "suggestion": "Generate meta description"}
        
        meta_lower = self.meta_description.lower()
        
        hook_patterns = {
            HookType.DATA: ["%", "statistics", "data", "study", "research", "percent"],
            HookType.PROBLEM: ["problem", "challenge", "issue", "mistake", "avoid"],
            HookType.HOW_TO: ["how to", "guide", "step", "learn", "master"],
            HookType.QUESTION: ["?", "what", "why", "how", "discover"],
            HookType.STORY: ["story", "case study", "example", "learn from"],
            HookType.CONTROVERSY: ["myth", "truth", "fact", "vs", "debate"]
        }
        
        patterns = hook_patterns.get(self.title_hook_type, [])
        matches = sum(1 for p in patterns if p in meta_lower)
        
        if matches >= 1:
            return {"aligned": True, "suggestion": "Good alignment"}
        else:
            suggestion = f"Consider adding {self.title_hook_type.value} elements to meta: {', '.join(patterns[:3])}"
            return {"aligned": False, "suggestion": suggestion}
    
    def to_content_creator_task(self) -> Dict[str, Any]:
        """
        Convert SEOContext to task dict for ContentCreatorAgent.
        Ensures all necessary context is passed.
        """
        return {
            "type": "create_article",
            "keyword": self.target_keyword,
            "seo_context": self.model_dump(exclude={'featured_image_bytes'}),
            "title_must_use": self.selected_title,  # Critical: Force this title
            "outline": self.outline.model_dump() if self.outline else None,
            "research_context": {
                "business_intent": self.business_intent,
                "value_score": self.value_score,
                "research_sources": [s.model_dump() for s in self.research_result.sources] if self.research_result else [],
                "statistics": self.research_result.statistics if self.research_result else [],
                "pain_points": [p.model_dump() for p in self.research_result.pain_points] if self.research_result else [],
            },
            "semantic_keywords": self.semantic_keywords,
            "internal_links": [link.model_dump() for link in self.internal_links],
        }
    
    def to_publishable_content(self) -> Dict[str, Any]:
        """Convert to PublishableContent format"""
        return {
            "title": self.selected_title or self.topic_title,
            "content": self.content_html,
            "excerpt": self.meta_description[:300] if self.meta_description else "",
            "status": "publish" if self.auto_publish else "draft",
            "seo_title": self.meta_title or self.selected_title or self.topic_title,
            "seo_description": self.meta_description,
            "focus_keyword": self.target_keyword,
            "categories": self.categories,
            "tags": self.tags,
            "featured_image_data": self.featured_image_bytes,
            "featured_image_alt": self.featured_image_alt or self.selected_title,
        }


class SEOSynchronizationError(Exception):
    """Raised when SEO elements are not synchronized"""
    pass
