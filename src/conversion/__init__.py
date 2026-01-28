"""
Conversion Module
P3: Conversion tracking, attribution, and optimization
"""

from .dynamic_cta import (
    UserIntent,
    CTAType,
    CTAVariant,
    DynamicCTAConfig,
    CTARecommendationEngine,
    CTATracker,
    CTAOptimizer
)

from .attribution import (
    ConversionEventType,
    AttributionModel,
    ConversionEvent,
    Lead,
    ConversionTracker,
    AttributionEngine,
    ROIAnalyzer
)

from .lead_quality import (
    LeadQualityMetrics,
    LeadQualityScorer,
    OpportunityFeedbackLoop
)

__all__ = [
    # Dynamic CTA
    "UserIntent",
    "CTAType",
    "CTAVariant",
    "DynamicCTAConfig",
    "CTARecommendationEngine",
    "CTATracker",
    "CTAOptimizer",
    
    # Attribution
    "ConversionEventType",
    "AttributionModel",
    "ConversionEvent",
    "Lead",
    "ConversionTracker",
    "AttributionEngine",
    "ROIAnalyzer",
    
    # Lead Quality
    "LeadQualityMetrics",
    "LeadQualityScorer",
    "OpportunityFeedbackLoop",
]
