"""
Content Intelligence API

Admin endpoints for research management and cache monitoring.
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.core.database import get_db
from src.core.auth import get_current_admin
from src.services.content_intelligence import ContentIntelligenceService
from src.services.research.cache import ResearchCache
from src.services.content.outline_generator import OutlineGenerator
from src.services.content.hook_optimizer import HookOptimizer
from src.models.content_intelligence import ContentTopic, ResearchResult, ContentOutline, ResearchContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/content-intelligence", tags=["content-intelligence"])


# Request/Response Models

class ResearchRequest(BaseModel):
    """Request to trigger research"""
    industry: str = Field(..., description="Industry type (e.g., packaging, manufacturing)")
    audience: str = Field(..., description="Target audience")
    pain_points: List[str] = Field(default_factory=list, description="Known customer pain points")
    product_categories: List[str] = Field(default_factory=list, description="Product categories")
    business_type: str = Field(default="b2b", description="Business type: b2b or b2c")
    
    
class TopicResponse(BaseModel):
    """Response with generated topics"""
    title: str
    angle: str
    value_score: float
    business_intent: float
    hook_type: str
    industry: str
    target_audience: str
    
    class Config:
        from_attributes = True


class CacheStatsResponse(BaseModel):
    """Cache statistics response"""
    memory_hit_rate: float
    redis_hit_rate: float
    db_hit_rate: float
    total_requests: int
    api_calls_saved: int
    memory_cache_size: int
    

class TopicQueueResponse(BaseModel):
    """Pending topics in queue"""
    id: int
    title: str
    value_score: float
    business_intent: float
    industry: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class OutlineRequest(BaseModel):
    """Request to generate outline"""
    topic_title: str
    research_result: Optional[dict] = None


class OutlineResponse(BaseModel):
    """Generated outline response"""
    title: str
    hook: str
    hook_type: str
    sections: List[dict]
    target_word_count: int
    estimated_read_time: int
    conclusion_type: str


class TitleOptimizationRequest(BaseModel):
    """Request to optimize titles"""
    topic_title: str
    industry: str
    audience: str
    count: int = Field(default=5, ge=1, le=10)


class TitleOptimizationResponse(BaseModel):
    """Optimized titles response"""
    title: str
    hook_type: str
    expected_ctr: float
    rationale: str
    test_variant: str


# Endpoints

@router.post("/research", response_model=List[TopicResponse])
async def trigger_research(
    request: ResearchRequest,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Manually trigger research for a topic and get high-value content topics.
    
    This endpoint:
    1. Conducts parallel research across multiple sources
    2. Generates research-driven topics
    3. Scores topics by business value
    4. Returns top-scoring topics
    
    Requires admin authentication.
    """
    logger.info(f"Admin {current_admin.get('username')} triggered research for industry: {request.industry}")
    
    try:
        # Initialize services
        cache = ResearchCache(db=db)
        service = ContentIntelligenceService(db, cache)
        
        # Generate topics
        topics = await service.generate_high_value_topics(
            industry=request.industry,
            audience=request.audience,
            pain_points=request.pain_points
        )
        
        # Convert to response format
        response_topics = []
        for topic in topics:
            response_topics.append(TopicResponse(
                title=topic.title,
                angle=topic.angle,
                value_score=topic.value_score,
                business_intent=topic.business_intent,
                hook_type=topic.hook_type.value,
                industry=topic.industry,
                target_audience=topic.target_audience
            ))
        
        logger.info(f"Generated {len(response_topics)} topics for {request.industry}")
        return response_topics
        
    except Exception as e:
        logger.error(f"Research failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research generation failed: {str(e)}"
        )


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get research cache statistics.
    
    Returns hit rates for all three cache tiers (Memory, Redis, Database)
    and API call savings metrics.
    
    Requires admin authentication.
    """
    try:
        cache = ResearchCache(db=db)
        stats = cache.get_stats()
        
        return CacheStatsResponse(
            memory_hit_rate=stats.get('memory_hits', 0) / max(stats.get('total_requests', 1), 1),
            redis_hit_rate=stats.get('redis_hits', 0) / max(stats.get('total_requests', 1), 1),
            db_hit_rate=stats.get('db_hits', 0) / max(stats.get('total_requests', 1), 1),
            total_requests=stats.get('total_requests', 0),
            api_calls_saved=stats.get('api_calls_saved', 0),
            memory_cache_size=stats.get('memory_cache_size', 0)
        )
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cache stats: {str(e)}"
        )


@router.get("/topics/queue", response_model=List[TopicQueueResponse])
async def get_pending_topics(
    min_value_score: float = 0.7,
    industry: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    View high-value topics waiting to be used.
    
    Returns topics that:
    - Have value_score > min_value_score (default 0.7)
    - Have not been used yet
    - Are sorted by value_score (highest first)
    
    Query Parameters:
    - min_value_score: Minimum value score threshold (0.0-1.0)
    - industry: Filter by specific industry (optional)
    
    Requires admin authentication.
    """
    try:
        from src.models.content_intelligence import ContentTopicModel
        
        query = db.query(ContentTopicModel).filter(
            ContentTopicModel.used == False,
            ContentTopicModel.value_score >= min_value_score
        )
        
        if industry:
            query = query.filter(ContentTopicModel.industry == industry)
        
        topics = query.order_by(ContentTopicModel.value_score.desc()).limit(50).all()
        
        return [
            TopicQueueResponse(
                id=t.id,
                title=t.title,
                value_score=t.value_score,
                business_intent=t.business_intent,
                industry=t.industry,
                created_at=t.created_at
            )
            for t in topics
        ]
        
    except Exception as e:
        logger.error(f"Failed to get topic queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve topic queue: {str(e)}"
        )


@router.post("/outline/generate", response_model=OutlineResponse)
async def generate_outline(
    request: OutlineRequest,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Generate a research-supported content outline.
    
    Creates a structured outline with:
    - Engaging hook based on research
    - Logical section flow
    - Research citations
    - Word count estimates
    
    Requires admin authentication.
    """
    try:
        generator = OutlineGenerator()
        
        # Build minimal topic for outline generation
        from src.models.content_intelligence import ContentTopic, HookType
        
        topic = ContentTopic(
            title=request.topic_title,
            angle="Comprehensive guide",
            hook_type=HookType.HOW_TO,
            industry="general",
            target_audience="b2b_buyers",
            business_intent=0.7,
            research_result=ResearchResult(**request.research_result) if request.research_result else None
        )
        
        outline = await generator.generate_outline(topic, topic.research_result)
        
        return OutlineResponse(
            title=outline.title,
            hook=outline.hook,
            hook_type=outline.hook_type.value,
            sections=[s.dict() for s in outline.sections],
            target_word_count=outline.target_word_count,
            estimated_read_time=outline.estimated_read_time,
            conclusion_type=outline.conclusion_type
        )
        
    except Exception as e:
        logger.error(f"Outline generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Outline generation failed: {str(e)}"
        )


@router.post("/titles/optimize", response_model=List[TitleOptimizationResponse])
async def optimize_titles(
    request: TitleOptimizationRequest,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Generate optimized title variants with CTR estimates.
    
    Creates multiple title options with:
    - Different hook types (data, problem, question, how-to, story)
    - Expected CTR based on research
    - A/B test variants
    
    Requires admin authentication.
    """
    try:
        optimizer = HookOptimizer()
        
        # Build minimal topic
        from src.models.content_intelligence import ContentTopic, HookType
        
        topic = ContentTopic(
            title=request.topic_title,
            angle="Optimized approach",
            hook_type=HookType.DATA,
            industry=request.industry,
            target_audience=request.audience,
            business_intent=0.75,
            differentiation_score=0.7
        )
        
        titles = await optimizer.generate_optimized_titles(topic, count=request.count)
        
        return [
            TitleOptimizationResponse(
                title=t.title,
                hook_type=t.hook_type.value,
                expected_ctr=t.expected_ctr,
                rationale=t.rationale,
                test_variant=t.test_variant
            )
            for t in titles
        ]
        
    except Exception as e:
        logger.error(f"Title optimization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Title optimization failed: {str(e)}"
        )


@router.post("/cache/cleanup")
async def cleanup_cache(
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Clean up expired cache entries.
    
    Removes expired entries from all cache tiers.
    
    Requires admin authentication.
    """
    try:
        cache = ResearchCache(db=db)
        cleaned = await cache.cleanup_expired(db=db)
        
        logger.info(f"Admin {current_admin.get('username')} cleaned up {cleaned} expired cache entries")
        
        return {
            "status": "success",
            "cleaned_entries": cleaned,
            "message": f"Cleaned {cleaned} expired cache entries"
        }
        
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache cleanup failed: {str(e)}"
        )
