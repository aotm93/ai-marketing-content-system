"""
Quality Gate API Endpoints
Implements BUG-009: Enhanced content quality validation with detailed diagnostics

Endpoints:
- POST /api/v1/quality-gate/check - Full quality diagnostic
- POST /api/v1/quality-gate/similarity - Similarity check only
- POST /api/v1/quality-gate/quick-check - Fast basic check
- GET /api/v1/quality-gate/thresholds - Get current thresholds
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.auth import get_current_admin
from src.services.quality_gate import EnhancedQualityGate

router = APIRouter(prefix="/api/v1/quality-gate", tags=["quality-gate"])


# ==================== Request Models ====================

class ExistingContent(BaseModel):
    """Existing content for comparison"""
    id: str
    content: str
    url: Optional[str] = None


class QualityCheckRequest(BaseModel):
    """Full quality check request"""
    content: str
    content_id: str
    existing_content: Optional[List[ExistingContent]] = None
    target_keyword: Optional[str] = None
    components: Optional[List[str]] = None


class SimilarityCheckRequest(BaseModel):
    """Similarity-only check request"""
    content: str
    existing_content: List[ExistingContent]


class QuickCheckRequest(BaseModel):
    """Quick basic check request"""
    content: str
    target_keyword: Optional[str] = None


# ==================== Response Models ====================

class IssueResponse(BaseModel):
    """Quality issue response"""
    issue_id: str
    category: str
    severity: str
    title: str
    description: str
    location: Optional[str]
    fix_recommendation: str
    auto_fixable: bool
    estimated_fix_time: str


class QualityCheckResponse(BaseModel):
    """Quality check response"""
    content_id: str
    overall_score: float
    grade: str
    passed: bool
    can_publish: bool
    issues_count: int
    issues_by_severity: Dict[str, int]
    summary: str
    top_recommendations: List[str]


# ==================== Endpoints ====================

@router.post("/check", response_model=QualityCheckResponse)
async def full_quality_check(
    request: QualityCheckRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Run comprehensive quality diagnostic
    
    Performs multi-dimensional quality analysis:
    - Similarity detection (multi-algorithm)
    - Information increment validation
    - Structure analysis
    - SEO optimization check
    - Readability scoring
    - Completeness verification
    
    Returns detailed diagnostic with actionable fix recommendations.
    """
    try:
        service = EnhancedQualityGate()
        
        # Convert request to service format
        existing = None
        if request.existing_content:
            existing = [
                {"id": e.id, "content": e.content, "url": e.url}
                for e in request.existing_content
            ]
        
        diagnostic = await service.full_diagnostic(
            content=request.content,
            content_id=request.content_id,
            existing_content=existing,
            target_keyword=request.target_keyword,
            components=request.components
        )
        
        return QualityCheckResponse(
            content_id=diagnostic.content_id,
            overall_score=round(diagnostic.overall_score, 1),
            grade=diagnostic.grade,
            passed=diagnostic.passed,
            can_publish=diagnostic.can_publish,
            issues_count=len(diagnostic.issues),
            issues_by_severity=diagnostic._count_by_severity(),
            summary=diagnostic.summary,
            top_recommendations=diagnostic.top_recommendations
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check/detailed")
async def detailed_quality_check(
    request: QualityCheckRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Run quality check with full details
    
    Returns complete diagnostic including all issues,
    similarity analysis, and information analysis.
    """
    try:
        service = EnhancedQualityGate()
        
        existing = None
        if request.existing_content:
            existing = [
                {"id": e.id, "content": e.content, "url": e.url}
                for e in request.existing_content
            ]
        
        diagnostic = await service.full_diagnostic(
            content=request.content,
            content_id=request.content_id,
            existing_content=existing,
            target_keyword=request.target_keyword,
            components=request.components
        )
        
        return {
            "status": "success",
            "diagnostic": diagnostic.to_dict()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/similarity")
async def check_similarity(
    request: SimilarityCheckRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Check content similarity only
    
    Fast similarity check using multiple algorithms:
    - SequenceMatcher
    - Jaccard similarity
    - W-shingling
    
    Returns similarity scores and matching sections.
    """
    try:
        service = EnhancedQualityGate()
        
        existing = [
            {"id": e.id, "content": e.content, "url": e.url}
            for e in request.existing_content
        ]
        
        text_content = service._strip_html(request.content)
        
        similarity_result, issues = await service._analyze_similarity(
            request.content, text_content, existing
        )
        
        if similarity_result:
            return {
                "status": "success",
                "is_duplicate": similarity_result.is_duplicate,
                "overall_similarity": round(similarity_result.overall_similarity * 100, 1),
                "algorithm_scores": {
                    k: round(v * 100, 1) 
                    for k, v in similarity_result.algorithm_scores.items()
                },
                "matched_content_id": similarity_result.matched_content_id,
                "matched_url": similarity_result.matched_url,
                "matching_sections": similarity_result.matching_sections[:5],
                "issues": [i.to_dict() for i in issues]
            }
        else:
            return {
                "status": "success",
                "is_duplicate": False,
                "overall_similarity": 0,
                "message": "No similar content found"
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-check")
async def quick_quality_check(
    request: QuickCheckRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Quick basic quality check
    
    Fast check without similarity analysis.
    Useful for real-time validation during content creation.
    
    Checks:
    - Word count
    - Structure (headings, paragraphs)
    - Basic SEO (if keyword provided)
    - Readability
    """
    try:
        service = EnhancedQualityGate()
        
        text_content = service._strip_html(request.content)
        word_count = len(text_content.split())
        
        issues = []
        score = 100
        
        # Structure check
        structure_score, structure_issues = service._analyze_structure(request.content)
        issues.extend(structure_issues)
        score = min(score, structure_score)
        
        # SEO check (if keyword)
        if request.target_keyword:
            seo_score, seo_issues = service._analyze_seo(request.content, request.target_keyword)
            issues.extend(seo_issues)
            score = min(score, seo_score)
        
        # Word count
        if word_count < 500:
            score -= 20
            issues.append({
                "issue_id": "QUICK-001",
                "severity": "critical" if word_count < 300 else "high",
                "title": "Content too short",
                "description": f"Word count: {word_count} (need 500+)",
                "fix": f"Add {500 - word_count} more words"
            })
        
        # Quick pass/fail
        critical_count = len([i for i in issues if i.get("severity") == "critical"])
        
        return {
            "status": "success",
            "word_count": word_count,
            "score": round(score, 1),
            "passed": critical_count == 0 and score >= 60,
            "issues_count": len(issues),
            "critical_issues": critical_count,
            "quick_issues": [
                {
                    "title": i.get("title") or i.title if hasattr(i, 'title') else str(i),
                    "severity": i.get("severity") or (i.severity.value if hasattr(i, 'severity') else "medium")
                }
                for i in issues[:5]
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thresholds")
async def get_thresholds():
    """Get current quality thresholds"""
    service = EnhancedQualityGate()
    
    return {
        "status": "success",
        "thresholds": {
            "duplicate_threshold": service.DUPLICATE_THRESHOLD * 100,
            "high_similarity_threshold": service.HIGH_SIMILARITY_THRESHOLD * 100,
            "min_unique_info_percentage": service.MIN_UNIQUE_INFO_PERCENTAGE,
            "min_word_count": service.MIN_WORD_COUNT,
            "min_reading_grade": service.MIN_READING_GRADE,
            "max_reading_grade": service.MAX_READING_GRADE
        },
        "scoring_weights": service.SCORE_WEIGHTS,
        "grade_thresholds": service.GRADE_THRESHOLDS
    }


@router.get("/health")
async def quality_gate_health():
    """Health check for Quality Gate service"""
    return {
        "status": "healthy",
        "service": "QualityGate",
        "version": "2.0",
        "features": [
            "multi_algorithm_similarity",
            "information_increment_analysis",
            "detailed_diagnostics",
            "fix_recommendations",
            "auto_fix_suggestions"
        ]
    }
