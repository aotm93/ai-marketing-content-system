"""
Email Subscriber Model

SQLAlchemy model for storing email subscribers.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from datetime import datetime
from typing import Dict, Any

from .base import Base, TimestampMixin


class EmailSubscriber(Base, TimestampMixin):
    """
    Email subscriber tracking
    
    Stores subscriber information for email marketing
    """
    __tablename__ = "email_subscribers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Subscriber info
    email = Column(String(255), nullable=False, unique=True, index=True)
    first_name = Column(String(255), nullable=True)
    source = Column(String(100), nullable=True)  # where they subscribed from
    
    # Subscription status
    subscribed_at = Column(DateTime, default=datetime.now)
    unsubscribed_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    
    __table_args__ = (
        Index('ix_email_subscriber_email', 'email'),
        Index('ix_email_subscriber_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<EmailSubscriber(email='{self.email}', active={self.is_active})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "source": self.source,
            "subscribed_at": self.subscribed_at.isoformat() if self.subscribed_at else None,
            "unsubscribed_at": self.unsubscribed_at.isoformat() if self.unsubscribed_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
