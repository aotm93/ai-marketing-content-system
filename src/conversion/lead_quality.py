"""
Lead Quality Feedback Loop
Implements P3-3: Lead quality回写反哺 OpportunityScore

Features:
- Lead quality scoring
- ROI feedback to opportunity scoring
- Quality-based opportunity re-ranking
- Performance learning
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class LeadQualityMetrics:
    """Lead quality metrics"""
    lead_id: str
    lead_score: int  # 0-100
    lead_status: str  # new, qualified, opportunity, won, lost
    conversion_value: Optional[float] = None
    time_to_conversion_days: Optional[int] = None
    touchpoint_count: int = 0
    source_page: Optional[str] = None
    source_topic: Optional[str] = None


class LeadQualityScorer:
    """
    Lead Quality Scoring System
    
    Scores leads based on:
    - Company size/industry
    - Engagement level
    - Speed to conversion
    - Actual conversion value
    """
    
    # Scoring weights
    WEIGHTS = {
        "company_size": 0.2,
        "industry_match": 0.15,
        "engagement_score": 0.25,
        "speed_to_convert": 0.2,
        "conversion_value": 0.2
    }
    
    def score_lead(self, lead_data: Dict[str, Any]) -> int:
        """
        Score a lead (0-100)
        
        Args:
            lead_data: Lead information
                - company_size: small/medium/large
                - industry: Industry/vertical
                - engagement_score: 0-100
                - time_to_conversion_days: Days to convert
                - conversion_value: Revenue generated
        """
        score = 0
        
        # Company size
        company_size = lead_data.get("company_size", "small")
        size_scores = {"small": 50, "medium": 75, "large": 100}
        score += size_scores.get(company_size, 50) * self.WEIGHTS["company_size"]
        
        # Industry match
        industry = lead_data.get("industry")
        target_industries = lead_data.get("target_industries", [])
        if industry in target_industries:
            score += 100 * self.WEIGHTS["industry_match"]
        else:
            score += 50 * self.WEIGHTS["industry_match"]
        
        # Engagement
        engagement = lead_data.get("engagement_score", 50)
        score += engagement * self.WEIGHTS["engagement_score"]
        
        # Speed to convert (faster = better)
        time_to_convert = lead_data.get("time_to_conversion_days", 30)
        if time_to_convert <= 7:
            speed_score = 100
        elif time_to_convert <= 14:
            speed_score = 80
        elif time_to_convert <= 30:
            speed_score = 60
        else:
            speed_score = 40
        score += speed_score * self.WEIGHTS["speed_to_convert"]
        
        # Conversion value
        value = lead_data.get("conversion_value", 0)
        if value >= 10000:
            value_score = 100
        elif value >= 5000:
            value_score = 80
        elif value >= 1000:
            value_score = 60
        else:
            value_score = max(20, value / 50)  # Scale up to product
        score += min(100, value_score) * self.WEIGHTS["conversion_value"]
        
        return int(min(100, score))


class OpportunityFeedbackLoop:
    """
    Feedback Loop: Lead Quality → Opportunity Scoring
    
    Uses actual lead performance to improve future opportunity predictions
    """
    
    def __init__(self):
        self.lead_metrics: List[LeadQualityMetrics] = []
        self.page_performance: Dict[str, Dict[str, Any]] = {}
        self.topic_performance: Dict[str, Dict[str, Any]] = {}
    
    def record_lead_outcome(self, metrics: LeadQualityMetrics):
        """Record lead outcome for learning"""
        self.lead_metrics.append(metrics)
        
        # Update page performance
        if metrics.source_page:
            self._update_page_performance(metrics)
        
        # Update topic performance
        if metrics.source_topic:
            self._update_topic_performance(metrics)
        
        logger.info(f"Recorded lead outcome: {metrics.lead_id} (score: {metrics.lead_score})")
    
    def _update_page_performance(self, metrics: LeadQualityMetrics):
        """Update performance stats for a page"""
        page = metrics.source_page
        
        if page not in self.page_performance:
            self.page_performance[page] = {
                "total_leads": 0,
                "total_revenue": 0.0,
                "avg_lead_score": 0.0,
                "conversion_rate": 0.0,
                "qualified_leads": 0
            }
        
        perf = self.page_performance[page]
        perf["total_leads"] += 1
        
        if metrics.conversion_value:
            perf["total_revenue"] += metrics.conversion_value
        
        if metrics.lead_status in ["qualified", "opportunity", "won"]:
            perf["qualified_leads"] += 1
        
        # Update averages
        all_leads = [m for m in self.lead_metrics if m.source_page == page]
        perf["avg_lead_score"] = sum(m.lead_score for m in all_leads) / len(all_leads)
        perf["conversion_rate"] = perf["qualified_leads"] / perf["total_leads"] * 100
    
    def _update_topic_performance(self, metrics: LeadQualityMetrics):
        """Update performance stats for a topic"""
        topic = metrics.source_topic
        
        if topic not in self.topic_performance:
            self.topic_performance[topic] = {
                "total_leads": 0,
                "total_revenue": 0.0,
                "avg_lead_score": 0.0,
                "conversion_rate": 0.0
            }
        
        perf = self.topic_performance[topic]
        perf["total_leads"] += 1
        
        if metrics.conversion_value:
            perf["total_revenue"] += metrics.conversion_value
        
        # Update averages
        all_leads = [m for m in self.lead_metrics if m.source_topic == topic]
        perf["avg_lead_score"] = sum(m.lead_score for m in all_leads) / len(all_leads)
    
    def get_page_quality_multiplier(self, page_url: str) -> float:
        """
        Get quality multiplier for opportunity scoring
        
        Returns: 0.5-1.5 multiplier based on historical performance
        """
        if page_url not in self.page_performance:
            return 1.0  # Neutral for new pages
        
        perf = self.page_performance[page_url]
        
        # Calculate multiplier based on:
        # - Average lead score
        # - Conversion rate
        # - Total revenue
        
        score_factor = perf["avg_lead_score"] / 100  # 0-1
        conversion_factor = min(perf["conversion_rate"] / 50, 1.0)  # Cap at 50% CR
        
        revenue = perf["total_revenue"]
        revenue_factor = min(revenue / 10000, 1.0) if revenue > 0 else 0.5
        
        # Combine factors
        multiplier = (score_factor * 0.4 + conversion_factor * 0.3 + revenue_factor * 0.3)
        
        # Scale to 0.5-1.5 range
        return 0.5 + multiplier
    
    def enhance_opportunity_score(
        self,
        opportunity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance opportunity score with quality feedback
        
        Args:
            opportunity: Opportunity from OpportunityScoringAgent
        
        Returns: Enhanced opportunity with adjusted score
        """
        base_score = opportunity.get("score", 50)
        page_url = opportunity.get("target_page")
        topic = opportunity.get("topic_cluster")
        
        # Get quality multipliers
        page_multiplier = self.get_page_quality_multiplier(page_url) if page_url else 1.0
        
        # Adjust score
        enhanced_score = base_score * page_multiplier
        
        # Add quality insights
        opportunity["original_score"] = base_score
        opportunity["quality_multiplier"] = round(page_multiplier, 2)
        opportunity["enhanced_score"] = round(enhanced_score, 1)
        
        if page_url and page_url in self.page_performance:
            opportunity["historical_performance"] = self.page_performance[page_url]
        
        return opportunity
    
    def get_top_performing_pages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing pages by revenue"""
        pages = [
            {
                "page": page,
                "revenue": perf["total_revenue"],
                "leads": perf["total_leads"],
                "avg_lead_score": perf["avg_lead_score"],
                "conversion_rate": perf["conversion_rate"]
            }
            for page, perf in self.page_performance.items()
        ]
        
        # Sort by revenue
        pages.sort(key=lambda x: x["revenue"], reverse=True)
        
        return pages[:limit]
    
    def get_performance_report(self, time_period_days: int = 30) -> Dict[str, Any]:
        """Generate performance report"""
        cutoff = datetime.now() - timedelta(days=time_period_days)
        
        # Filter recent leads
        recent_leads = [
            m for m in self.lead_metrics
            # Would filter by timestamp if available
        ]
        
        total_leads = len(recent_leads)
        qualified_leads = sum(
            1 for m in recent_leads
            if m.lead_status in ["qualified", "opportunity", "won"]
        )
        total_revenue = sum(m.conversion_value for m in recent_leads if m.conversion_value)
        
        return {
            "time_period_days": time_period_days,
            "total_leads": total_leads,
            "qualified_leads": qualified_leads,
            "qualification_rate": round(qualified_leads / total_leads * 100, 2) if total_leads > 0 else 0,
            "total_revenue": round(total_revenue, 2),
            "revenue_per_lead": round(total_revenue / total_leads, 2) if total_leads > 0 else 0,
            "top_pages": self.get_top_performing_pages(5),
            "avg_lead_score": round(sum(m.lead_score for m in recent_leads) / total_leads, 1) if total_leads > 0 else 0
        }
