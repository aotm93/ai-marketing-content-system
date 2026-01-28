
from fastapi import APIRouter, BackgroundTasks, Request
from typing import Dict, Any, Optional
from pydantic import BaseModel
from src.conversion.dynamic_cta import CTATracker, CTARecommendationEngine, UserIntent
from src.conversion.attribution import ConversionTracker, ConversionEvent, ConversionEventType
import uuid
from datetime import datetime

router = APIRouter(prefix="/conversion", tags=["conversion"])

# Shared singleton instances (In prod, use dependency injection)
cta_tracker = CTATracker()
cta_engine = CTARecommendationEngine()
conv_tracker = ConversionTracker()

class TrackRequest(BaseModel):
    event_type: str  # pageview, click, form_submit
    page_url: str
    variant_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CTARequest(BaseModel):
    page_url: str
    page_type: str = "blog_post"
    intent: str = "informational"
    industry: Optional[str] = None

from src.core.database import SessionLocal

@router.post("/track")
async def track_event(data: TrackRequest, request: Request, background_tasks: BackgroundTasks):
    """Track a conversion event"""
    
    # Enrichment logic here (headers, IP)
    
    # Dispatch tracking task
    background_tasks.add_task(
        _process_tracking,
        data
    )
    
    return {"status": "accepted"}

def _process_tracking(data: TrackRequest):
    """Process event in background with DB session"""
    db = SessionLocal()
    try:
        # 1. Track CTA stats
        if data.variant_id:
            if data.event_type == "impression":
                cta_tracker.track_impression(
                    data.variant_id, 
                    data.page_url, 
                    db,
                    user_id=data.user_id
                )
            elif data.event_type == "click":
                cta_tracker.track_click(
                    data.variant_id, 
                    data.page_url, 
                    db,
                    user_id=data.user_id
                )
                
        # 2. Track Attribution Journey
        event_id = str(uuid.uuid4())
        # Safe conversion of string to enum
        try:
            event_type_enum = ConversionEventType(data.event_type)
        except ValueError:
            event_type_enum = ConversionEventType.PAGEVIEW
        
        event = ConversionEvent(
            event_id=event_id,
            event_type=event_type_enum,
            user_id=data.user_id,
            session_id=data.session_id,
            page_url=data.page_url,
            timestamp=datetime.now()
        )
        conv_tracker.track_event(event, db)
        
    except Exception as e:
        # In prod, log critical error
        print(f"Tracking error: {e}")
    finally:
        db.close()

@router.post("/cta/recommend")
async def recommend_cta(data: CTARequest):
    """Get optimized CTA for current context"""
    try:
        intent_enum = UserIntent(data.intent)
    except ValueError:
        intent_enum = UserIntent.INFORMATIONAL
        
    variants = cta_engine.recommend_ctas(
        intent=intent_enum,
        page_type=data.page_type,
        industry=data.industry
    )
    
    # Convert to dict
    return {
        "variants": [v.to_dict() for v in variants],
        "primary": variants[0].to_dict() if variants else None
    }
