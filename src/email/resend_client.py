"""
Resend Email API Client

Client for sending emails via Resend API.
"""

import logging
import httpx
from typing import List, Dict, Any, Optional
from src.config import settings

logger = logging.getLogger(__name__)


class ResendClient:
    """
    Client for Resend Email API
    
    Provides methods to:
    - Send single emails
    - Send batch emails
    - Create contacts in audiences
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.resend_api_key
        self.base_url = "https://api.resend.com"
        self.from_email = settings.resend_from_email or "noreply@example.com"
        
        if not self.api_key:
            logger.warning("Resend API key not configured")
    
    async def send_email(
        self, 
        to: str, 
        subject: str, 
        html_body: str, 
        from_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a single email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            from_email: Sender email (defaults to settings.resend_from_email)
            
        Returns:
            API response dictionary with 'id' field on success
        """
        if not self.api_key:
            logger.error("Resend API key not configured")
            return {"error": "API key not configured"}
        
        sender = from_email or self.from_email
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/emails",
                    json={
                        "from": sender,
                        "to": [to],
                        "subject": subject,
                        "html": html_body
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Email sent successfully to {to}, id: {data.get('id')}")
                    return data
                elif response.status_code == 429:
                    logger.warning("Resend rate limit hit")
                    return {"error": "rate_limited"}
                else:
                    error_text = response.text
                    logger.error(f"Resend API error: {response.status_code} - {error_text}")
                    return {"error": f"API error: {response.status_code}"}
                    
        except httpx.TimeoutException:
            logger.error("Resend request timed out")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {"error": str(e)}
    
    async def send_batch(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send multiple emails in a batch.
        
        Args:
            emails: List of email dictionaries with keys:
                    - to: recipient email
                    - subject: email subject
                    - html: HTML body
                    - from: sender email (optional)
                    
        Returns:
            API response dictionary
        """
        if not self.api_key:
            logger.error("Resend API key not configured")
            return {"error": "API key not configured"}
        
        if not emails:
            return {"data": []}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/emails/batch",
                    json={"emails": emails},
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Batch email sent: {len(emails)} emails")
                    return data
                elif response.status_code == 429:
                    logger.warning("Resend rate limit hit")
                    return {"error": "rate_limited"}
                else:
                    error_text = response.text
                    logger.error(f"Resend batch API error: {response.status_code} - {error_text}")
                    return {"error": f"API error: {response.status_code}"}
                    
        except httpx.TimeoutException:
            logger.error("Resend batch request timed out")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"Error sending batch emails: {e}")
            return {"error": str(e)}
    
    async def create_contact(
        self, 
        email: str, 
        first_name: Optional[str] = None, 
        audience_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a contact in a Resend audience.
        
        Args:
            email: Contact email address
            first_name: Contact first name
            audience_id: Resend audience ID (required for contacts)
            
        Returns:
            API response dictionary
        """
        if not self.api_key:
            logger.error("Resend API key not configured")
            return {"error": "API key not configured"}
        
        if not audience_id:
            logger.warning("No audience_id provided for contact creation")
            return {"error": "audience_id required"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/audiences/{audience_id}/contacts",
                    json={
                        "email": email,
                        "first_name": first_name
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    logger.info(f"Contact created: {email}")
                    return data
                else:
                    error_text = response.text
                    logger.error(f"Resend contacts API error: {response.status_code} - {error_text}")
                    return {"error": f"API error: {response.status_code}"}
                    
        except httpx.TimeoutException:
            logger.error("Resend contacts request timed out")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            return {"error": str(e)}
