"""
Email API Router

Provides endpoints for email subscription management and sequence handling.
Public endpoints: subscribe, unsubscribe
Admin endpoints: subscribers, sequences, broadcast
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from src.core.auth import get_current_admin
from src.core.database import get_db
from src.email.resend_client import ResendClient
from src.email.sequence_engine import SequenceEngine
from src.models.email import EmailSubscriber
from src.models.email_sequence import EmailSequence, EmailSequenceStep
from src.models.email_enrollment import EmailEnrollment, EnrollmentStatus

router = APIRouter(prefix="/api/v1/email", tags=["email"])


# Pydantic models for request/response
class SubscribeRequest(BaseModel):
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    first_name: Optional[str] = None
    source: Optional[str] = None


class UnsubscribeRequest(BaseModel):
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


class CreateSequenceRequest(BaseModel):
    name: str
    description: Optional[str] = None


class CreateSequenceStepRequest(BaseModel):
    sequence_id: int
    step_order: int
    subject: str
    html_body: str
    delay_hours: int = 24


class BroadcastRequest(BaseModel):
    subject: str
    html_body: str
    from_email: Optional[str] = None


# ==================== PUBLIC ENDPOINTS (No Auth) ====================

@router.post("/subscribe")
async def subscribe(
    request: SubscribeRequest,
    db: Session = Depends(get_db)
):
    """
    Subscribe to email list.
    Public endpoint - no authentication required.
    """
    try:
        # Check if email already exists
        existing = db.query(EmailSubscriber).filter(
            EmailSubscriber.email == request.email
        ).first()
        
        if existing:
            if existing.is_active:
                return {"message": "Already subscribed", "subscriber_id": existing.id}
            else:
                # Reactivate
                existing.is_active = True
                existing.unsubscribed_at = None
                existing.first_name = request.first_name or existing.first_name
                existing.source = request.source or existing.source
                db.commit()
                return {"message": "Resubscribed successfully", "subscriber_id": existing.id}
        
        # Create new subscriber
        subscriber = EmailSubscriber(
            email=request.email,
            first_name=request.first_name,
            source=request.source
        )
        db.add(subscriber)
        db.commit()
        db.refresh(subscriber)
        
        return {
            "message": "Subscribed successfully",
            "subscriber_id": subscriber.id,
            "email": subscriber.email
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error subscribing: {str(e)}")


@router.post("/unsubscribe")
async def unsubscribe(
    request: UnsubscribeRequest,
    db: Session = Depends(get_db)
):
    """
    Unsubscribe from email list.
    Public endpoint - no authentication required.
    """
    try:
        subscriber = db.query(EmailSubscriber).filter(
            EmailSubscriber.email == request.email
        ).first()
        
        if not subscriber:
            raise HTTPException(status_code=404, detail="Email not found")
        
        if not subscriber.is_active:
            return {"message": "Already unsubscribed"}
        
        # Mark as inactive
        subscriber.is_active = False
        subscriber.unsubscribed_at = datetime.now()
        
        # Cancel any active enrollments
        from datetime import datetime
        enrollments = db.query(EmailEnrollment).filter(
            EmailEnrollment.subscriber_id == subscriber.id,
            EmailEnrollment.status == EnrollmentStatus.ACTIVE
        ).all()
        
        for enrollment in enrollments:
            enrollment.status = EnrollmentStatus.CANCELLED
        
        db.commit()
        
        return {"message": "Unsubscribed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error unsubscribing: {str(e)}")


# ==================== ADMIN ENDPOINTS (Requires Auth) ====================

@router.get("/subscribers")
def get_subscribers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(False),
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get list of email subscribers.
    Admin only.
    """
    try:
        query = db.query(EmailSubscriber)
        
        if active_only:
            query = query.filter(EmailSubscriber.is_active == True)
        
        total = query.count()
        subscribers = query.order_by(EmailSubscriber.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        
        return {
            "subscribers": [s.to_dict() for s in subscribers],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching subscribers: {str(e)}")


@router.get("/sequences")
def get_sequences(
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all email sequences.
    Admin only.
    """
    try:
        sequences = db.query(EmailSequence).all()
        return {
            "sequences": [s.to_dict() for s in sequences],
            "count": len(sequences)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sequences: {str(e)}")


@router.post("/sequences")
def create_sequence(
    request: CreateSequenceRequest,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new email sequence.
    Admin only.
    """
    try:
        sequence = EmailSequence(
            name=request.name,
            description=request.description,
            is_active=True
        )
        db.add(sequence)
        db.commit()
        db.refresh(sequence)
        
        return {
            "message": "Sequence created successfully",
            "sequence_id": sequence.id,
            "sequence": sequence.to_dict()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating sequence: {str(e)}")


@router.post("/sequences/steps")
def add_sequence_step(
    request: CreateSequenceStepRequest,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Add a step to an email sequence.
    Admin only.
    """
    try:
        # Verify sequence exists
        sequence = db.query(EmailSequence).filter(
            EmailSequence.id == request.sequence_id
        ).first()
        
        if not sequence:
            raise HTTPException(status_code=404, detail="Sequence not found")
        
        step = EmailSequenceStep(
            sequence_id=request.sequence_id,
            step_order=request.step_order,
            subject=request.subject,
            html_body=request.html_body,
            delay_hours=request.delay_hours
        )
        db.add(step)
        db.commit()
        db.refresh(step)
        
        return {
            "message": "Step added successfully",
            "step_id": step.id,
            "step": step.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding step: {str(e)}")


@router.post("/broadcast")
async def send_broadcast(
    request: BroadcastRequest,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Send broadcast email to all active subscribers.
    Admin only.
    """
    try:
        # Get all active subscribers
        subscribers = db.query(EmailSubscriber).filter(
            EmailSubscriber.is_active == True
        ).all()
        
        if not subscribers:
            return {"message": "No active subscribers to send to", "sent_count": 0}
        
        # Send emails
        resend = ResendClient()
        sent_count = 0
        failed_count = 0
        
        for subscriber in subscribers:
            result = await resend.send_email(
                to=subscriber.email,
                subject=request.subject,
                html_body=request.html_body,
                from_email=request.from_email
            )
            
            if "error" not in result:
                sent_count += 1
            else:
                failed_count += 1
        
        return {
            "message": "Broadcast completed",
            "total_subscribers": len(subscribers),
            "sent": sent_count,
            "failed": failed_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending broadcast: {str(e)}")


@router.post("/sequences/{sequence_id}/enroll/{subscriber_id}")
async def enroll_subscriber(
    sequence_id: int,
    subscriber_id: int,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Enroll a subscriber in a sequence.
    Admin only.
    """
    try:
        engine = SequenceEngine(db)
        enrollment = await engine.enroll(subscriber_id, sequence_id)
        
        if not enrollment:
            raise HTTPException(status_code=400, detail="Failed to enroll subscriber")
        
        return {
            "message": "Enrolled successfully",
            "enrollment_id": enrollment.id,
            "status": enrollment.status.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enrolling: {str(e)}")
