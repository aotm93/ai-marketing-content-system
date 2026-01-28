"""
Dynamic CTA Component System
Implements P3-1: Intent-based dynamic CTA

Features:
- Intent detection (inquiry, sample, download, quote)
- Dynamic CTA switching
- Conversion tracking
- A/B testing support
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class UserIntent(str, Enum):
    """User search intent categories"""
    INFORMATIONAL = "informational"  # Learning/research
    COMMERCIAL = "commercial"        # Comparing options
    TRANSACTIONAL = "transactional"  # Ready to buy
    NAVIGATIONAL = "navigational"    # Looking for specific brand/page


class CTAType(str, Enum):
    """CTA action types"""
    REQUEST_QUOTE = "request_quote"
    REQUEST_SAMPLE = "request_sample"
    DOWNLOAD_SPECS = "download_specs"
    CONTACT_SALES = "contact_sales"
    VIEW_PRODUCTS = "view_products"
    START_TRIAL = "start_trial"
    SUBSCRIBE = "subscribe"
    LEARN_MORE = "learn_more"


@dataclass
class CTAVariant:
    """Single CTA variant for A/B testing"""
    variant_id: str
    cta_type: CTAType
    button_text: str
    button_url: str
    description: Optional[str] = None
    button_color: str = "primary"
    icon: Optional[str] = None
    
    # A/B testing metrics
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    
    @property
    def ctr(self) -> float:
        """Click-through rate"""
        return self.clicks / self.impressions if self.impressions > 0 else 0.0
    
    @property
    def conversion_rate(self) -> float:
        """Conversion rate"""
        return self.conversions / self.clicks if self.clicks > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "cta_type": self.cta_type.value,
            "button_text": self.button_text,
            "button_url": self.button_url,
            "description": self.description,
            "button_color": self.button_color,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "ctr": round(self.ctr * 100, 2),
            "conversion_rate": round(self.conversion_rate * 100, 2)
        }


@dataclass
class DynamicCTAConfig:
    """Configuration for dynamic CTA selection"""
    intent: UserIntent
    page_type: str  # blog_post, product_page, landing_page, comparison
    variants: List[CTAVariant] = field(default_factory=list)
    ab_test_enabled: bool = True
    traffic_split: Optional[Dict[str, float]] = None  # {variant_id: percentage}
    
    def get_primary_cta(self) -> Optional[CTAVariant]:
        """Get the best performing CTA variant"""
        if not self.variants:
            return None
        
        # Sort by conversion rate, then CTR
        sorted_variants = sorted(
            self.variants,
            key=lambda v: (v.conversion_rate, v.ctr),
            reverse=True
        )
        
        return sorted_variants[0]
    
    def select_variant_for_user(self, user_id: Optional[str] = None) -> Optional[CTAVariant]:
        """Select CTA variant for a user (A/B testing)"""
        if not self.variants:
            return None
        
        if not self.ab_test_enabled:
            return self.get_primary_cta()
        
        # Simple round-robin for demo
        # In production, would use consistent hashing based on user_id
        if self.traffic_split:
            # Use traffic split percentages
            import random
            rand = random.random()
            cumulative = 0.0
            
            for variant in self.variants:
                split = self.traffic_split.get(variant.variant_id, 0)
                cumulative += split
                if rand <= cumulative:
                    return variant
        
        # Default: equal split
        import random
        return random.choice(self.variants)


class CTARecommendationEngine:
    """
    CTA Recommendation Engine
    
    Recommends optimal CTA based on:
    - User intent
    - Page type
    - Industry
    - Historical performance
    """
    
    # Intent-based CTA mapping
    INTENT_CTA_MAP = {
        UserIntent.INFORMATIONAL: [
            CTAType.LEARN_MORE,
            CTAType.DOWNLOAD_SPECS,
            CTAType.SUBSCRIBE
        ],
        UserIntent.COMMERCIAL: [
            CTAType.REQUEST_SAMPLE,
            CTAType.CONTACT_SALES,
            CTAType.VIEW_PRODUCTS
        ],
        UserIntent.TRANSACTIONAL: [
            CTAType.REQUEST_QUOTE,
            CTAType.CONTACT_SALES,
            CTAType.START_TRIAL
        ],
        UserIntent.NAVIGATIONAL: [
            CTAType.VIEW_PRODUCTS,
            CTAType.CONTACT_SALES,
            CTAType.LEARN_MORE
        ]
    }
    
    # Default button texts
    DEFAULT_BUTTON_TEXT = {
        CTAType.REQUEST_QUOTE: "Request a Quote",
        CTAType.REQUEST_SAMPLE: "Request Free Sample",
        CTAType.DOWNLOAD_SPECS: "Download Specifications",
        CTAType.CONTACT_SALES: "Contact Sales Team",
        CTAType.VIEW_PRODUCTS: "View All Products",
        CTAType.START_TRIAL: "Start Free Trial",
        CTAType.SUBSCRIBE: "Subscribe to Newsletter",
        CTAType.LEARN_MORE: "Learn More"
    }
    
    def recommend_ctas(
        self,
        intent: UserIntent,
        page_type: str,
        industry: Optional[str] = None,
        count: int = 3
    ) -> List[CTAVariant]:
        """
        Recommend CTA variants for given context
        
        Args:
            intent: User search intent
            page_type: Type of page
            industry: Industry/vertical
            count: Number of variants to return
        """
        recommended_types = self.INTENT_CTA_MAP.get(intent, [CTAType.LEARN_MORE])
        
        variants = []
        for i, cta_type in enumerate(recommended_types[:count]):
            variant = self._create_variant(cta_type, i, industry)
            variants.append(variant)
        
        return variants
    
    def _create_variant(
        self,
        cta_type: CTAType,
        index: int,
        industry: Optional[str] = None
    ) -> CTAVariant:
        """Create a CTA variant"""
        button_text = self.DEFAULT_BUTTON_TEXT.get(cta_type, "Learn More")
        
        # Customize for industry
        if industry == "manufacturing":
            if cta_type == CTAType.REQUEST_QUOTE:
                button_text = "Get Custom Quote"
            elif cta_type == CTAType.REQUEST_SAMPLE:
                button_text = "Request Free Sample + Specs"
        
        return CTAVariant(
            variant_id=f"cta_{cta_type.value}_{index}",
            cta_type=cta_type,
            button_text=button_text,
            button_url=f"/{cta_type.value.replace('_', '-')}",
            button_color="primary" if index == 0 else "secondary"
        )
    
    def analyze_performance(
        self,
        variants: List[CTAVariant]
    ) -> Dict[str, Any]:
        """Analyze CTA performance and recommend winner"""
        if not variants:
            return {"status": "no_variants"}
        
        # Calculate overall metrics
        total_impressions = sum(v.impressions for v in variants)
        total_clicks = sum(v.clicks for v in variants)
        total_conversions = sum(v.conversions for v in variants)
        
        # Find best performer
        best_variant = max(variants, key=lambda v: (v.conversion_rate, v.ctr))
        
        # Statistical significance (simplified)
        # In production, would use proper A/B test significance calculation
        is_significant = total_impressions >= 1000 and best_variant.conversions >= 10
        
        return {
            "status": "success",
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "overall_ctr": round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0,
            "overall_conversion_rate": round(total_conversions / total_clicks * 100, 2) if total_clicks > 0 else 0,
            "best_variant": best_variant.to_dict(),
            "is_significant": is_significant,
            "recommendation": "Use variant as winner" if is_significant else "Continue testing"
        }



from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models.conversion import ConversionEventModel
import uuid
from datetime import datetime

class CTATracker:
    """
    CTA Conversion Tracker (DB Backed)
    """
    
    def __init__(self, db: Session = None):
        pass
    
    def track_impression(
        self,
        variant_id: str,
        page_url: str,
        db: Session,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Track CTA impression"""
        event = ConversionEventModel(
            event_id=str(uuid.uuid4()),
            event_type="impression", # DB enum or string
            variant_id=variant_id,
            page_url=page_url,
            user_id=user_id,
            timestamp=datetime.now(),
            metadata_json=metadata
        )
        db.add(event)
        db.commit()
        logger.info(f"CTA impression tracked (DB): {variant_id}")
    
    def track_click(
        self,
        variant_id: str,
        page_url: str,
        db: Session,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Track CTA click"""
        event = ConversionEventModel(
            event_id=str(uuid.uuid4()),
            event_type="click", 
            variant_id=variant_id,
            page_url=page_url,
            user_id=user_id,
            timestamp=datetime.now(),
            metadata_json=metadata
        )
        db.add(event)
        db.commit()
        logger.info(f"CTA click tracked (DB): {variant_id}")
    
    def track_conversion(
        self,
        variant_id: str,
        page_url: str,
        db: Session,
        user_id: Optional[str] = None,
        conversion_value: Optional[float] = None,
        metadata: Optional[Dict] = None
    ):
        """Track conversion from CTA"""
        event = ConversionEventModel(
            event_id=str(uuid.uuid4()),
            event_type="conversion", 
            variant_id=variant_id,
            page_url=page_url,
            user_id=user_id,
            conversion_value=conversion_value,
            timestamp=datetime.now(),
            metadata_json=metadata
        )
        db.add(event)
        db.commit()
        logger.info(f"CTA conversion tracked (DB): {variant_id}")
    
    def get_stats_by_variant(self, variant_id: str, db: Session) -> Dict[str, int]:
        """Get event stats for a variant from DB"""
        
        # Aggregate query
        stats = db.query(
            ConversionEventModel.event_type,
            func.count(ConversionEventModel.event_id)
        ).filter(
            ConversionEventModel.variant_id == variant_id
        ).group_by(ConversionEventModel.event_type).all()
        
        counts = {bt: count for bt, count in stats}
        
        impressions = counts.get("impression", 0)
        clicks = counts.get("click", 0)
        conversions = counts.get("conversion", 0)
        
        return {
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "ctr": round(clicks / impressions * 100, 2) if impressions > 0 else 0,
            "conversion_rate": round(conversions / clicks * 100, 2) if clicks > 0 else 0
        }
    
    def get_revenue_by_page(self, page_url: str, db: Session) -> float:
        """Get total revenue from a page"""
        result = db.query(
            func.sum(ConversionEventModel.conversion_value)
        ).filter(
            ConversionEventModel.event_type == "conversion",
            ConversionEventModel.page_url == page_url
        ).scalar()
        
        return result or 0.0
    
    def _get_timestamp(self) -> str:
        return datetime.now().isoformat()



class CTAOptimizer:
    """
    CTA Optimizer using Multi-Armed Bandit
    
    Automatically adjusts traffic split to maximize conversions
    """
    
    def __init__(self, epsilon: float = 0.1):
        """
        Args:
            epsilon: Exploration rate (0.1 = 10% exploration, 90% exploitation)
        """
        self.epsilon = epsilon
    
    def select_variant(
        self,
        variants: List[CTAVariant]
    ) -> CTAVariant:
        """
        Select variant using epsilon-greedy strategy
        
        90% of the time: show best performing variant
        10% of the time: randomly explore other variants
        """
        import random
        
        if random.random() < self.epsilon:
            # Explore: random variant
            return random.choice(variants)
        else:
            # Exploit: best variant
            return max(variants, key=lambda v: v.conversion_rate)
    
    def update_traffic_split(
        self,
        variants: List[CTAVariant],
        min_impressions: int = 100
    ) -> Dict[str, float]:
        """
        Calculate optimal traffic split based on performance
        
        Uses Thompson Sampling for traffic allocation
        """
        # Filter variants with sufficient data
        tested_variants = [v for v in variants if v.impressions >= min_impressions]
        
        if not tested_variants:
            # Equal split for cold start
            return {v.variant_id: 1.0 / len(variants) for v in variants}
        
        # Calculate scores (simplified Thompson Sampling)
        import random
        scores = {}
        
        for variant in tested_variants:
            # Beta distribution sample
            alpha = variant.conversions + 1
            beta = variant.clicks - variant.conversions + 1
            
            # Sample from Beta(alpha, beta)
            score = random.betavariate(alpha, beta)
            scores[variant.variant_id] = score
        
        # Normalize to percentages
        total_score = sum(scores.values())
        traffic_split = {
            variant_id: score / total_score
            for variant_id, score in scores.items()
        }
        
        return traffic_split
