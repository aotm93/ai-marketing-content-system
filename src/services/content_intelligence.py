"""
Content Intelligence Service

Main service for research-driven content generation.
Replaces the fallback layer with high-value, research-based content topics.
"""

import logging
import asyncio
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.models.content_intelligence import (
    ContentTopic, ResearchContext, ResearchResult,
    ContentTopicModel, ResearchCacheEntry, APICallLog,
    HookType, OptimizedTitle
)

logger = logging.getLogger(__name__)


class ValueScorer:
    """
    Scores content topics based on multiple dimensions.
    
    Scoring weights:
    - Business Intent: 30% (most important)
    - Trend Score: 25%
    - Competition Score: 20% (inverse - lower is better)
    - Differentiation: 15%
    - Brand Alignment: 10%
    """
    
    WEIGHTS = {
        'business_intent': 0.30,
        'trend': 0.25,
        'competition': 0.20,
        'differentiation': 0.15,
        'brand_alignment': 0.10
    }
    
    def score(self, topic: ContentTopic) -> float:
        """
        Calculate composite value score (0-1).
        Higher is better.
        """
        # Normalize competition score (lower is better, so invert)
        normalized_competition = 1 - topic.competition_score
        
        # Calculate weighted score
        score = (
            self.WEIGHTS['business_intent'] * topic.business_intent +
            self.WEIGHTS['trend'] * topic.trend_score +
            self.WEIGHTS['competition'] * normalized_competition +
            self.WEIGHTS['differentiation'] * topic.differentiation_score +
            self.WEIGHTS['brand_alignment'] * topic.brand_alignment_score
        )
        
        return round(score, 2)
    
    def score_batch(self, topics: List[ContentTopic]) -> List[tuple[ContentTopic, float]]:
        """Score multiple topics and return sorted by score (descending)"""
        scored = [(topic, self.score(topic)) for topic in topics]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


class TopicGenerator:
    """Generates unique content topics from research"""
    
    def __init__(self):
        self.value_scorer = ValueScorer()
    
    def generate(self, research: ResearchResult, context: ResearchContext) -> List[ContentTopic]:
        """
        Generate content topics from research results.
        Returns multiple unique angles.
        """
        topics = []
        
        # Generate topic from pain points
        if research.pain_points:
            topics.extend(self._generate_from_pain_points(
                research.pain_points, context, research
            ))
        
        # Generate topic from trends
        if research.trend_data:
            topics.extend(self._generate_from_trends(
                research.trend_data, context, research
            ))
        
        # Generate topic from content gaps
        if research.content_gaps:
            topics.extend(self._generate_from_gaps(
                research.content_gaps, context, research
            ))
        
        # Generate topic from competitor insights
        if research.competitor_insights:
            topics.extend(self._generate_from_competitors(
                research.competitor_insights, context, research
            ))
        
        # Score and deduplicate
        unique_topics = self._deduplicate_topics(topics)
        scored_topics = self.value_scorer.score_batch(unique_topics)
        
        # Update topics with scores
        for topic, score in scored_topics:
            topic.value_score = score
        
        return [t for t, s in scored_topics]
    
    def _generate_from_pain_points(
        self, 
        pain_points: List[Any], 
        context: ResearchContext,
        research: ResearchResult
    ) -> List[ContentTopic]:
        """Generate topics addressing pain points"""
        topics = []
        
        for pain in pain_points[:3]:  # Top 3 pain points
            # High-intent solution topic
            topics.append(ContentTopic(
                title=f"Solving {pain.category}: A Complete Guide for {context.audience}",
                angle=f"practical_solution_{pain.category}",
                hook_type=HookType.PROBLEM,
                business_intent=0.85,
                pain_points=[pain.description],
                industry=context.industry,
                target_audience=context.audience,
                research_sources=research.sources,
                research_result=research
            ))
            
            # Cost-focused topic (if pain involves cost)
            if "cost" in pain.description.lower() or "price" in pain.description.lower():
                topics.append(ContentTopic(
                    title=f"The Hidden Costs of {context.industry}: What {context.audience} Need to Know",
                    angle="cost_breakdown_hidden_fees",
                    hook_type=HookType.DATA,
                    business_intent=0.90,
                    pain_points=[pain.description],
                    industry=context.industry,
                    target_audience=context.audience,
                    research_sources=research.sources,
                    research_result=research
                ))
        
        return topics
    
    def _generate_from_trends(
        self, 
        trend_data: Any, 
        context: ResearchContext,
        research: ResearchResult
    ) -> List[ContentTopic]:
        """Generate topics from trend data"""
        topics = []
        
        # Rising trend topic
        if trend_data.trend_direction == "rising":
            growth = trend_data.growth_rate or 15
            topics.append(ContentTopic(
                title=f"Why {trend_data.topic} is Growing {growth}%: Insights for {context.audience}",
                angle="trend_analysis_opportunity",
                hook_type=HookType.DATA,
                trend_score=0.90,
                business_intent=0.75,
                industry=context.industry,
                target_audience=context.audience,
                research_sources=research.sources,
                research_result=research
            ))
        
        # Year-ahead prediction topic
        current_year = datetime.now().year
        topics.append(ContentTopic(
            title=f"{context.industry} Trends {current_year}: What {context.audience} Should Prepare For",
            angle="future_predictions_preparation",
            hook_type=HookType.HOW_TO,
            trend_score=0.85,
            business_intent=0.70,
            industry=context.industry,
            target_audience=context.audience,
            research_sources=research.sources,
            research_result=research
        ))
        
        return topics
    
    def _generate_from_gaps(
        self, 
        gaps: List[Any], 
        context: ResearchContext,
        research: ResearchResult
    ) -> List[ContentTopic]:
        """Generate topics from content gaps"""
        topics = []
        
        for gap in gaps[:2]:  # Top 2 gaps
            topics.append(ContentTopic(
                title=f"{gap.topic}: The Guide {context.audience} Actually Need",
                angle=f"gap_filling_{gap.gap_type}",
                hook_type=HookType.CONTROVERSY if gap.gap_type == "angle" else HookType.HOW_TO,
                differentiation_score=0.90,
                business_intent=0.80,
                industry=context.industry,
                target_audience=context.audience,
                research_sources=research.sources,
                research_result=research
            ))
        
        return topics
    
    def _generate_from_competitors(
        self, 
        insights: List[Any], 
        context: ResearchContext,
        research: ResearchResult
    ) -> List[ContentTopic]:
        """Generate topics from competitor analysis"""
        topics = []
        
        # Comparison topic
        if len(insights) >= 2:
            topics.append(ContentTopic(
                title=f"{context.industry} Comparison: A Data-Driven Analysis for {context.audience}",
                angle="competitive_comparison_data",
                hook_type=HookType.DATA,
                differentiation_score=0.85,
                business_intent=0.75,
                industry=context.industry,
                target_audience=context.audience,
                research_sources=research.sources,
                research_result=research
            ))
        
        return topics
    
    def _deduplicate_topics(self, topics: List[ContentTopic]) -> List[ContentTopic]:
        """Remove duplicate topics based on title similarity"""
        seen = set()
        unique = []
        
        for topic in topics:
            # Simple dedup: normalized title
            normalized = topic.title.lower().replace(" ", "")
            if normalized not in seen:
                seen.add(normalized)
                unique.append(topic)
        
        return unique


class ContentIntelligenceService:
    """
    Main service for content intelligence.
    Replaces the fallback layer with research-driven topic generation.
    """
    
    def __init__(self, db: Session, cache: Optional[Any] = None):
        self.db = db
        self.cache = cache
        self.topic_generator = TopicGenerator()
        self.value_scorer = ValueScorer()
        self.orchestrator = None  # Will be set in Task 2
        logger.info("ContentIntelligenceService initialized")
    
    async def generate_high_value_topics(
        self,
        industry: str,
        audience: str,
        pain_points: Optional[List[str]] = None,
        product_categories: Optional[List[str]] = None,
        force_refresh: bool = False
    ) -> List[ContentTopic]:
        """
        Generate high-value content topics based on research.
        
        This is the main entry point that replaces the fallback layer.
        """
        try:
            # Build research context
            context = ResearchContext(
                industry=industry,
                audience=audience,
                pain_points=pain_points or [],
                product_categories=product_categories or []
            )
            
            # Check cache first (unless force refresh)
            if not force_refresh and self.cache:
                cached = await self.cache.get(context.cache_key)
                if cached:
                    logger.info(f"Cache hit for {industry}/{audience}")
                    return [ContentTopic(**t) for t in cached]
            
            # Conduct research (Task 2 will implement orchestrator)
            logger.info(f"Conducting research for {industry}/{audience}")
            if self.orchestrator:
                research = await self.orchestrator.conduct_research(context)
            else:
                # Fallback to mock research if orchestrator not ready
                research = await self._generate_mock_research(context)
            
            # Generate topics from research
            topics = self.topic_generator.generate(research, context)
            
            if not topics:
                logger.warning("No topics generated from research, using emergency fallback")
                topics = await self._generate_emergency_topics(context)
            
            # Score topics
            scored_topics = self.value_scorer.score_batch(topics)
            for topic, score in scored_topics:
                topic.value_score = score
            
            # Sort by value score (highest first)
            topics = [t for t, s in scored_topics]
            
            # Cache results
            if self.cache and topics:
                await self.cache.set(
                    context.cache_key,
                    [t.model_dump() for t in topics],
                    ttl=86400  # 24 hours
                )
            
            # Persist high-value topics to database
            await self._persist_topics(topics)
            
            logger.info(f"Generated {len(topics)} topics for {industry}/{audience}")
            return topics
            
        except Exception as e:
            logger.error(f"Error generating topics: {e}", exc_info=True)
            # Return emergency fallback topics
            return await self._generate_emergency_topics(
                ResearchContext(industry=industry, audience=audience)
            )
    
    async def get_unused_topics(
        self,
        industry: Optional[str] = None,
        min_value_score: float = 0.6,
        limit: int = 10
    ) -> List[ContentTopic]:
        """
        Get high-value topics that haven't been used yet.
        """
        query = self.db.query(ContentTopicModel).filter(
            ContentTopicModel.used == False,
            ContentTopicModel.value_score >= min_value_score
        )
        
        if industry:
            query = query.filter(ContentTopicModel.industry == industry)
        
        models = query.order_by(ContentTopicModel.value_score.desc()).limit(limit).all()
        return [m.to_pydantic() for m in models]
    
    async def mark_topic_used(self, topic_id: int) -> bool:
        """Mark a topic as used"""
        try:
            model = self.db.query(ContentTopicModel).filter_by(id=topic_id).first()
            if model:
                model.used = True
                model.used_at = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error marking topic as used: {e}")
            self.db.rollback()
            return False
    
    async def _generate_mock_research(self, context: ResearchContext) -> ResearchResult:
        """Generate mock research for testing (before orchestrator is ready)"""
        # This is temporary until Task 2 implements real orchestrator
        return ResearchResult(
            pain_points=[
                PainPoint(
                    description=f"Finding reliable {context.industry} suppliers",
                    category="supplier_selection",
                    severity=0.8,
                    frequency="common"
                ),
                PainPoint(
                    description="Managing costs and quality balance",
                    category="cost_quality",
                    severity=0.75,
                    frequency="common"
                )
            ],
            trend_data=TrendData(
                topic=f"{context.industry} automation",
                trend_direction="rising",
                growth_rate=25.5
            ),
            timestamp=datetime.now()
        )
    
    async def _generate_emergency_topics(self, context: ResearchContext) -> List[ContentTopic]:
        """Emergency fallback when everything else fails - but still research-based angles"""
        emergency_topics = [
            ContentTopic(
                title=f"The Complete {context.industry} Guide for {context.audience} ({datetime.now().year})",
                angle="comprehensive_guide",
                hook_type=HookType.HOW_TO,
                business_intent=0.70,
                trend_score=0.60,
                differentiation_score=0.50,
                industry=context.industry,
                target_audience=context.audience,
                value_score=0.60
            ),
            ContentTopic(
                title=f"5 {context.industry} Mistakes {context.audience} Make (And How to Avoid Them)",
                angle="mistakes_avoidance",
                hook_type=HookType.PROBLEM,
                business_intent=0.75,
                trend_score=0.55,
                differentiation_score=0.65,
                industry=context.industry,
                target_audience=context.audience,
                value_score=0.65
            ),
            ContentTopic(
                title=f"{context.industry} Cost Breakdown: What {context.audience} Actually Pay",
                angle="cost_transparency",
                hook_type=HookType.DATA,
                business_intent=0.85,
                trend_score=0.50,
                differentiation_score=0.70,
                industry=context.industry,
                target_audience=context.audience,
                value_score=0.68
            )
        ]
        
        # Score emergency topics
        scored = self.value_scorer.score_batch(emergency_topics)
        for topic, score in scored:
            topic.value_score = score
        
        return [t for t, s in scored]
    
    async def _persist_topics(self, topics: List[ContentTopic]) -> None:
        """Persist high-value topics to database"""
        try:
            for topic in topics:
                # Check if topic already exists
                existing = self.db.query(ContentTopicModel).filter(
                    ContentTopicModel.title == topic.title,
                    ContentTopicModel.industry == topic.industry
                ).first()
                
                if not existing:
                    model = ContentTopicModel(
                        title=topic.title,
                        slug=topic.slug,
                        angle=topic.angle,
                        hook_type=topic.hook_type,
                        business_intent=topic.business_intent,
                        trend_score=topic.trend_score,
                        competition_score=topic.competition_score,
                        differentiation_score=topic.differentiation_score,
                        brand_alignment_score=topic.brand_alignment_score,
                        value_score=topic.value_score,
                        research_sources=[s.model_dump() for s in topic.research_sources],
                        research_result=topic.research_result.model_dump() if topic.research_result else None,
                        outline=topic.outline.model_dump() if topic.outline else None,
                        optimized_titles=[t.model_dump() for t in topic.optimized_titles],
                        industry=topic.industry,
                        target_audience=topic.target_audience,
                        content_format=topic.content_format,
                        estimated_difficulty=topic.estimated_difficulty,
                        used=False
                    )
                    self.db.add(model)
            
            self.db.commit()
            logger.info(f"Persisted {len(topics)} topics to database")
            
        except Exception as e:
            logger.error(f"Error persisting topics: {e}")
            self.db.rollback()
