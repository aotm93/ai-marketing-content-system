"""
Email Enrollment Model

SQLAlchemy model for tracking subscriber enrollment in email sequences.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional

from .base import Base, TimestampMixin


class EnrollmentStatus(str, Enum):
    """Status of email sequence enrollment"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EmailEnrollment(Base, TimestampMixin):
    """
    Email sequence enrollment tracking
    
    Tracks which subscribers are enrolled in which sequences
    and their progress through the sequence
    """
    __tablename__ = "email_enrollments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    subscriber_id = Column(Integer, ForeignKey('email_subscribers.id'), nullable=False)
    sequence_id = Column(Integer, ForeignKey('email_sequences.id'), nullable=False)
    
    # Progress tracking
    current_step = Column(Integer, default=0)  # 0 = not started, 1 = step 1, etc.
    status = Column(SQLEnum(EnrollmentStatus), default=EnrollmentStatus.ACTIVE)
    
    # Timing
    enrolled_at = Column(DateTime, default=datetime.now)
    last_step_sent_at = Column(DateTime, nullable=True)
    next_step_due_at = Column(DateTime, nullable=True)
    
    # Relationships
    subscriber = relationship("EmailSubscriber")
    sequence = relationship("EmailSequence")
    
    def __repr__(self):
        return f"<EmailEnrollment(subscriber_id={self.subscriber_id}, sequence_id={self.sequence_id}, status={self.status.value})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "subscriber_id": self.subscriber_id,
            "subscriber_email": self.subscriber.email if self.subscriber else None,
            "sequence_id": self.sequence_id,
            "sequence_name": self.sequence.name if self.sequence else None,
            "current_step": self.current_step,
            "status": self.status.value,
            "enrolled_at": self.enrolled_at.isoformat() if self.enrolled_at else None,
            "last_step_sent_at": self.last_step_sent_at.isoformat() if self.last_step_sent_at else None,
            "next_step_due_at": self.next_step_due_at.isoformat() if self.next_step_due_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
