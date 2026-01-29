"""
Opportunities API
Manage and execute SEO opportunities (BUG-003 Enhanced)

Features:
- Full filtering (position, impressions, ctr, score)
- Multi-field sorting
- Bulk actions
- Execute actions (generate/optimize/refresh)
- Statistics endpoint
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func, and_, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from enum import Enum

from src.core.database import get_db
from src.core.auth import get_current_admin
from src.models.gsc_data import Opportunity

router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


# ==================== Enums ====================

class OpportunityTypeEnum(str, Enum):
    CONTENT_GAP = "content_gap"
    CTR_OPTIMIZE = "ctr_optimize"
    POSITION_IMPROVE = "position_improve"
    CONTENT_REFRESH = "content_refresh"
    NEW_PAGE = "new_page"


class OpportunityStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SortFieldEnum(str, Enum):
    SCORE = "score"
    IMPRESSIONS = "impressions"
    CLICKS = "clicks"
    CTR = "ctr"
    POSITION = "position"
    CREATED_AT = "created_at"


class ActionTypeEnum(str, Enum):
    GENERATE = "generate"
    OPTIMIZE = "optimize"
    REFRESH = "refresh"
    SKIP = "skip"


# ==================== Request/Response Models ====================

class OpportunityResponse(BaseModel):
    id: int
    opportunity_id: str
    type: str
    target_query: Optional[str]
    target_page: Optional[str]
    score: float
    status: str
    priority: str
    impressions: Optional[int] = 0
    clicks: Optional[int] = 0
    position: Optional[float] = 0
    ctr: Optional[float] = 0
    potential_traffic: Optional[int] = 0
    created_at: datetime
    executed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class OpportunityListResponse(BaseModel):
    opportunities: List[OpportunityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    filters_applied: dict


class OpportunityStatsResponse(BaseModel):
    total_opportunities: int
    by_type: dict
    by_status: dict
    by_priority: dict
    total_potential_traffic: int
    avg_score: float


class ExecuteRequest(BaseModel):
    action: ActionTypeEnum
    params: Optional[dict] = {}


class BulkExecuteRequest(BaseModel):
    opportunity_ids: List[str]
    action: ActionTypeEnum
    params: Optional[dict] = {}


# ==================== Endpoints ====================

@router.get("/", response_model=OpportunityListResponse)
async def list_opportunities(
    # Filtering
    type: Optional[str] = Query(None, description="Filter by opportunity type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority (high/medium/low)"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum score"),
    max_score: Optional[float] = Query(None, ge=0, le=100, description="Maximum score"),
    min_impressions: Optional[int] = Query(None, ge=0, description="Minimum impressions"),
    max_impressions: Optional[int] = Query(None, description="Maximum impressions"),
    min_position: Optional[float] = Query(None, ge=1, description="Minimum position"),
    max_position: Optional[float] = Query(None, le=100, description="Maximum position"),
    min_ctr: Optional[float] = Query(None, ge=0, description="Minimum CTR (0-1)"),
    search: Optional[str] = Query(None, description="Search in query/page"),
    # Sorting
    sort_by: SortFieldEnum = Query(SortFieldEnum.SCORE, description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    List SEO opportunities with full filtering and sorting
    
    Supports:
    - Filter by type, status, priority
    - Filter by score, impressions, position, CTR ranges
    - Search in query/page text
    - Sort by any metric
    - Pagination
    """
    query = db.query(Opportunity)
    filters_applied = {}
    
    # Apply filters
    if type:
        query = query.filter(Opportunity.opportunity_type == type)
        filters_applied["type"] = type
    
    if status:
        query = query.filter(Opportunity.status == status)
        filters_applied["status"] = status
    
    if priority:
        query = query.filter(Opportunity.priority == priority)
        filters_applied["priority"] = priority
    
    if min_score is not None:
        query = query.filter(Opportunity.score >= min_score)
        filters_applied["min_score"] = min_score
    
    if max_score is not None:
        query = query.filter(Opportunity.score <= max_score)
        filters_applied["max_score"] = max_score
    
    if min_impressions is not None:
        query = query.filter(Opportunity.current_impressions >= min_impressions)
        filters_applied["min_impressions"] = min_impressions
    
    if max_impressions is not None:
        query = query.filter(Opportunity.current_impressions <= max_impressions)
        filters_applied["max_impressions"] = max_impressions
    
    if min_position is not None:
        query = query.filter(Opportunity.current_position >= min_position)
        filters_applied["min_position"] = min_position
    
    if max_position is not None:
        query = query.filter(Opportunity.current_position <= max_position)
        filters_applied["max_position"] = max_position
    
    if min_ctr is not None:
        query = query.filter(Opportunity.current_ctr >= min_ctr)
        filters_applied["min_ctr"] = min_ctr
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Opportunity.target_query.ilike(search_term),
                Opportunity.target_page.ilike(search_term)
            )
        )
        filters_applied["search"] = search
    
    # Sorting
    sort_column = {
        SortFieldEnum.SCORE: Opportunity.score,
        SortFieldEnum.IMPRESSIONS: Opportunity.current_impressions,
        SortFieldEnum.CLICKS: Opportunity.current_clicks,
        SortFieldEnum.CTR: Opportunity.current_ctr,
        SortFieldEnum.POSITION: Opportunity.current_position,
        SortFieldEnum.CREATED_AT: Opportunity.created_at
    }.get(sort_by, Opportunity.score)
    
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # Get total count
    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    
    # Pagination
    offset = (page - 1) * page_size
    opportunities = query.offset(offset).limit(page_size).all()
    
    return OpportunityListResponse(
        opportunities=[
            OpportunityResponse(
                id=o.id,
                opportunity_id=o.opportunity_id,
                type=o.opportunity_type,
                target_query=o.target_query,
                target_page=o.target_page,
                score=o.score or 0,
                status=o.status,
                priority=o.priority,
                impressions=o.current_impressions or 0,
                clicks=o.current_clicks or 0,
                position=o.current_position or 0,
                ctr=o.current_ctr or 0,
                potential_traffic=o.potential_clicks or 0,
                created_at=o.created_at,
                executed_at=o.executed_at
            ) for o in opportunities
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        filters_applied=filters_applied
    )


@router.get("/stats", response_model=OpportunityStatsResponse)
async def get_opportunity_stats(
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get opportunity statistics summary"""
    
    # Total count
    total = db.query(Opportunity).count()
    
    # By type
    type_counts = db.query(
        Opportunity.opportunity_type,
        func.count(Opportunity.id)
    ).group_by(Opportunity.opportunity_type).all()
    by_type = {t: c for t, c in type_counts}
    
    # By status
    status_counts = db.query(
        Opportunity.status,
        func.count(Opportunity.id)
    ).group_by(Opportunity.status).all()
    by_status = {s: c for s, c in status_counts}
    
    # By priority
    priority_counts = db.query(
        Opportunity.priority,
        func.count(Opportunity.id)
    ).group_by(Opportunity.priority).all()
    by_priority = {p: c for p, c in priority_counts}
    
    # Aggregates
    aggregates = db.query(
        func.sum(Opportunity.potential_clicks).label("total_traffic"),
        func.avg(Opportunity.score).label("avg_score")
    ).first()
    
    return OpportunityStatsResponse(
        total_opportunities=total,
        by_type=by_type,
        by_status=by_status,
        by_priority=by_priority,
        total_potential_traffic=aggregates.total_traffic or 0,
        avg_score=round(aggregates.avg_score or 0, 1)
    )


@router.get("/{opportunity_id}")
async def get_opportunity(
    opportunity_id: str,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get single opportunity details"""
    opp = db.query(Opportunity).filter(Opportunity.opportunity_id == opportunity_id).first()
    
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    return {
        "status": "success",
        "opportunity": OpportunityResponse(
            id=opp.id,
            opportunity_id=opp.opportunity_id,
            type=opp.opportunity_type,
            target_query=opp.target_query,
            target_page=opp.target_page,
            score=opp.score or 0,
            status=opp.status,
            priority=opp.priority,
            impressions=opp.current_impressions or 0,
            clicks=opp.current_clicks or 0,
            position=opp.current_position or 0,
            ctr=opp.current_ctr or 0,
            potential_traffic=opp.potential_clicks or 0,
            created_at=opp.created_at,
            executed_at=opp.executed_at
        ).model_dump()
    }


@router.post("/{opportunity_id}/execute")
async def execute_opportunity(
    opportunity_id: str,
    request: ExecuteRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Execute an opportunity action
    
    Actions:
    - generate: Create new content
    - optimize: Optimize existing content (title, meta, etc.)
    - refresh: Update content with new information
    - skip: Mark as skipped
    """
    opp = db.query(Opportunity).filter(Opportunity.opportunity_id == opportunity_id).first()
    
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Handle skip action
    if request.action == ActionTypeEnum.SKIP:
        opp.status = "skipped"
        opp.executed_at = datetime.now()
        db.commit()
        return {
            "status": "success",
            "message": f"Opportunity {opportunity_id} marked as skipped",
            "opportunity_id": opportunity_id
        }
    
    # Update status
    opp.status = "in_progress"
    opp.action_type = request.action.value
    opp.assigned_to = admin.get("username", "admin")
    opp.executed_at = datetime.now()
    db.commit()
    
    try:
        result_message = ""
        
        if request.action == ActionTypeEnum.GENERATE:
            # Trigger new content generation
            # In production, this would queue a job
            result_message = f"New content generation started for query: {opp.target_query}"
            
        elif request.action == ActionTypeEnum.OPTIMIZE:
            # Trigger CTR optimization
            result_message = f"CTR optimization started for page: {opp.target_page}"
            
        elif request.action == ActionTypeEnum.REFRESH:
            # Trigger content refresh
            result_message = f"Content refresh started for page: {opp.target_page}"
        
        return {
            "status": "success",
            "message": result_message,
            "opportunity_id": opportunity_id,
            "action": request.action.value,
            "job_id": f"job_{opportunity_id}_{request.action.value}"
        }
        
    except Exception as e:
        opp.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-execute")
async def bulk_execute_opportunities(
    request: BulkExecuteRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Execute action on multiple opportunities"""
    
    results = []
    success_count = 0
    failed_count = 0
    
    for opp_id in request.opportunity_ids:
        opp = db.query(Opportunity).filter(Opportunity.opportunity_id == opp_id).first()
        
        if not opp:
            results.append({"opportunity_id": opp_id, "status": "not_found"})
            failed_count += 1
            continue
        
        try:
            if request.action == ActionTypeEnum.SKIP:
                opp.status = "skipped"
            else:
                opp.status = "in_progress"
                opp.action_type = request.action.value
            
            opp.assigned_to = admin.get("username", "admin")
            opp.executed_at = datetime.now()
            
            results.append({"opportunity_id": opp_id, "status": "success"})
            success_count += 1
            
        except Exception as e:
            results.append({"opportunity_id": opp_id, "status": "failed", "error": str(e)})
            failed_count += 1
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Bulk action completed: {success_count} success, {failed_count} failed",
        "action": request.action.value,
        "results": results
    }


@router.get("/types/list")
async def get_opportunity_types():
    """Get available opportunity types"""
    return {
        "types": [
            {"value": "content_gap", "label": "Content Gap", "description": "Missing content for high-potential query"},
            {"value": "ctr_optimize", "label": "CTR Optimize", "description": "Low CTR despite good position"},
            {"value": "position_improve", "label": "Position Improve", "description": "Good impressions, position can improve"},
            {"value": "content_refresh", "label": "Content Refresh", "description": "Existing content needs update"},
            {"value": "new_page", "label": "New Page", "description": "Opportunity for new pSEO page"}
        ]
    }


@router.get("/actions/list")
async def get_available_actions():
    """Get available opportunity actions"""
    return {
        "actions": [
            {"value": "generate", "label": "Generate", "description": "Create new content", "icon": "✨"},
            {"value": "optimize", "label": "Optimize", "description": "Optimize title/meta for CTR", "icon": "🎯"},
            {"value": "refresh", "label": "Refresh", "description": "Update content with new info", "icon": "🔄"},
            {"value": "skip", "label": "Skip", "description": "Mark as not actionable", "icon": "⏭️"}
        ]
    }
