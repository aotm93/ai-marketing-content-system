"""
Cannibalization Detection API Endpoints
Implements BUG-013: Enhanced keyword cannibalization detection

Endpoints:
- POST /api/v1/cannibalization/analyze - Full cannibalization analysis
- POST /api/v1/cannibalization/check-query - Check specific query
- POST /api/v1/cannibalization/recommendations - Get merge/redirect recommendations
- GET /api/v1/cannibalization/health - Overall cannibalization health
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from src.core.database import get_db
from src.core.auth import get_current_admin
from src.services.cannibalization import CannibalizationDetector

router = APIRouter(prefix="/api/v1/cannibalization", tags=["cannibalization"])


# ==================== Request Models ====================

class GSCDataRow(BaseModel):
    """GSC data row for analysis"""
    query: str
    page: str
    impressions: int
    clicks: int
    position: float
    ctr: float = 0.0
    date: Optional[str] = None
    page_id: Optional[int] = None
    title: Optional[str] = None
    word_count: Optional[int] = 0
    internal_links: Optional[int] = 0
    quality_score: Optional[float] = 70.0


class PageContent(BaseModel):
    """Page content for semantic analysis"""
    url: str
    content: str


class AnalyzeRequest(BaseModel):
    """Full analysis request"""
    gsc_data: List[GSCDataRow]
    page_content: Optional[List[PageContent]] = None
    historical_data: Optional[List[GSCDataRow]] = None
    min_impressions: int = 50


class QueryCheckRequest(BaseModel):
    """Check specific query request"""
    query: str
    pages: List[GSCDataRow]
    page_content: Optional[List[PageContent]] = None


class RecommendationsRequest(BaseModel):
    """Get recommendations for top issues"""
    gsc_data: List[GSCDataRow]
    max_issues: int = 10
    min_severity: str = "medium"  # critical, high, medium, low


# ==================== Endpoints ====================

@router.post("/analyze")
async def analyze_cannibalization(
    request: AnalyzeRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Perform comprehensive cannibalization analysis
    
    Analyzes GSC data to detect keyword cannibalization:
    - Identifies queries with multiple ranking pages
    - Calculates semantic similarity between competing pages
    - Analyzes URL structure patterns
    - Tracks ranking volatility
    - Generates actionable recommendations
    
    Returns complete analysis with prioritized issues.
    """
    try:
        detector = CannibalizationDetector()
        
        # Convert request data
        gsc_data = [row.model_dump() for row in request.gsc_data]
        
        page_content = None
        if request.page_content:
            page_content = {pc.url: pc.content for pc in request.page_content}
        
        historical_data = None
        if request.historical_data:
            historical_data = [row.model_dump() for row in request.historical_data]
        
        report = await detector.analyze(
            gsc_data=gsc_data,
            page_content=page_content,
            historical_data=historical_data,
            min_impressions=request.min_impressions
        )
        
        return {
            "status": "success",
            "report": report.to_dict()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-query")
async def check_query_cannibalization(
    request: QueryCheckRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Check cannibalization for a specific query
    
    Analyze if multiple pages are competing for the same keyword.
    Useful for quick checks during content planning.
    """
    try:
        detector = CannibalizationDetector()
        
        # Convert to expected format
        gsc_data = [row.model_dump() for row in request.pages]
        
        # Add query to each row if not present
        for row in gsc_data:
            if not row.get("query"):
                row["query"] = request.query
        
        page_content = None
        if request.page_content:
            page_content = {pc.url: pc.content for pc in request.page_content}
        
        # Run analysis for this specific query
        report = await detector.analyze(
            gsc_data=gsc_data,
            page_content=page_content,
            min_impressions=0  # No threshold for specific query check
        )
        
        if report.issues:
            issue = report.issues[0]
            return {
                "status": "success",
                "has_cannibalization": True,
                "query": request.query,
                "severity": issue.severity.value,
                "type": issue.cannibalization_type.value,
                "competing_pages_count": len(issue.competing_pages),
                "competing_pages": [p.to_dict() for p in issue.competing_pages],
                "recommendation": {
                    "action": issue.recommended_action.value,
                    "winner_page": issue.winner_page,
                    "details": issue.action_details,
                    "steps": issue.implementation_steps
                }
            }
        else:
            return {
                "status": "success",
                "has_cannibalization": False,
                "query": request.query,
                "message": "No cannibalization detected for this query"
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations")
async def get_cannibalization_recommendations(
    request: RecommendationsRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Get actionable recommendations for top cannibalization issues
    
    Returns prioritized recommendations with:
    - Winner page (page to keep)
    - Recommended action (merge, redirect, differentiate)
    - Step-by-step implementation guide
    - Expected improvement
    """
    try:
        detector = CannibalizationDetector()
        
        gsc_data = [row.model_dump() for row in request.gsc_data]
        
        report = await detector.analyze(
            gsc_data=gsc_data,
            min_impressions=50
        )
        
        # Filter by severity
        severity_order = ["critical", "high", "medium", "low"]
        min_idx = severity_order.index(request.min_severity) if request.min_severity in severity_order else 2
        allowed_severities = set(severity_order[:min_idx + 1])
        
        filtered_issues = [
            i for i in report.issues 
            if i.severity.value in allowed_severities
        ][:request.max_issues]
        
        recommendations = []
        for issue in filtered_issues:
            recommendations.append({
                "query": issue.query,
                "severity": issue.severity.value,
                "type": issue.cannibalization_type.value,
                "action": issue.recommended_action.value,
                "winner_page": issue.winner_page,
                "loser_pages": [p.page_url for p in issue.competing_pages if p.page_url != issue.winner_page],
                "action_details": issue.action_details,
                "implementation_steps": issue.implementation_steps,
                "expected_improvement": issue.expected_improvement,
                "estimated_traffic_recovery": issue.estimated_traffic_loss,
                "priority_score": {
                    "critical": 100, "high": 75, "medium": 50, "low": 25
                }.get(issue.severity.value, 25)
            })
        
        return {
            "status": "success",
            "total_recommendations": len(recommendations),
            "estimated_total_traffic_recovery": sum(r["estimated_traffic_recovery"] for r in recommendations),
            "recommendations": recommendations,
            "implementation_order": [
                f"{i+1}. {r['query']} ({r['severity']}): {r['action'].replace('_', ' ')}"
                for i, r in enumerate(recommendations)
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-scan")
async def quick_cannibalization_scan(
    request: AnalyzeRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Quick cannibalization scan
    
    Fast scan that returns summary without full details.
    Useful for dashboard widgets and periodic checks.
    """
    try:
        detector = CannibalizationDetector()
        
        gsc_data = [row.model_dump() for row in request.gsc_data]
        
        report = await detector.analyze(
            gsc_data=gsc_data,
            min_impressions=request.min_impressions
        )
        
        return {
            "status": "success",
            "scan_date": datetime.now().isoformat(),
            "queries_analyzed": report.analyzed_queries,
            "issues_found": report.total_issues,
            "issues_by_severity": report.issues_by_severity,
            "health_score": round(report.health_score, 1),
            "estimated_traffic_at_risk": report.estimated_total_traffic_loss,
            "top_3_issues": [
                {
                    "query": i.query,
                    "severity": i.severity.value,
                    "competing_pages": len(i.competing_pages),
                    "action": i.recommended_action.value
                }
                for i in report.issues[:3]
            ],
            "summary": report.summary
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def cannibalization_health():
    """Health check for Cannibalization Detection service"""
    return {
        "status": "healthy",
        "service": "CannibalizationDetector",
        "version": "1.0",
        "features": [
            "semantic_similarity_analysis",
            "url_structure_analysis",
            "ranking_volatility_tracking",
            "intelligent_merge_recommendations",
            "traffic_loss_estimation"
        ],
        "detection_types": [
            "keyword_overlap",
            "content_duplicate",
            "url_conflict",
            "intent_mismatch",
            "ranking_split"
        ],
        "action_types": [
            "merge_content",
            "redirect_301",
            "differentiate",
            "canonical",
            "noindex",
            "internal_link",
            "monitor",
            "retarget"
        ]
    }
