"""
Email Sequence Engine

Handles email sequence enrollment, processing, and progress tracking.
Supports linear sequences only (no conditional branching).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from src.email.resend_client import ResendClient
from src.models.email import EmailSubscriber
from src.models.email_sequence import EmailSequence, EmailSequenceStep
from src.models.email_enrollment import EmailEnrollment, EnrollmentStatus

logger = logging.getLogger(__name__)


class SequenceEngine:
    """
    Email Sequence Engine
    
    Manages subscriber enrollment in email sequences and
    processes pending email sends based on timing rules.
    """
    
    def __init__(self, db: Session, resend_client: Optional[ResendClient] = None):
        self.db = db
        self.resend_client = resend_client or ResendClient()
    
    async def enroll(self, subscriber_id: int, sequence_id: int) -> Optional[EmailEnrollment]:
        """
        Enroll a subscriber in an email sequence.
        
        Args:
            subscriber_id: ID of the EmailSubscriber
            sequence_id: ID of the EmailSequence
            
        Returns:
            EmailEnrollment object or None if enrollment failed
        """
        try:
            # Verify subscriber exists and is active
            subscriber = self.db.query(EmailSubscriber).filter(
                EmailSubscriber.id == subscriber_id,
                EmailSubscriber.is_active == True
            ).first()
            
            if not subscriber:
                logger.warning(f"Subscriber {subscriber_id} not found or inactive")
                return None
            
            # Verify sequence exists and is active
            sequence = self.db.query(EmailSequence).filter(
                EmailSequence.id == sequence_id,
                EmailSequence.is_active == True
            ).first()
            
            if not sequence:
                logger.warning(f"Sequence {sequence_id} not found or inactive")
                return None
            
            # Check if already enrolled
            existing = self.db.query(EmailEnrollment).filter(
                EmailEnrollment.subscriber_id == subscriber_id,
                EmailEnrollment.sequence_id == sequence_id,
                EmailEnrollment.status == EnrollmentStatus.ACTIVE
            ).first()
            
            if existing:
                logger.info(f"Subscriber {subscriber_id} already enrolled in sequence {sequence_id}")
                return existing
            
            # Get first step to calculate next_step_due_at
            first_step = self.db.query(EmailSequenceStep).filter(
                EmailSequenceStep.sequence_id == sequence_id
            ).order_by(EmailSequenceStep.step_order).first()
            
            # Create enrollment
            enrollment = EmailEnrollment(
                subscriber_id=subscriber_id,
                sequence_id=sequence_id,
                current_step=0,  # Not started yet
                status=EnrollmentStatus.ACTIVE,
                enrolled_at=datetime.now(),
                last_step_sent_at=None,
                next_step_due_at=datetime.now() if first_step else None
            )
            
            self.db.add(enrollment)
            self.db.commit()
            self.db.refresh(enrollment)
            
            logger.info(f"Enrolled subscriber {subscriber_id} in sequence {sequence_id}")
            return enrollment
            
        except Exception as e:
            logger.error(f"Error enrolling subscriber: {e}")
            self.db.rollback()
            return None
    
    async def process_pending_steps(self) -> Dict[str, Any]:
        """
        Process all pending email sequence steps.
        Sends emails for enrollments where next_step_due_at <= now.
        
        Returns:
            Dict with processing statistics
        """
        stats = {
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "completed": 0,
            "errors": []
        }
        
        try:
            # Find all enrollments ready for next step
            now = datetime.now()
            pending_enrollments = self.db.query(EmailEnrollment).filter(
                EmailEnrollment.status == EnrollmentStatus.ACTIVE,
                EmailEnrollment.next_step_due_at <= now
            ).all()
            
            logger.info(f"Processing {len(pending_enrollments)} pending enrollments")
            
            for enrollment in pending_enrollments:
                try:
                    stats["processed"] += 1
                    
                    # Get next step
                    next_step = self.db.query(EmailSequenceStep).filter(
                        EmailSequenceStep.sequence_id == enrollment.sequence_id,
                        EmailSequenceStep.step_order == enrollment.current_step + 1
                    ).first()
                    
                    if not next_step:
                        # No more steps, mark as completed
                        enrollment.status = EnrollmentStatus.COMPLETED
                        enrollment.current_step = enrollment.current_step + 1
                        self.db.commit()
                        stats["completed"] += 1
                        logger.info(f"Completed sequence for enrollment {enrollment.id}")
                        continue
                    
                    # Send email
                    subscriber = enrollment.subscriber
                    if not subscriber or not subscriber.is_active:
                        # Subscriber unsubscribed, cancel enrollment
                        enrollment.status = EnrollmentStatus.CANCELLED
                        self.db.commit()
                        logger.info(f"Cancelled enrollment {enrollment.id} - subscriber inactive")
                        continue
                    
                    # Send the email
                    result = await self.resend_client.send_email(
                        to=subscriber.email,
                        subject=next_step.subject,
                        html_body=next_step.html_body
                    )
                    
                    if "error" in result:
                        stats["failed"] += 1
                        stats["errors"].append(f"Enrollment {enrollment.id}: {result['error']}")
                        logger.error(f"Failed to send email for enrollment {enrollment.id}: {result['error']}")
                        continue
                    
                    # Update enrollment
                    enrollment.current_step = next_step.step_order
                    enrollment.last_step_sent_at = now
                    
                    # Calculate next step due time
                    enrollment.next_step_due_at = now + timedelta(hours=next_step.delay_hours)
                    
                    self.db.commit()
                    stats["sent"] += 1
                    logger.info(f"Sent step {next_step.step_order} to {subscriber.email}")
                    
                except Exception as e:
                    stats["failed"] += 1
                    stats["errors"].append(f"Enrollment {enrollment.id}: {str(e)}")
                    logger.error(f"Error processing enrollment {enrollment.id}: {e}")
                    continue
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in process_pending_steps: {e}")
            stats["errors"].append(f"Global error: {str(e)}")
            return stats
    
    def get_progress(self, enrollment_id: int) -> Optional[Dict[str, Any]]:
        """
        Get progress information for an enrollment.
        
        Args:
            enrollment_id: ID of the EmailEnrollment
            
        Returns:
            Dict with progress information or None if not found
        """
        try:
            enrollment = self.db.query(EmailEnrollment).filter(
                EmailEnrollment.id == enrollment_id
            ).first()
            
            if not enrollment:
                return None
            
            # Get total steps in sequence
            total_steps = self.db.query(EmailSequenceStep).filter(
                EmailSequenceStep.sequence_id == enrollment.sequence_id
            ).count()
            
            # Get current step details
            current_step = None
            if enrollment.current_step > 0:
                step = self.db.query(EmailSequenceStep).filter(
                    EmailSequenceStep.sequence_id == enrollment.sequence_id,
                    EmailSequenceStep.step_order == enrollment.current_step
                ).first()
                if step:
                    current_step = {
                        "step_order": step.step_order,
                        "subject": step.subject,
                        "delay_hours": step.delay_hours
                    }
            
            return {
                "enrollment_id": enrollment.id,
                "subscriber_id": enrollment.subscriber_id,
                "subscriber_email": enrollment.subscriber.email if enrollment.subscriber else None,
                "sequence_id": enrollment.sequence_id,
                "sequence_name": enrollment.sequence.name if enrollment.sequence else None,
                "status": enrollment.status.value,
                "current_step": enrollment.current_step,
                "total_steps": total_steps,
                "progress_percent": round((enrollment.current_step / total_steps * 100), 1) if total_steps > 0 else 0,
                "current_step_details": current_step,
                "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
                "last_step_sent_at": enrollment.last_step_sent_at.isoformat() if enrollment.last_step_sent_at else None,
                "next_step_due_at": enrollment.next_step_due_at.isoformat() if enrollment.next_step_due_at else None
            }
            
        except Exception as e:
            logger.error(f"Error getting progress: {e}")
            return None
    
    async def cancel_enrollment(self, enrollment_id: int) -> bool:
        """
        Cancel an active enrollment.
        
        Args:
            enrollment_id: ID of the EmailEnrollment to cancel
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            enrollment = self.db.query(EmailEnrollment).filter(
                EmailEnrollment.id == enrollment_id,
                EmailEnrollment.status == EnrollmentStatus.ACTIVE
            ).first()
            
            if not enrollment:
                logger.warning(f"Active enrollment {enrollment_id} not found")
                return False
            
            enrollment.status = EnrollmentStatus.CANCELLED
            enrollment.next_step_due_at = None
            self.db.commit()
            
            logger.info(f"Cancelled enrollment {enrollment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling enrollment: {e}")
            self.db.rollback()
            return False
