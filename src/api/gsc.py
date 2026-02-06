
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from src.core.database import get_db
from src.integrations.gsc_client import GSCClient, GSCDataSync, GSCAuthMethod
from src.config import settings
from src.core.auth import get_current_admin

router = APIRouter(prefix="/api/v1/gsc", tags=["Google Search Console"])

class SyncRequest(BaseModel):
    days: int = 7
    force: bool = False

class OpportunityResponse(BaseModel):
    query: str
    page: str
    impressions: int
    clicks: int
    position: float
    potential_score: float

def get_gsc_client():
    """Dependency to get GSC Client"""
    if not settings.gsc_enabled:
        raise HTTPException(status_code=503, detail="GSC integration disabled")
        
    try:
        return GSCClient(
            site_url=settings.gsc_site_url,
            auth_method=GSCAuthMethod.SERVICE_ACCOUNT,
            credentials_json=settings.gsc_credentials_json,
            credentials_path=settings.gsc_credentials_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GSC Init Failed: {str(e)}")

@router.get("/status")
def get_status(
    client: GSCClient = Depends(get_gsc_client),
    admin: dict = Depends(get_current_admin)
):
    """Get GSC connection status"""
    try:
        return client.health_check()
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/sync")
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    client: GSCClient = Depends(get_gsc_client),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Trigger GSC data sync"""
    syncer = GSCDataSync(client, db)
    
    # Run sync in background? 
    # Actually, syncer needs db session. If we pass db session to background, it might close.
    # Better to run sync synchronously for now or handle DB inside background task properly.
    # Given GSC API latency, background is better. But providing DB session is tricky.
    
    # For MVP, we run valid async immediately (request will hang but it's okay for admin action)
    result = await syncer.sync_queries(days_back=request.days)
    return result

@router.get("/opportunities", response_model=List[OpportunityResponse])
def get_opportunities(
    limit: int = 50,
    client: GSCClient = Depends(get_gsc_client),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get low-hanging fruit opportunities"""
    opps = client.get_low_hanging_fruits(limit=limit)
    
    return [
        OpportunityResponse(
            query=o.query,
            page=o.page,
            impressions=o.impressions,
            clicks=o.clicks,
            position=o.position,
            potential_score=o.impressions * (20 - o.position)
        ) for o in opps
    ]


@router.get("/quota")
async def get_quota_status(
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Get GSC API quota status and usage statistics
    
    Returns:
    - Current day's quota consumption
    - Usage percentage
    - Status (healthy/warning/critical/exceeded)
    - Historical usage trend
    """
    from src.services.gsc_usage_tracker import GSCUsageTracker
    
    tracker = GSCUsageTracker(db)
    
    # Current quota status
    quota = tracker.get_quota_status()
    
    # Last 7 days history
    history = tracker.get_usage_history(days=7)
    
    # Usage breakdown by type
    breakdown = tracker.get_usage_by_type(days=7)
    
    return {
        "current": quota,
        "history": history,
        "breakdown_by_type": breakdown,
        "recommendations": generate_quota_recommendations(quota)
    }


def generate_quota_recommendations(quota: dict) -> list:
    """Generate recommendations based on quota status"""
    recommendations = []
    
    if quota["status"] == "exceeded":
        recommendations.append("⚠️ Quota exceeded! Wait until tomorrow or request increased quota from Google")
    elif quota["status"] == "critical":
        recommendations.append("🚨 Quota at 90%+ - Reduce sync frequency or batch operations")
    elif quota["status"] == "warning":
        recommendations.append("⚡ Quota at 80%+ - Consider optimizing query patterns")
    
    if quota["usage_percentage"] > 50:
        recommendations.append("📊 Consider reviewing sync schedule to spread load")
    
    return recommendations


@router.get("/quota/history")
async def get_quota_history(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get detailed quota usage history"""
    from src.services.gsc_usage_tracker import GSCUsageTracker
    
    tracker = GSCUsageTracker(db)
    history = tracker.get_usage_history(days=days)
    
    return {
        "days": days,
        "data": history,
        "summary": {
            "total_calls": sum(d["api_calls"] for d in history),
            "total_rows": sum(d["rows_fetched"] for d in history),
            "avg_daily_calls": sum(d["api_calls"] for d in history) / len(history) if history else 0
        }
    }

