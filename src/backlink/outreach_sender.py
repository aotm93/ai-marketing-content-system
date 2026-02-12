"""
Outreach Sender

Handles sending outreach emails for backlink opportunities.
Features:
- Admin approval required
- 50/day limit enforcement
- Status tracking
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.email.resend_client import ResendClient
from src.models.backlink import BacklinkOpportunityModel, OutreachStatus

logger = logging.getLogger(__name__)


class OutreachSender:
    """
    Outreach Email Sender
    
    Sends outreach emails for backlink opportunities with:
    - Daily limit enforcement (50/day)
    - Admin approval requirement
    - Status tracking
    """
    
    DAILY_LIMIT = 50
    
    def __init__(self, db: Session, resend_client: Optional[ResendClient] = None):
        self.db = db
        self.resend_client = resend_client or ResendClient()
    
    async def send_outreach(
        self, 
        opportunity_id: int, 
        email_content: str, 
        admin_approved: bool = False
    ) -> Dict[str, Any]:
        """
        Send outreach email for a specific opportunity.
        
        Args:
            opportunity_id: ID of the BacklinkOpportunityModel
            email_content: HTML/text content of the email
            admin_approved: Must be True to send (safety check)
            
        Returns:
            Dict with result status and message
        """
        # Check admin approval
        if not admin_approved:
            logger.warning(f"Outreach to opportunity {opportunity_id} blocked: admin approval required")
            return {
                "success": False,
                "error": "Admin approval required",
                "message": "This outreach email must be approved by an admin before sending"
            }
        
        # Check daily limit
        daily_count = self.get_daily_send_count()
        if daily_count >= self.DAILY_LIMIT:
            logger.warning(f"Daily outreach limit reached: {daily_count}/{self.DAILY_LIMIT}")
            return {
                "success": False,
                "error": "Daily limit reached",
                "message": f"Daily outreach limit of {self.DAILY_LIMIT} has been reached. Try again tomorrow.",
                "sent_today": daily_count
            }
        
        # Get opportunity
        opportunity = self.db.query(BacklinkOpportunityModel).filter(
            BacklinkOpportunityModel.id == opportunity_id
        ).first()
        
        if not opportunity:
            return {
                "success": False,
                "error": "Opportunity not found",
                "message": f"Opportunity with ID {opportunity_id} does not exist"
            }
        
        # Check if already sent
        if opportunity.outreach_status == OutreachStatus.SENT:
            return {
                "success": False,
                "error": "Already sent",
                "message": "Outreach has already been sent for this opportunity"
            }
        
        # Check if has contact email
        if not opportunity.contact_email:
            return {
                "success": False,
                "error": "No contact email",
                "message": "This opportunity does not have a contact email address"
            }
        
        try:
            # Send email
            result = await self.resend_client.send_email(
                to=opportunity.contact_email,
                subject=f"Question about your article on {opportunity.target_domain}",
                html_body=email_content
            )
            
            if "error" in result:
                logger.error(f"Failed to send outreach email: {result['error']}")
                return {
                    "success": False,
                    "error": "Send failed",
                    "message": f"Failed to send email: {result['error']}"
                }
            
            # Update opportunity status
            opportunity.outreach_status = OutreachStatus.SENT
            # Note: We're tracking sent_at in the notes field since the model doesn't have a sent_at column
            if opportunity.notes:
                opportunity.notes += f"\nEmail sent at {datetime.now().isoformat()}"
            else:
                opportunity.notes = f"Email sent at {datetime.now().isoformat()}"
            
            self.db.commit()
            
            logger.info(f"Outreach email sent to {opportunity.contact_email} for opportunity {opportunity_id}")
            
            return {
                "success": True,
                "message": "Outreach email sent successfully",
                "email_id": result.get("id"),
                "sent_to": opportunity.contact_email,
                "sent_today": daily_count + 1,
                "daily_limit": self.DAILY_LIMIT
            }
            
        except Exception as e:
            logger.error(f"Error sending outreach: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": "Exception",
                "message": f"Error sending outreach: {str(e)}"
            }
    
    def get_pending_outreach(self) -> List[Dict[str, Any]]:
        """
        Get list of opportunities with DRAFTED status (ready to send).
        
        Returns:
            List of opportunity dictionaries
        """
        try:
            opportunities = self.db.query(BacklinkOpportunityModel).filter(
                BacklinkOpportunityModel.outreach_status == OutreachStatus.DRAFTED,
                BacklinkOpportunityModel.contact_email.isnot(None)
            ).order_by(
                BacklinkOpportunityModel.relevance_score.desc()
            ).all()
            
            return [opp.to_dict() for opp in opportunities]
            
        except Exception as e:
            logger.error(f"Error fetching pending outreach: {e}")
            return []
    
    async def approve_and_send(
        self, 
        opportunity_id: int, 
        email_content: str
    ) -> Dict[str, Any]:
        """
        Approve and immediately send outreach email.
        This is the admin confirmation action.
        
        Args:
            opportunity_id: ID of the opportunity
            email_content: Email content to send
            
        Returns:
            Result dict from send_outreach
        """
        # First mark as drafted (if not already)
        opportunity = self.db.query(BacklinkOpportunityModel).filter(
            BacklinkOpportunityModel.id == opportunity_id
        ).first()
        
        if opportunity and opportunity.outreach_status == OutreachStatus.DISCOVERED:
            opportunity.outreach_status = OutreachStatus.DRAFTED
            self.db.commit()
        
        # Now send with admin_approved=True
        return await self.send_outreach(
            opportunity_id=opportunity_id,
            email_content=email_content,
            admin_approved=True
        )
    
    def get_daily_send_count(self) -> int:
        """
        Get count of outreach emails sent today.
        
        Returns:
            Number of emails sent today
        """
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Count opportunities marked as SENT today
            # We check the notes field for the sent timestamp
            count = self.db.query(BacklinkOpportunityModel).filter(
                BacklinkOpportunityModel.outreach_status == OutreachStatus.SENT,
                BacklinkOpportunityModel.notes.contains(today_start.strftime("%Y-%m-%d"))
            ).count()
            
            return count
            
        except Exception as e:
            logger.error(f"Error counting daily sends: {e}")
            return 0
    
    def get_outreach_stats(self) -> Dict[str, Any]:
        """
        Get outreach campaign statistics.
        
        Returns:
            Dict with statistics
        """
        try:
            total = self.db.query(BacklinkOpportunityModel).count()
            
            status_counts = {}
            for status in OutreachStatus:
                count = self.db.query(BacklinkOpportunityModel).filter(
                    BacklinkOpportunityModel.outreach_status == status
                ).count()
                status_counts[status.value] = count
            
            sent_today = self.get_daily_send_count()
            
            return {
                "total_opportunities": total,
                "status_breakdown": status_counts,
                "sent_today": sent_today,
                "daily_limit": self.DAILY_LIMIT,
                "remaining_today": max(0, self.DAILY_LIMIT - sent_today)
            }
            
        except Exception as e:
            logger.error(f"Error getting outreach stats: {e}")
            return {
                "error": str(e)
            }
