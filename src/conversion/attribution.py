"""
Conversion Tracking and Attribution System
Implements P3-2: Conversion tracking with page/topic/template attribution

Features:
- Event tracking (pageview, click, form_submit, lead)
- Multi-touch attribution
- ROI calculation by page/topic/template
- Lead quality scoring
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ConversionEventType(str, Enum):
    """Types of conversion events"""
    PAGEVIEW = "pageview"
    CLICK = "click"
    FORM_SUBMIT = "form_submit"
    LEAD_CREATED = "lead_created"
    QUALIFIED_LEAD = "qualified_lead"
    OPPORTUNITY = "opportunity"
    WON = "won"
    LOST = "lost"


class AttributionModel(str, Enum):
    """Attribution models"""
    FIRST_TOUCH = "first_touch"       # Credit to first touchpoint
    LAST_TOUCH = "last_touch"         # Credit to last touchpoint
    LINEAR = "linear"                  # Equal credit to all
    TIME_DECAY = "time_decay"         # More credit to recent
    POSITION_BASED = "position_based" # 40% first, 40% last, 20% middle


@dataclass
class ConversionEvent:
    """Single conversion event"""
    event_id: str
    event_type: ConversionEventType
    user_id: Optional[str]
    session_id: Optional[str]
    page_url: str
    page_id: Optional[int] = None
    topic_id: Optional[int] = None
    template_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Conversion details
    conversion_value: Optional[float] = None
    lead_id: Optional[str] = None
    
    # Attribution metadata
    referrer: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "page_url": self.page_url,
            "page_id": self.page_id,
            "topic_id": self.topic_id,
            "template_id": self.template_id,
            "timestamp": self.timestamp.isoformat(),
            "conversion_value": self.conversion_value,
            "lead_id": self.lead_id
        }


@dataclass
class Lead:
    """Lead/conversion record"""
    lead_id: str
    created_at: datetime
    user_id: Optional[str] = None
    
    # Lead info
    email: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    
    # Qualification
    lead_score: int = 0  # 0-100
    lead_status: str = "new"  # new, qualified, opportunity, won, lost
    
    # Value
    estimated_value: Optional[float] = None
    actual_value: Optional[float] = None
    
    # Attribution
    first_touch_page: Optional[str] = None
    last_touch_page: Optional[str] = None
    touchpoint_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "lead_id": self.lead_id,
            "created_at": self.created_at.isoformat(),
            "email": self.email,
            "company": self.company,
            "lead_score": self.lead_score,
            "lead_status": self.lead_status,
            "estimated_value": self.estimated_value,
            "actual_value": self.actual_value,
            "first_touch_page": self.first_touch_page,
            "last_touch_page": self.last_touch_page,
            "touchpoint_count": self.touchpoint_count
        }



from sqlalchemy.orm import Session
from src.models.conversion import ConversionEventModel, LeadModel, ConversionEventType as DBEventType
import json
import uuid

class ConversionTracker:
    """
    Conversion Tracking System (DB Backed)
    """
    
    def __init__(self, db: Session = None):
        # We allow passing db explicitly, or we might need to get it per method in async context
        # For this refactor, we will assume the caller passes the session or we use a context manager
        pass
    
    def track_event(self, event: ConversionEvent, db: Session):
        """Track a conversion event to DB"""
        
        # Convert Enum to string for DB if needed, or rely on handling
        db_event = ConversionEventModel(
            event_id=event.event_id,
            event_type=event.event_type.value,
            user_id=event.user_id,
            session_id=event.session_id,
            page_url=event.page_url,
            page_id=event.page_id,
            topic_id=event.topic_id,
            template_id=event.template_id,
            timestamp=event.timestamp,
            conversion_value=event.conversion_value,
            referrer=event.referrer,
            utm_source=event.utm_source,
            utm_medium=event.utm_medium,
            utm_campaign=event.utm_campaign,
            # lead_id is not directly on event model yet, but could be added
        )
        
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        
        logger.info(f"Event tracked (DB): {event.event_type.value} on {event.page_url}")
    
    def create_lead(
        self,
        lead_id: str,
        session_id: str,
        db: Session,
        email: Optional[str] = None,
        company: Optional[str] = None
    ) -> Lead:
        """Create a new lead from session history"""
        
        # Reconstruct journey from DB
        journey_events = db.query(ConversionEventModel).filter(
            ConversionEventModel.session_id == session_id
        ).order_by(ConversionEventModel.timestamp).all()
        
        if not journey_events:
            logger.warning(f"No journey found for session: {session_id}")
        
        first_touch = journey_events[0] if journey_events else None
        last_touch = journey_events[-1] if journey_events else None
        
        db_lead = LeadModel(
            lead_id=lead_id,
            created_at=datetime.now(),
            email=email,
            company=company,
            first_touch_page=first_touch.page_url if first_touch else None,
            last_touch_page=last_touch.page_url if last_touch else None,
            touchpoint_count=len(journey_events),
            lead_status="new",
            lead_score=0
        )
        
        db.add(db_lead)
        db.commit()
        
        logger.info(f"Lead created (DB): {lead_id} from {len(journey_events)} touchpoints")
        
        # Return domain object (simplified)
        return Lead(
            lead_id=lead_id,
            created_at=db_lead.created_at,
            email=email,
            company=company,
            first_touch_page=db_lead.first_touch_page,
            last_touch_page=db_lead.last_touch_page,
            touchpoint_count=db_lead.touchpoint_count
        )
    def update_lead_status(
        self,
        lead_id: str,
        status: str,
        db: Session,
        actual_value: Optional[float] = None
    ):
        """Update lead status and value"""
        db_lead = db.query(LeadModel).filter(LeadModel.lead_id == lead_id).first()
        
        if not db_lead:
            logger.warning(f"Lead not found: {lead_id}")
            return
        
        db_lead.lead_status = status
        
        if actual_value is not None:
            db_lead.actual_value = actual_value
            
        db.commit()
        
        logger.info(f"Lead {lead_id} updated (DB): {status}")
        """Get user journey for a session"""
        events = db.query(ConversionEventModel).filter(
            ConversionEventModel.session_id == session_id
        ).order_by(ConversionEventModel.timestamp).all()
        
        # Convert back to domain objects
        return [
            ConversionEvent(
                event_id=e.event_id,
                event_type=ConversionEventType(e.event_type),
                user_id=e.user_id,
                session_id=e.session_id,
                page_url=e.page_url,
                timestamp=e.timestamp,
                conversion_value=e.conversion_value
            ) for e in events
        ]



class AttributionEngine:
    """
    Multi-Touch Attribution Engine
    
    Calculates attribution credit for each touchpoint in user journey
    """
    
    def calculate_attribution(
        self,
        journey: List[ConversionEvent],
        conversion_value: float,
        model: AttributionModel = AttributionModel.LINEAR
    ) -> Dict[str, float]:
        """
        Calculate attribution for each page in journey
        
        Returns: {page_url: attributed_value}
        """
        if not journey:
            return {}
        
        if model == AttributionModel.FIRST_TOUCH:
            return self._first_touch(journey, conversion_value)
        elif model == AttributionModel.LAST_TOUCH:
            return self._last_touch(journey, conversion_value)
        elif model == AttributionModel.LINEAR:
            return self._linear(journey, conversion_value)
        elif model == AttributionModel.TIME_DECAY:
            return self._time_decay(journey, conversion_value)
        elif model == AttributionModel.POSITION_BASED:
            return self._position_based(journey, conversion_value)
        
        return {}
    
    def _first_touch(
        self,
        journey: List[ConversionEvent],
        value: float
    ) -> Dict[str, float]:
        """100% credit to first touchpoint"""
        first_page = journey[0].page_url
        return {first_page: value}
    
    def _last_touch(
        self,
        journey: List[ConversionEvent],
        value: float
    ) -> Dict[str, float]:
        """100% credit to last touchpoint"""
        last_page = journey[-1].page_url
        return {last_page: value}
    
    def _linear(
        self,
        journey: List[ConversionEvent],
        value: float
    ) -> Dict[str, float]:
        """Equal credit to all touchpoints"""
        credit_per_page = value / len(journey)
        attribution = {}
        
        for event in journey:
            page = event.page_url
            attribution[page] = attribution.get(page, 0) + credit_per_page
        
        return attribution
    
    def _time_decay(
        self,
        journey: List[ConversionEvent],
        value: float,
        half_life_days: float = 7.0
    ) -> Dict[str, float]:
        """More credit to recent touchpoints (exponential decay)"""
        import math
        
        last_timestamp = journey[-1].timestamp
        weights = []
        
        for event in journey:
            days_ago = (last_timestamp - event.timestamp).days
            weight = math.exp(-days_ago / half_life_days)
            weights.append(weight)
        
        total_weight = sum(weights)
        attribution = {}
        
        for event, weight in zip(journey, weights):
            page = event.page_url
            credit = (weight / total_weight) * value
            attribution[page] = attribution.get(page, 0) + credit
        
        return attribution
    
    def _position_based(
        self,
        journey: List[ConversionEvent],
        value: float
    ) -> Dict[str, float]:
        """40% first, 40% last, 20% middle"""
        attribution = {}
        
        if len(journey) == 1:
            attribution[journey[0].page_url] = value
        elif len(journey) == 2:
            attribution[journey[0].page_url] = value * 0.5
            attribution[journey[-1].page_url] = value * 0.5
        else:
            # 40% to first
            attribution[journey[0].page_url] = value * 0.4
            
            # 40% to last
            last_page = journey[-1].page_url
            attribution[last_page] = attribution.get(last_page, 0) + value * 0.4
            
            # 20% to middle (split equally)
            middle_credit = (value * 0.2) / (len(journey) - 2)
            for event in journey[1:-1]:
                page = event.page_url
                attribution[page] = attribution.get(page, 0) + middle_credit
        
        return attribution


class ROIAnalyzer:
    """
    ROI Analysis by Page/Topic/Template
    
    Calculates return on investment for content
    """
    
    def __init__(self, tracker: ConversionTracker, attribution_engine: AttributionEngine):
        self.tracker = tracker
        self.attribution = attribution_engine
    
    def calculate_page_roi(
        self,
        page_url: str,
        attribution_model: AttributionModel = AttributionModel.LINEAR,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """Calculate ROI for a specific page"""
        cutoff_date = datetime.now() - timedelta(days=time_period_days)
        
        # Get all conversions that involved this page
        total_revenue = 0.0
        conversion_count = 0
        
        for lead in self.tracker.leads.values():
            if lead.created_at < cutoff_date:
                continue
            
            if not lead.actual_value:
                continue
            
            # Get journey for this lead
            # (In production, would store lead -> session mapping)
            # Simplified: check if page is in first/last touch
            if page_url in [lead.first_touch_page, lead.last_touch_page]:
                # Get attribution credit
                # For demo, use simple attribution
                if attribution_model == AttributionModel.FIRST_TOUCH:
                    if page_url == lead.first_touch_page:
                        total_revenue += lead.actual_value
                        conversion_count += 1
                elif attribution_model == AttributionModel.LAST_TOUCH:
                    if page_url == lead.last_touch_page:
                        total_revenue += lead.actual_value
                        conversion_count += 1
                else:
                    # Linear: split equally
                    credit = lead.actual_value / lead.touchpoint_count
                    if page_url in [lead.first_touch_page, lead.last_touch_page]:
                        total_revenue += credit
                        conversion_count += 0.5
        
        # Calculate metrics
        # Cost would come from content creation cost
        # For demo, assume $50 per page
        content_cost = 50.0
        
        roi_percentage = ((total_revenue - content_cost) / content_cost * 100) if content_cost > 0 else 0
        
        return {
            "page_url": page_url,
            "time_period_days": time_period_days,
            "total_revenue": round(total_revenue, 2),
            "conversion_count": conversion_count,
            "content_cost": content_cost,
            "roi_percentage": round(roi_percentage, 2),
            "revenue_per_conversion": round(total_revenue / conversion_count, 2) if conversion_count > 0 else 0
        }
    
    def calculate_template_roi(
        self,
        template_id: str,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """Calculate ROI for all pages using a template"""
        # Get all events for this template
        template_events = [
            e for e in self.tracker.events
            if e.template_id == template_id
            and e.timestamp >= datetime.now() - timedelta(days=time_period_days)
        ]
        
        # Calculate aggregate metrics
        total_revenue = 0.0
        conversion_count = 0
        unique_pages = set(e.page_url for e in template_events)
        
        # Simplified calculation
        # In production, would properly attribute across all pages
        
        return {
            "template_id": template_id,
            "time_period_days": time_period_days,
            "pages_using_template": len(unique_pages),
            "total_revenue": round(total_revenue, 2),
            "conversion_count": conversion_count,
            "avg_revenue_per_page": round(total_revenue / len(unique_pages), 2) if unique_pages else 0
        }
