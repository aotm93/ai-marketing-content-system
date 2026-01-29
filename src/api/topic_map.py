"""
TopicMap API Endpoints
Implements BUG-008: Enhanced TopicMap with Hub-Spoke, Intent Grouping, and Cannibalization Detection

Endpoints:
- POST /api/v1/topic-map/analyze - Full cluster analysis
- POST /api/v1/topic-map/detect-hub - Detect hub/spoke structure
- POST /api/v1/topic-map/classify-intent - Classify page intents
- POST /api/v1/topic-map/detect-cannibalization - Detect keyword cannibalization
- POST /api/v1/topic-map/recommendations - Get smart link recommendations
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.auth import get_current_admin
from src.services.topic_map import TopicMapService, SearchIntent

router = APIRouter(prefix="/api/v1/topic-map", tags=["topic-map"])


# ==================== Request Models ====================

class PageData(BaseModel):
    """Page data for analysis"""
    page_id: int
    url: str
    title: str
    keyword: str
    word_count: int = 0
    internal_links_in: int = 0
    internal_links_out: int = 0
    impressions: int = 0
    clicks: int = 0
    position: float = 0.0
    ctr: float = 0.0


class GSCRow(BaseModel):
    """GSC data row"""
    query: str
    page: str
    impressions: int
    clicks: int
    position: float
    ctr: float = 0.0


class AnalyzeClusterRequest(BaseModel):
    """Full cluster analysis request"""
    cluster_name: str
    pages: List[PageData]
    gsc_data: Optional[List[GSCRow]] = None
    root_keyword: Optional[str] = None


class DetectHubRequest(BaseModel):
    """Hub detection request"""
    pages: List[PageData]
    root_keyword: str


class ClassifyIntentRequest(BaseModel):
    """Intent classification request"""
    pages: List[PageData]


class DetectCannibalizationRequest(BaseModel):
    """Cannibalization detection request"""
    gsc_data: List[GSCRow]
    min_impressions: int = 100


class RecommendationsRequest(BaseModel):
    """Smart recommendations request"""
    pages: List[PageData]
    hub_page: Optional[PageData] = None
    existing_links: Optional[List[List[int]]] = None  # [[source_id, target_id], ...]


# ==================== Endpoints ====================

@router.post("/analyze")
async def analyze_cluster(
    request: AnalyzeClusterRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Perform comprehensive topic cluster analysis
    
    This is the main endpoint that combines:
    - Hub/Spoke structure detection
    - Intent-based page grouping
    - Keyword cannibalization detection
    - Smart internal link recommendations
    - Cluster health scoring
    
    Returns a complete analysis with actionable insights.
    """
    try:
        service = TopicMapService(db)
        
        # Convert Pydantic models to dicts
        pages = [p.model_dump() for p in request.pages]
        gsc_data = [g.model_dump() for g in request.gsc_data] if request.gsc_data else None
        
        analysis = await service.analyze_cluster(
            cluster_name=request.cluster_name,
            pages=pages,
            gsc_data=gsc_data,
            root_keyword=request.root_keyword
        )
        
        return {
            "status": "success",
            "analysis": analysis.to_dict()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-hub")
async def detect_hub_spoke(
    request: DetectHubRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Detect Hub/Spoke structure from a list of pages
    
    The algorithm identifies the most likely hub page based on:
    - Content length (pillar content tends to be longer)
    - Keyword match with root topic
    - GSC impressions (broader reach = hub)
    - Internal link patterns
    
    Returns the identified hub and spoke pages with recommendations.
    """
    try:
        service = TopicMapService(db)
        pages = [p.model_dump() for p in request.pages]
        
        result = service.detect_hub_spoke_structure(pages, request.root_keyword)
        
        return {
            "status": "success",
            **result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify-intent")
async def classify_page_intents(
    request: ClassifyIntentRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Classify pages by search intent
    
    Intent types:
    - Informational: "what is", "how to", guides
    - Commercial: "best", "review", comparisons
    - Transactional: "buy", "price", shopping
    - Navigational: brand/site-specific
    
    Returns pages grouped by intent for strategic linking.
    """
    try:
        service = TopicMapService(db)
        pages = [p.model_dump() for p in request.pages]
        
        grouped = service.group_pages_by_intent(pages)
        
        # Add individual classifications
        classifications = []
        for page in request.pages:
            intent = service.classify_intent(page.keyword, page.title)
            classifications.append({
                "page_id": page.page_id,
                "url": page.url,
                "keyword": page.keyword,
                "intent": intent.value
            })
        
        return {
            "status": "success",
            "intent_groups": {k: len(v) for k, v in grouped.items()},
            "classifications": classifications,
            "distribution": {
                SearchIntent.INFORMATIONAL.value: len(grouped.get(SearchIntent.INFORMATIONAL.value, [])),
                SearchIntent.COMMERCIAL.value: len(grouped.get(SearchIntent.COMMERCIAL.value, [])),
                SearchIntent.TRANSACTIONAL.value: len(grouped.get(SearchIntent.TRANSACTIONAL.value, [])),
                SearchIntent.NAVIGATIONAL.value: len(grouped.get(SearchIntent.NAVIGATIONAL.value, []))
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-cannibalization")
async def detect_cannibalization(
    request: DetectCannibalizationRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Detect keyword cannibalization from GSC data
    
    Cannibalization occurs when multiple pages compete for the same keyword,
    causing:
    - Confusion for search engines
    - Diluted page authority
    - Lower overall rankings
    
    Returns issues sorted by severity with specific recommendations.
    """
    try:
        service = TopicMapService(db)
        gsc_data = [g.model_dump() for g in request.gsc_data]
        
        issues = service.detect_cannibalization(gsc_data, request.min_impressions)
        
        # Summarize by severity
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        total_traffic_loss = 0
        for issue in issues:
            severity_counts[issue.severity] += 1
            total_traffic_loss += issue.estimated_traffic_loss
        
        return {
            "status": "success",
            "total_issues": len(issues),
            "severity_summary": severity_counts,
            "estimated_total_traffic_loss": total_traffic_loss,
            "issues": [issue.to_dict() for issue in issues[:20]],  # Top 20
            "recommendation": (
                f"Found {len(issues)} cannibalization issues. "
                f"Focus on {severity_counts['critical']} critical and {severity_counts['high']} high severity issues first."
                if issues else "No significant cannibalization detected."
            )
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations")
async def get_smart_recommendations(
    request: RecommendationsRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Generate smart internal link recommendations
    
    Uses multiple signals:
    - Hub/Spoke structure (prioritize cluster links)
    - Intent matching (natural user journey)
    - Semantic relatedness (keyword overlap)
    - Performance data (boost underperforming pages)
    
    Returns prioritized recommendations ready for implementation.
    """
    try:
        service = TopicMapService(db)
        
        pages = [p.model_dump() for p in request.pages]
        hub_page = request.hub_page.model_dump() if request.hub_page else None
        existing_links = [tuple(link) for link in request.existing_links] if request.existing_links else None
        
        recommendations = service.generate_smart_recommendations(
            pages, hub_page, existing_links
        )
        
        # Group by priority
        by_priority = {
            "high": [],
            "medium": [],
            "low": []
        }
        
        for rec in recommendations:
            by_priority[rec.priority].append(rec.to_dict())
        
        return {
            "status": "success",
            "total_recommendations": len(recommendations),
            "by_priority": {k: len(v) for k, v in by_priority.items()},
            "recommendations": [r.to_dict() for r in recommendations],
            "high_priority": by_priority["high"],
            "implementation_order": [
                f"1. Add {len(by_priority['high'])} high-priority links (hub-spoke structure)",
                f"2. Add {len(by_priority['medium'])} medium-priority links (intent matching)",
                f"3. Consider {len(by_priority['low'])} low-priority links (performance boost)"
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def topic_map_health():
    """Health check for TopicMap service"""
    return {
        "status": "healthy",
        "service": "TopicMap",
        "features": [
            "hub_spoke_detection",
            "intent_classification",
            "cannibalization_detection",
            "smart_recommendations"
        ]
    }
