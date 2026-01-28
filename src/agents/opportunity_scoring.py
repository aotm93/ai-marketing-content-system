"""
Opportunity Scoring Agent
Implements P1-4: OpportunityScoringAgent

Analyzes GSC data to identify and score SEO opportunities:
- Low-hanging fruits (high impressions, position 4-20)
- CTR optimization candidates (low CTR despite good position)
- Content refresh candidates (declining performance)
- Cannibalization detection (multiple pages for same query)
"""

import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
import uuid

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class ScoredOpportunity:
    """Scored SEO opportunity"""
    opportunity_id: str
    opportunity_type: str
    target_query: str
    target_page: str
    score: float  # 0-100
    potential_clicks: int
    confidence: float  # 0-1
    current_metrics: Dict[str, Any]
    recommended_action: str
    action_details: Dict[str, Any]
    priority: str  # low, medium, high, critical
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "type": self.opportunity_type,
            "target_query": self.target_query,
            "target_page": self.target_page,
            "score": round(self.score, 1),
            "potential_clicks": self.potential_clicks,
            "confidence": round(self.confidence, 2),
            "current_metrics": self.current_metrics,
            "recommended_action": self.recommended_action,
            "action_details": self.action_details,
            "priority": self.priority
        }


class OpportunityScoringAgent(BaseAgent):
    """
    Opportunity Scoring Agent
    
    Identifies and prioritizes SEO opportunities based on GSC data analysis.
    Uses a multi-factor scoring system to rank opportunities by potential impact.
    """
    
    # Scoring weights for different factors
    SCORING_WEIGHTS = {
        "impressions": 0.25,      # Higher impressions = more opportunity
        "position_gap": 0.30,     # Room to improve position
        "ctr_potential": 0.20,    # CTR improvement potential
        "trend": 0.15,            # Trending direction
        "competition": 0.10      # Query difficulty estimate
    }
    
    # Position benchmarks for CTR
    EXPECTED_CTR = {
        1: 0.32,   # Position 1: ~32% CTR
        2: 0.17,
        3: 0.11,
        4: 0.08,
        5: 0.07,
        6: 0.05,
        7: 0.04,
        8: 0.03,
        9: 0.025,
        10: 0.02
    }
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute opportunity analysis task"""
        task_type = task.get("type", "analyze_opportunities")
        
        if task_type == "analyze_opportunities":
            return await self._analyze_opportunities(task)
        elif task_type == "score_query":
            return await self._score_single_query(task)
        elif task_type == "detect_cannibalization":
            return await self._detect_cannibalization(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _analyze_opportunities(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze GSC data and identify opportunities
        
        Task params:
            gsc_data: List of GSC query data
            min_impressions: Minimum impressions threshold (default: 100)
            position_range: Tuple of (min, max) position (default: (4, 20))
            limit: Max opportunities to return (default: 50)
        """
        gsc_data = task.get("gsc_data", [])
        min_impressions = task.get("min_impressions", 100)
        position_range = task.get("position_range", (4, 20))
        limit = task.get("limit", 50)
        
        if not gsc_data:
            return {
                "status": "error",
                "error": "No GSC data provided"
            }
        
        logger.info(f"Analyzing {len(gsc_data)} queries for opportunities")
        
        opportunities = []
        
        # 1. Low-hanging fruits
        low_hanging = self._find_low_hanging_fruits(
            gsc_data, min_impressions, position_range
        )
        opportunities.extend(low_hanging)
        
        # 2. CTR optimization candidates
        ctr_candidates = self._find_ctr_optimization_candidates(gsc_data)
        opportunities.extend(ctr_candidates)
        
        # 3. Cannibalization issues
        cannibalization = self._find_cannibalization(gsc_data)
        opportunities.extend(cannibalization)
        
        # Sort by score and limit
        opportunities.sort(key=lambda x: x.score, reverse=True)
        top_opportunities = opportunities[:limit]
        
        # Publish event
        await self.publish_event("opportunities_analyzed", {
            "total_queries": len(gsc_data),
            "opportunities_found": len(opportunities),
            "top_opportunities": len(top_opportunities)
        })
        
        return {
            "status": "success",
            "total_analyzed": len(gsc_data),
            "opportunities_found": len(opportunities),
            "opportunities": [o.to_dict() for o in top_opportunities]
        }
    
    def _find_low_hanging_fruits(
        self,
        gsc_data: List[Dict],
        min_impressions: int,
        position_range: Tuple[float, float]
    ) -> List[ScoredOpportunity]:
        """Find low-hanging fruit opportunities"""
        opportunities = []
        
        for data in gsc_data:
            impressions = data.get("impressions", 0)
            position = data.get("position", 0)
            
            # Filter by criteria
            if impressions < min_impressions:
                continue
            if not (position_range[0] <= position <= position_range[1]):
                continue
            
            # Calculate score
            score, potential_clicks, details = self._calculate_opportunity_score(data)
            
            if score < 30:  # Minimum threshold
                continue
            
            opportunity = ScoredOpportunity(
                opportunity_id=str(uuid.uuid4())[:8],
                opportunity_type="low_hanging_fruit",
                target_query=data.get("query", ""),
                target_page=data.get("page", ""),
                score=score,
                potential_clicks=potential_clicks,
                confidence=0.8,  # High confidence for data-driven opportunities
                current_metrics={
                    "position": position,
                    "impressions": impressions,
                    "clicks": data.get("clicks", 0),
                    "ctr": data.get("ctr", 0)
                },
                recommended_action=details["action"],
                action_details=details,
                priority=self._score_to_priority(score)
            )
            
            opportunities.append(opportunity)
        
        return opportunities
    
    def _find_ctr_optimization_candidates(
        self,
        gsc_data: List[Dict]
    ) -> List[ScoredOpportunity]:
        """Find pages with below-expected CTR"""
        opportunities = []
        
        for data in gsc_data:
            position = data.get("position", 0)
            ctr = data.get("ctr", 0)
            impressions = data.get("impressions", 0)
            
            if impressions < 50 or position > 10:
                continue
            
            # Get expected CTR for this position
            expected_ctr = self.EXPECTED_CTR.get(int(position), 0.02)
            
            # Check if CTR is significantly below expected
            if ctr < expected_ctr * 0.6:  # 40% below expected
                ctr_gap = expected_ctr - ctr
                potential_clicks = int(impressions * ctr_gap)
                
                score = min(100, (ctr_gap / expected_ctr) * 100 + (impressions / 1000) * 10)
                
                opportunity = ScoredOpportunity(
                    opportunity_id=str(uuid.uuid4())[:8],
                    opportunity_type="ctr_optimization",
                    target_query=data.get("query", ""),
                    target_page=data.get("page", ""),
                    score=score,
                    potential_clicks=potential_clicks,
                    confidence=0.7,
                    current_metrics={
                        "position": position,
                        "current_ctr": round(ctr * 100, 2),
                        "expected_ctr": round(expected_ctr * 100, 2),
                        "ctr_gap": round(ctr_gap * 100, 2)
                    },
                    recommended_action="optimize_title_description",
                    action_details={
                        "action": "Improve title and meta description to increase CTR",
                        "focus": ["compelling title", "action words", "include query"],
                        "expected_improvement": f"+{round(ctr_gap * 100, 1)}% CTR"
                    },
                    priority=self._score_to_priority(score)
                )
                
                opportunities.append(opportunity)
        
        return opportunities
    
    def _find_cannibalization(
        self,
        gsc_data: List[Dict]
    ) -> List[ScoredOpportunity]:
        """Detect keyword cannibalization (multiple pages ranking for same query)"""
        opportunities = []
        
        # Group by query
        query_pages: Dict[str, List[Dict]] = {}
        for data in gsc_data:
            query = data.get("query", "")
            if query not in query_pages:
                query_pages[query] = []
            query_pages[query].append(data)
        
        # Find queries with multiple pages
        for query, pages in query_pages.items():
            if len(pages) < 2:
                continue
            
            # Sort by position
            pages.sort(key=lambda x: x.get("position", 100))
            
            # Check if there's significant overlap
            total_impressions = sum(p.get("impressions", 0) for p in pages)
            if total_impressions < 200:
                continue
            
            # Calculate cannibalization score
            position_spread = pages[-1].get("position", 0) - pages[0].get("position", 0)
            
            if position_spread < 10:  # Pages are close in ranking
                score = min(100, 40 + (total_impressions / 500) * 20)
                
                opportunity = ScoredOpportunity(
                    opportunity_id=str(uuid.uuid4())[:8],
                    opportunity_type="cannibalization",
                    target_query=query,
                    target_page=pages[0].get("page", ""),  # Best ranking page
                    score=score,
                    potential_clicks=int(total_impressions * 0.05),  # Conservative estimate
                    confidence=0.6,
                    current_metrics={
                        "pages_count": len(pages),
                        "pages": [p.get("page") for p in pages[:3]],
                        "positions": [p.get("position") for p in pages[:3]],
                        "total_impressions": total_impressions
                    },
                    recommended_action="consolidate_content",
                    action_details={
                        "action": "Consolidate competing pages or add canonical",
                        "primary_page": pages[0].get("page"),
                        "secondary_pages": [p.get("page") for p in pages[1:3]],
                        "recommendation": "Merge content into primary page and redirect others"
                    },
                    priority=self._score_to_priority(score)
                )
                
                opportunities.append(opportunity)
        
        return opportunities
    
    def _calculate_opportunity_score(
        self,
        data: Dict[str, Any]
    ) -> Tuple[float, int, Dict[str, Any]]:
        """
        Calculate opportunity score using multi-factor analysis
        
        Returns: (score, potential_clicks, details)
        """
        position = data.get("position", 0)
        impressions = data.get("impressions", 0)
        clicks = data.get("clicks", 0)
        ctr = data.get("ctr", 0)
        
        # Factor 1: Impressions score (log scale)
        import math
        impressions_score = min(100, math.log10(max(impressions, 1) + 1) * 30)
        
        # Factor 2: Position gap (room to improve)
        if position <= 3:
            position_score = 10  # Already good
        elif position <= 10:
            position_score = 100 - (position - 3) * 8  # Good potential
        else:
            position_score = max(0, 50 - (position - 10) * 2.5)
        
        # Factor 3: CTR potential
        expected_ctr = self.EXPECTED_CTR.get(min(int(position), 10), 0.02)
        if ctr < expected_ctr:
            ctr_score = min(100, (expected_ctr - ctr) / expected_ctr * 100)
        else:
            ctr_score = 20  # Already good
        
        # Calculate weighted score
        score = (
            impressions_score * self.SCORING_WEIGHTS["impressions"] +
            position_score * self.SCORING_WEIGHTS["position_gap"] +
            ctr_score * self.SCORING_WEIGHTS["ctr_potential"]
        ) / (sum(list(self.SCORING_WEIGHTS.values())[:3]))
        
        # Estimate potential clicks
        target_position = max(1, position - 5)  # Aim to improve 5 positions
        target_ctr = self.EXPECTED_CTR.get(int(target_position), ctr * 1.5)
        potential_clicks = int(impressions * target_ctr) - clicks
        potential_clicks = max(0, potential_clicks)
        
        # Determine action
        if position > 10:
            action = "Improve content depth and add more keywords"
        elif ctr < expected_ctr * 0.7:
            action = "Optimize title and meta description"
        else:
            action = "Add more internal links and improve page experience"
        
        details = {
            "action": action,
            "target_position": target_position,
            "factors": {
                "impressions_score": round(impressions_score, 1),
                "position_score": round(position_score, 1),
                "ctr_score": round(ctr_score, 1)
            }
        }
        
        return score * 100 / 100, potential_clicks, details
    
    def _score_to_priority(self, score: float) -> str:
        """Convert score to priority level"""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"
    
    async def _score_single_query(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Score a single query/page combination"""
        data = task.get("data", {})
        score, potential, details = self._calculate_opportunity_score(data)
        
        return {
            "status": "success",
            "score": score,
            "potential_clicks": potential,
            "details": details,
            "priority": self._score_to_priority(score)
        }
    
    async def _detect_cannibalization(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Detect cannibalization for specific queries"""
        gsc_data = task.get("gsc_data", [])
        cannibalization = self._find_cannibalization(gsc_data)
        
        return {
            "status": "success",
            "issues_found": len(cannibalization),
            "issues": [o.to_dict() for o in cannibalization]
        }
