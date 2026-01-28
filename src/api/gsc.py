
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
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
