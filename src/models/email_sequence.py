"""
Email Sequence Models

SQLAlchemy models for email sequences and steps.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from typing import Dict, Any, List

from .base import Base, TimestampMixin


class EmailSequence(Base, TimestampMixin):
    """
    Email sequence definition
    
    A sequence is a series of automated emails sent over time
    """
    __tablename__ = "email_sequences"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Sequence info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    steps = relationship("EmailSequenceStep", back_populates="sequence", order_by="EmailSequenceStep.step_order")
    
    def __repr__(self):
        return f"<EmailSequence(name='{self.name}', active={self.is_active})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "steps": [step.to_dict() for step in self.steps],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EmailSequenceStep(Base, TimestampMixin):
    """
    Individual step in an email sequence
    
    Each step represents one email in the sequence
    """
    __tablename__ = "email_sequence_steps"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to sequence
    sequence_id = Column(Integer, ForeignKey('email_sequences.id'), nullable=False)
    
    # Step details
    step_order = Column(Integer, nullable=False)  # 1, 2, 3...
    subject = Column(String(500), nullable=False)
    html_body = Column(Text, nullable=False)
    delay_hours = Column(Integer, default=24)  # hours after previous step
    
    # Relationships
    sequence = relationship("EmailSequence", back_populates="steps")
    
    def __repr__(self):
        return f"<EmailSequenceStep(sequence_id={self.sequence_id}, order={self.step_order})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "sequence_id": self.sequence_id,
            "step_order": self.step_order,
            "subject": self.subject,
            "html_body": self.html_body,
            "delay_hours": self.delay_hours,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
