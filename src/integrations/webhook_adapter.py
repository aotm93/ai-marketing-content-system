"""
Webhook Adapter
Implements P1 (optional): Generic webhook integration for content publishing
Supports Shopify, Webflow, and custom endpoints.
"""

import logging
import aiohttp
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WebhookAdapter:
    """
    Generic Webhook Adapter for content publishing.
    Can be configured to push content to Zapier, Make, Shopify, etc.
    """
    
    def __init__(self, endpoint_url: str, auth_token: Optional[str] = None):
        self.endpoint_url = endpoint_url
        self.auth_token = auth_token
        
    async def publish_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Push content to the configured webhook
        
        Args:
            content_data: Dictionary containing title, content, meta, etc.
            
        Returns:
            Response dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SEO-Autopilot/WebhookAdapter"
        }
        
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
            
        # Payload standardization
        payload = {
            "event": "content_published",
            "timestamp": content_data.get("timestamp"),
            "data": content_data
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.endpoint_url, json=payload, headers=headers, timeout=30) as response:
                    response_text = await response.text()
                    
                    if response.status in [200, 201, 202]:
                        logger.info(f"Successfully pushed content to webhook: {self.endpoint_url}")
                        try:
                            return {"status": "success", "data": json.loads(response_text), "code": response.status}
                        except:
                            return {"status": "success", "data": response_text, "code": response.status}
                    else:
                        logger.error(f"Webhook push failed with status {response.status}: {response_text}")
                        return {"status": "error", "error": f"HTTP {response.status}", "details": response_text}
                        
        except Exception as e:
            logger.error(f"Webhook connection failed: {e}")
            return {"status": "error", "error": str(e)}

    async def verify_connection(self) -> bool:
        """Send a ping event to verify connection"""
        try:
            res = await self.publish_content({"type": "ping", "message": "Verify connection"})
            return res.get("status") == "success"
        except:
            return False
