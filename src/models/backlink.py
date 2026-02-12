"""
Backlink Opportunity Model

SQLAlchemy model for storing backlink opportunities discovered via DataForSEO API.
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Index, Enum as SQLEnum
from datetime import datetime
from enum import Enum
from typing import Dict, Any

from .base import Base, TimestampMixin


class OpportunityType(str, Enum):
    """Types of backlink opportunities"""
    UNLINKED_MENTION = "unlinked_mention"
    RESOURCE_PAGE = "resource_page"
    BROKEN_LINK = "broken_link"
    COMPETITOR_BACKLINK = "competitor_backlink"
    GUEST_POST = "guest_post"


class OutreachStatus(str, Enum):
    """Outreach campaign status"""
    DISCOVERED = "discovered"
    DRAFTED = "drafted"
    SENT = "sent"
    REPLIED = "replied"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    NO_RESPONSE = "no_response"


class BacklinkOpportunityModel(Base, TimestampMixin):
    """
    Backlink opportunity tracking
    
    Stores opportunities discovered via DataForSEO backlink API
    """
    __tablename__ = "backlink_opportunities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Target information
    target_url = Column(String(1024), nullable=False)
    target_domain = Column(String(255), nullable=False, index=True)
    
    # Opportunity details
    opportunity_type = Column(SQLEnum(OpportunityType), nullable=False)
    domain_authority = Column(Integer, nullable=True)
    page_authority = Column(Integer, nullable=True)
    traffic_estimate = Column(Integer, nullable=True)
    relevance_score = Column(Float, default=0.0)
    
    # Contact information
    contact_email = Column(String(255), nullable=True)
    contact_name = Column(String(255), nullable=True)
    
    # Outreach status
    outreach_status = Column(SQLEnum(OutreachStatus), default=OutreachStatus.DISCOVERED)
    
    # Content details
    brand_mention = Column(String(1024), nullable=True)
    anchor_text_suggestion = Column(String(512), nullable=True)
    suggested_link_url = Column(String(1024), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Discovery tracking
    discovered_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('ix_backlink_target_domain', 'target_domain'),
        Index('ix_backlink_status', 'outreach_status'),
        Index('ix_backlink_relevance', 'relevance_score'),
        Index('ix_backlink_unique', 'target_url', 'opportunity_type', unique=True),
    )
    
    def __repr__(self):
        return f"<BacklinkOpportunity(url='{self.target_url[:50]}...', type={self.opportunity_type.value})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "target_url": self.target_url,
            "target_domain": self.target_domain,
            "opportunity_type": self.opportunity_type.value,
            "domain_authority": self.domain_authority,
            "page_authority": self.page_authority,
            "traffic_estimate": self.traffic_estimate,
            "relevance_score": round(self.relevance_score, 1) if self.relevance_score else 0.0,
            "contact_email": self.contact_email,
            "contact_name": self.contact_name,
            "outreach_status": self.outreach_status.value,
            "brand_mention": self.brand_mention,
            "anchor_text_suggestion": self.anchor_text_suggestion,
            "suggested_link_url": self.suggested_link_url,
            "notes": self.notes,
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
