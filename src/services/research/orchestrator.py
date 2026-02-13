"""
Research Orchestrator

Coordinates multiple research services in parallel.
Controls API call limits and caching.
"""

import logging
import asyncio
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass

from src.models.content_intelligence import (
    ResearchContext, ResearchResult, ResearchSource,
    PainPoint, TrendData, CompetitorInsight, ContentGap
)
from src.services.research.trend_research import TrendResearchService
from src.services.research.pain_point_analyzer import PainPointAnalyzer
from src.services.research.competitive_analyzer import CompetitiveAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class ResearchConfig:
    """Configuration for research orchestration"""
    enable_trends: bool = True
    enable_pain_points: bool = True
    enable_competitive: bool = True
    max_concurrent_calls: int = 3
    timeout_seconds: int = 30


class ResearchOrchestrator:
    """
    Orchestrates research across multiple sources.
    
    Features:
    - Parallel research execution
    - API call limiting
    - Intelligent caching
    - Graceful degradation
    """
    
    def __init__(self, config: Optional[ResearchConfig] = None):
        self.config = config or ResearchConfig()
        
        # Daily API call limits
        self.daily_call_limits = {
            'dataforseo': 100,
            'trends': 50,
            'competitive': 30,
            'pain_points': 40
        }
        
        # Track API calls
        self.call_counts = {k: 0 for k in self.daily_call_limits.keys()}
        self.call_reset_time = datetime.now().replace(hour=0, minute=0, second=0)
        
        # Initialize research services
        self.trend_service = TrendResearchService()
        self.pain_point_analyzer = PainPointAnalyzer()
        self.competitive_analyzer = CompetitiveAnalyzer()
        
        logger.info("ResearchOrchestrator initialized")
    
    async def conduct_research(self, context: ResearchContext) -> ResearchResult:
        """
        Conduct comprehensive research for given context.
        
        Parallel execution with API limit enforcement.
        """
        # Reset call count if it's a new day
        now = datetime.now()
        if now.date() != self.call_reset_time.date():
            self._reset_call_counts()
            self.call_reset_time = now
        
        logger.info(f"Starting research for {context.industry}/{context.audience}")
        logger.info(f"API call budget: {self._get_remaining_calls()}")
        
        # Build research tasks based on config
        tasks = []
        task_names = []
        
        # Task 1: Trend Research
        if self.config.enable_trends and self._check_call_limit('trends'):
            tasks.append(self._research_trends_safe(context))
            task_names.append('trends')
        else:
            logger.debug("Skipping trend research (disabled or limit reached)")
            tasks.append(self._empty_trend_result())
            task_names.append('trends_empty')
        
        # Task 2: Pain Point Analysis
        if self.config.enable_pain_points and self._check_call_limit('pain_points'):
            tasks.append(self._analyze_pain_points_safe(context))
            task_names.append('pain_points')
        else:
            logger.debug("Skipping pain point analysis (disabled or limit reached)")
            tasks.append(self._empty_pain_points_result())
            task_names.append('pain_points_empty')
        
        # Task 3: Competitive Analysis
        if self.config.enable_competitive and self._check_call_limit('competitive'):
            tasks.append(self._analyze_competitive_safe(context))
            task_names.append('competitive')
        else:
            logger.debug("Skipping competitive analysis (disabled or limit reached)")
            tasks.append(self._empty_competitive_result())
            task_names.append('competitive_empty')
        
        # Execute all tasks in parallel with timeout
        try:
            logger.info(f"Executing {len([t for t in tasks if not asyncio.iscoroutine(t)])} research tasks in parallel")
            
            # Run with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.timeout_seconds
            )
            
            # Process results
            trend_data = results[0] if not isinstance(results[0], Exception) else None
            pain_points = results[1] if not isinstance(results[1], Exception) else []
            competitive_result = results[2] if not isinstance(results[2], Exception) else ([], [])
            
            # Handle exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Research task '{task_names[i]}' failed: {result}")
            
            # Unpack competitive result
            if competitive_result and not isinstance(competitive_result, Exception):
                competitor_insights, content_gaps = competitive_result
            else:
                competitor_insights, content_gaps = [], []
            
            # Compile final result
            research_result = ResearchResult(
                trend_data=trend_data,
                pain_points=pain_points if pain_points else [],
                content_gaps=content_gaps if content_gaps else [],
                competitor_insights=competitor_insights if competitor_insights else [],
                timestamp=datetime.now(),
                sources=self._compile_sources(trend_data, pain_points, competitor_insights)
            )
            
            logger.info(f"Research completed: {len(pain_points or [])} pain points, "
                       f"{len(content_gaps or [])} gaps, "
                       f"trend_data={'yes' if trend_data else 'no'}")
            
            return research_result
            
        except asyncio.TimeoutError:
            logger.error("Research timeout - returning partial results")
            return self._create_partial_result()
        except Exception as e:
            logger.error(f"Research orchestration failed: {e}", exc_info=True)
            return self._create_fallback_result(context)
    
    async def _research_trends_safe(self, context: ResearchContext) -> Optional[TrendData]:
        """Safely research trends with error handling"""
        try:
            if self._check_call_limit('trends'):
                self._increment_call_count('trends')
                result = await self.trend_service.research_trends(context)
                return result
            return None
        except Exception as e:
            logger.warning(f"Trend research failed: {e}")
            return None
    
    async def _analyze_pain_points_safe(self, context: ResearchContext) -> List[PainPoint]:
        """Safely analyze pain points with error handling"""
        try:
            if self._check_call_limit('pain_points'):
                self._increment_call_count('pain_points')
                result = await self.pain_point_analyzer.analyze_pain_points(context)
                return result
            return []
        except Exception as e:
            logger.warning(f"Pain point analysis failed: {e}")
            return []
    
    async def _analyze_competitive_safe(self, context: ResearchContext) -> tuple[List[CompetitorInsight], List[ContentGap]]:
        """Safely analyze competition with error handling"""
        try:
            if self._check_call_limit('competitive'):
                self._increment_call_count('competitive')
                insights = await self.competitive_analyzer.analyze_competitors(context)
                gaps = await self.competitive_analyzer.identify_content_gaps(context)
                return insights, gaps
            return [], []
        except Exception as e:
            logger.warning(f"Competitive analysis failed: {e}")
            return [], []
    
    def _check_call_limit(self, api_name: str) -> bool:
        """Check if we're within API call limits for specific API"""
        limit = self.daily_call_limits.get(api_name, 100)
        count = self.call_counts.get(api_name, 0)
        return count < limit
    
    def _increment_call_count(self, api_name: str):
        """Increment API call counter"""
        if api_name in self.call_counts:
            self.call_counts[api_name] += 1
            logger.debug(f"API call: {api_name} ({self.call_counts[api_name]}/{self.daily_call_limits[api_name]})")
    
    def _reset_call_counts(self):
        """Reset all call counters (new day)"""
        for key in self.call_counts:
            self.call_counts[key] = 0
        logger.info("API call counts reset for new day")
    
    def _get_remaining_calls(self) -> dict:
        """Get remaining API call budget"""
        return {
            api: limit - self.call_counts.get(api, 0)
            for api, limit in self.daily_call_limits.items()
        }
    
    def _compile_sources(self, trend_data, pain_points, competitor_insights) -> List[ResearchSource]:
        """Compile research sources from all results"""
        sources = []
        
        if trend_data and hasattr(trend_data, 'sources'):
            sources.extend(trend_data.sources or [])
        
        # Add generic sources based on research type
        if pain_points:
            sources.append(ResearchSource(
                name="Customer Pain Point Analysis",
                type="synthesis",
                credibility_score=0.8
            ))
        
        if competitor_insights:
            sources.append(ResearchSource(
                name="Competitive Content Analysis",
                type="competitive_research",
                credibility_score=0.75
            ))
        
        return sources
    
    async def _empty_trend_result(self) -> None:
        return None
    
    async def _empty_pain_points_result(self) -> List[PainPoint]:
        return []
    
    async def _empty_competitive_result(self) -> tuple[List[CompetitorInsight], List[ContentGap]]:
        return [], []
    
    def _create_partial_result(self) -> ResearchResult:
        """Create partial result when timeout occurs"""
        return ResearchResult(
            timestamp=datetime.now(),
            sources=[ResearchSource(name="Partial Research (Timeout)", type="system", credibility_score=0.5)]
        )
    
    def _create_fallback_result(self, context: ResearchContext) -> ResearchResult:
        """Create fallback result when research fails completely"""
        return ResearchResult(
            pain_points=[
                PainPoint(
                    description=f"Managing {context.industry} costs effectively",
                    category="cost_management",
                    severity=0.75,
                    frequency="common"
                ),
                PainPoint(
                    description=f"Finding reliable {context.industry} partners",
                    category="supplier_selection",
                    severity=0.80,
                    frequency="common"
                )
            ],
            timestamp=datetime.now(),
            sources=[ResearchSource(name="Fallback Analysis", type="system", credibility_score=0.6)]
        )
