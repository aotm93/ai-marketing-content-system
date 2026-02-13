"""
Content Intelligence Models

Data models for research-driven content generation.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Enum as SQLEnum, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from src.models.base import Base, TimestampMixin


class HookType(str, Enum):
    """Types of content hooks"""
    DATA = "data"  # Statistics, percentages
    STORY = "story"  # Personal/company narrative
    PROBLEM = "problem"  # Pain point focus
    QUESTION = "question"  # Provocative question
    HOW_TO = "how_to"  # Practical guide
    CONTROVERSY = "controversy"  # Debate/challenge


class ContentType(str, Enum):
    """Types of content sections"""
    PROBLEM_STATEMENT = "problem_statement"
    SOLUTION = "solution"
    COMPARISON = "comparison"
    BEST_PRACTICES = "best_practices"
    CASE_STUDY = "case_study"
    DATA_ANALYSIS = "data_analysis"
    FAQ = "faq"
    CTA = "call_to_action"


class ResearchSource(BaseModel):
    """Source of research data"""
    name: str
    url: Optional[str] = None
    type: str  # "industry_report", "survey", "expert_interview", "case_study"
    credibility_score: float = Field(ge=0, le=1)
    publish_date: Optional[datetime] = None


class PainPoint(BaseModel):
    """Customer pain point identified from research"""
    description: str
    category: str
    severity: float = Field(ge=0, le=1)  # 0-1 scale
    frequency: str  # "common", "occasional", "rare"
    evidence: Optional[str] = None  # Supporting data
    quotes: List[str] = Field(default_factory=list)


class ContentGap(BaseModel):
    """Identified content gap in competitor landscape"""
    topic: str
    current_coverage: str  # How competitors cover it
    gap_type: str  # "depth", "angle", "format", "data"
    opportunity_score: float = Field(ge=0, le=1)
    suggested_approach: str


class CompetitorInsight(BaseModel):
    """Insight from competitor content analysis"""
    competitor: str
    content_url: Optional[str] = None
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    missing_elements: List[str] = Field(default_factory=list)


class TrendData(BaseModel):
    """Trend information from research"""
    topic: str
    trend_direction: str  # "rising", "stable", "declining"
    growth_rate: Optional[float] = None  # Percentage
    related_topics: List[str] = Field(default_factory=list)
    seasonality: Optional[str] = None
    data_points: List[Dict[str, Any]] = Field(default_factory=list)


class ResearchResult(BaseModel):
    """Complete research result"""
    trend_data: Optional[TrendData] = None
    pain_points: List[PainPoint] = Field(default_factory=list)
    content_gaps: List[ContentGap] = Field(default_factory=list)
    competitor_insights: List[CompetitorInsight] = Field(default_factory=list)
    statistics: List[Dict[str, Any]] = Field(default_factory=list)
    expert_quotes: List[Dict[str, str]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    sources: List[ResearchSource] = Field(default_factory=list)


class OutlineSection(BaseModel):
    """Section in content outline"""
    title: str
    content_type: ContentType
    key_points: List[str] = Field(default_factory=list)
    research_support: Optional[List[Dict[str, Any]]] = None
    estimated_word_count: int = 300
    order: int = 0


class ContentOutline(BaseModel):
    """Complete content outline"""
    title: str
    hook: str
    hook_type: HookType
    sections: List[OutlineSection] = Field(default_factory=list)
    conclusion_type: str = "summary"  # "summary", "cta", "question"
    target_word_count: int = 2000
    estimated_read_time: int = 8  # minutes


class OptimizedTitle(BaseModel):
    """Generated title with metadata"""
    title: str
    hook_type: HookType
    expected_ctr: float = Field(ge=0, le=1)
    rationale: str
    test_variant: str = "A"  # For A/B testing


class ContentTopic(BaseModel):
    """Research-driven content topic"""
    # Core identification
    title: str
    slug: Optional[str] = None
    
    # Research data
    angle: str  # Unique angle/approach
    hook_type: HookType
    
    # Scoring
    business_intent: float = Field(ge=0, le=1)
    trend_score: float = Field(ge=0, le=1)
    competition_score: float = Field(ge=0, le=1)  # Lower is better
    differentiation_score: float = Field(ge=0, le=1)
    brand_alignment_score: float = Field(ge=0, le=1)
    value_score: float = Field(ge=0, le=1)  # Composite score
    
    # Research sources
    research_sources: List[ResearchSource] = Field(default_factory=list)
    research_result: Optional[ResearchResult] = None
    
    # Content structure
    outline: Optional[ContentOutline] = None
    optimized_titles: List[OptimizedTitle] = Field(default_factory=list)
    
    # Metadata
    industry: str
    target_audience: str
    content_format: str = "blog_post"  # "blog_post", "guide", "comparison", etc.
    estimated_difficulty: str = "medium"  # "easy", "medium", "hard"
    
    # Usage tracking
    used: bool = False
    used_at: Optional[datetime] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class ResearchContext(BaseModel):
    """Context for research"""
    industry: str
    audience: str
    pain_points: List[str] = Field(default_factory=list)
    product_categories: List[str] = Field(default_factory=list)
    business_type: str = "b2b"
    geographic_focus: Optional[str] = None
    
    @property
    def cache_key(self) -> str:
        """Generate cache key for this context"""
        import hashlib
        key_data = f"{self.industry}:{self.audience}:{','.join(sorted(self.pain_points))}"
        return hashlib.md5(key_data.encode()).hexdigest()


# Database Models

class ContentTopicModel(Base, TimestampMixin):
    """Database model for content topics"""
    __tablename__ = "content_topics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core fields
    title = Column(String(500), nullable=False)
    slug = Column(String(500), nullable=True)
    angle = Column(String(500), nullable=False)
    hook_type = Column(SQLEnum(HookType), nullable=False)
    
    # Scoring
    business_intent = Column(Float, default=0.5)
    trend_score = Column(Float, default=0.5)
    competition_score = Column(Float, default=0.5)
    differentiation_score = Column(Float, default=0.5)
    brand_alignment_score = Column(Float, default=0.5)
    value_score = Column(Float, default=0.5)
    
    # Research data (JSON for flexibility)
    research_sources = Column(JSON, default=list)
    research_result = Column(JSON, nullable=True)
    outline = Column(JSON, nullable=True)
    optimized_titles = Column(JSON, default=list)
    
    # Metadata
    industry = Column(String(100), nullable=False, index=True)
    target_audience = Column(String(100), nullable=False)
    content_format = Column(String(50), default="blog_post")
    estimated_difficulty = Column(String(20), default="medium")
    
    # Usage tracking
    used = Column(Boolean, default=False, index=True)
    used_at = Column(DateTime, nullable=True)
    performance_metrics = Column(JSON, nullable=True)
    
    def to_pydantic(self) -> ContentTopic:
        """Convert to Pydantic model"""
        return ContentTopic(
            id=self.id,
            title=self.title,
            slug=self.slug,
            angle=self.angle,
            hook_type=self.hook_type,
            business_intent=self.business_intent,
            trend_score=self.trend_score,
            competition_score=self.competition_score,
            differentiation_score=self.differentiation_score,
            brand_alignment_score=self.brand_alignment_score,
            value_score=self.value_score,
            research_sources=[ResearchSource(**s) for s in self.research_sources],
            research_result=ResearchResult(**self.research_result) if self.research_result else None,
            outline=ContentOutline(**self.outline) if self.outline else None,
            optimized_titles=[OptimizedTitle(**t) for t in self.optimized_titles],
            industry=self.industry,
            target_audience=self.target_audience,
            content_format=self.content_format,
            estimated_difficulty=self.estimated_difficulty,
            used=self.used,
            used_at=self.used_at,
            performance_metrics=self.performance_metrics
        )


class ResearchCacheEntry(Base, TimestampMixin):
    """Cache for research results"""
    __tablename__ = "research_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(255), nullable=False, unique=True, index=True)
    data = Column(Text, nullable=False)  # JSON string
    context_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)


class APICallLog(Base, TimestampMixin):
    """Log of API calls for monitoring and cost control"""
    __tablename__ = "api_call_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    api_name = Column(String(50), nullable=False, index=True)  # "dataforseo", "trends", etc.
    endpoint = Column(String(255), nullable=False)
    call_date = Column(DateTime, default=datetime.now, index=True)
    success = Column(Boolean, default=True)
    response_time_ms = Column(Integer, nullable=True)
    cost_estimate = Column(Float, default=0.0)
    cache_hit = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
