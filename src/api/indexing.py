from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from src.core.auth import get_current_admin
from src.core.database import get_db

router = APIRouter(prefix="/api/v1/indexing", tags=["indexing"])


class IndexNowRequest(BaseModel):
    """IndexNow submission request"""
    urls: List[str]


class SitemapSubmitRequest(BaseModel):
    """Sitemap submission request"""
    sitemap_url: str
    target: str = "google" # google or bing


@router.post("/indexnow")
async def submit_to_indexnow(
    request: IndexNowRequest,
    admin: dict = Depends(get_current_admin)
):
    """Submit URLs to IndexNow"""
    from src.integrations.indexnow import IndexNowClient
    from src.config import settings
    import os
    
    # Get config
    api_key = getattr(settings, "indexnow_api_key", None) or os.getenv("INDEXNOW_KEY")
    # Provide a fallback just in case for testing
    if not api_key:
         api_key = "test-key-change-me"
         
    host = getattr(settings, "site_domain", None) or os.getenv("SITE_DOMAIN", "localhost")
    
    client = IndexNowClient(
        api_key=api_key,
        host=host
    )
    
    result = await client.submit_urls(request.urls)
    return result


@router.get("/status")
async def get_indexing_status(
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get overall indexing status"""
    from src.integrations.indexing_monitor import IndexingMonitor
    
    monitor = IndexingMonitor(db)
    
    # In a real scenario, we'd fetch recent URLs to check or return cached stats
    # For now, return the trend and summary
    
    trend = monitor.get_indexing_trend()
    
    return {
        "status": "success",
        "trend": trend,
        "summary": {
             "total_pages_tracked": 0, # To be implemented with DB query
             "indexed_pages": 0,
             "indexing_rate": 0
        }
    }


@router.post("/check")
async def check_indexing(
    request: IndexNowRequest,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Check indexing status for specific URLs"""
    from src.integrations.gsc_client import GoogleSearchConsoleClient
    from src.integrations.indexing_monitor import IndexingMonitor
    from src.config import settings
    import os
    
    # Needs GSC credentials
    creds_path = getattr(settings, "gsc_credentials_path", None) or os.getenv("GSC_CREDENTIALS_PATH")
    if not creds_path or not os.path.exists(creds_path):
        raise HTTPException(status_code=400, detail="GSC credentials not configured")
        
    try:
        gsc_client = GoogleSearchConsoleClient(creds_path)
        # Authenticate? The client usually handles this in init or first call
        
        monitor = IndexingMonitor(db)
        result = await monitor.check_indexing_status(request.urls, gsc_client)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pages/attention")
async def get_pages_needing_attention(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get pages that need manual attention"""
    from src.services.index_checker import IndexChecker
    
    checker = IndexChecker(db)
    return checker.get_pages_needing_attention(limit)


@router.post("/check/{post_id}")
async def check_page_index_status(
    post_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Trigger index check for a specific page"""
    from src.models.indexing_status import IndexingStatus
    
    page = db.query(IndexingStatus).filter(
        IndexingStatus.post_id == post_id
    ).first()
    
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Run check in background
    from src.services.index_checker import IndexChecker
    checker = IndexChecker(db)
    background_tasks.add_task(
        checker.check_page_index_status,
        page.page_url
    )
    
    return {"status": "checking", "url": page.page_url}


@router.post("/check-all")
async def run_index_checks(
    batch_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Run scheduled index checks"""
    from src.services.index_checker import IndexChecker
    
    checker = IndexChecker(db)
    results = await checker.run_scheduled_checks(batch_size)
    return results
