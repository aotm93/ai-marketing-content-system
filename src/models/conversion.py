
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON
from datetime import datetime
from .base import Base
import enum

class ConversionEventType(str, enum.Enum):
    PAGEVIEW = "pageview"
    CLICK = "click"
    FORM_SUBMIT = "form_submit"
    LEAD_CREATED = "lead_created"
    QUALIFIED_LEAD = "qualified_lead"
    OPPORTUNITY = "opportunity"
    WON = "won"
    LOST = "lost"

class ConversionEventModel(Base):
    __tablename__ = "conversion_events"

    event_id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False) # Store enum as string for simplicity
    
    # User Context
    user_id = Column(String, nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    
    # Page Context
    page_url = Column(String, nullable=False)
    page_id = Column(Integer, nullable=True)
    topic_id = Column(Integer, nullable=True)
    template_id = Column(String, nullable=True)
    
    # Value
    conversion_value = Column(Float, nullable=True)
    
    # Attribution Meta
    referrer = Column(String, nullable=True)
    utm_source = Column(String, nullable=True)
    utm_medium = Column(String, nullable=True)
    utm_campaign = Column(String, nullable=True)
    
    # CTA specifics
    variant_id = Column(String, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metadata_json = Column(JSON, nullable=True)

class LeadModel(Base):
    __tablename__ = "leads"

    lead_id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Contact Info
    email = Column(String, nullable=True, index=True)
    company = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    
    # Status & Score
    lead_score = Column(Integer, default=0)
    lead_status = Column(String, default="new")
    
    # Value
    estimated_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    
    # Attribution Snapshot
    first_touch_page = Column(String, nullable=True)
    last_touch_page = Column(String, nullable=True)
    touchpoint_count = Column(Integer, default=0)
