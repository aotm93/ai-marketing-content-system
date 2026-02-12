"""
DataForSEO Backlinks API Client

Client for interacting with DataForSEO Backlinks API endpoints.
"""

import logging
import httpx
import base64
from typing import List, Dict, Any, Optional
from src.config import settings

logger = logging.getLogger(__name__)


class DataForSEOBacklinksClient:
    """
    Client for DataForSEO Backlinks API
    
    Provides methods to:
    - Get referring domains for a target
    - Get backlinks for a domain
    - Check if a backlink exists
    """
    
    def __init__(self, api_key: Optional[str] = None, api_username: Optional[str] = None):
        self.api_key = api_key or settings.keyword_api_key
        self.api_username = api_username or settings.keyword_api_username
        self.base_url = "https://api.dataforseo.com"
        
        if not self.api_key or not self.api_username:
            logger.warning("DataForSEO Backlinks API credentials not configured")
    
    def _get_auth_header(self) -> str:
        """Generate HTTP Basic Auth header."""
        credentials = f"{self.api_username}:{self.api_key}"
        return base64.b64encode(credentials.encode()).decode()
    
    async def get_referring_domains(
        self, 
        target_domain: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get referring domains for a target domain.
        
        Args:
            target_domain: Domain to analyze (e.g., "example.com")
            limit: Maximum number of results (default 100)
            
        Returns:
            List of domain data dictionaries
        """
        if not self.api_key or not self.api_username:
            logger.warning("DataForSEO credentials not configured")
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v3/backlinks/referring_domains/live",
                    json=[{
                        "target": target_domain,
                        "limit": min(limit, 1000)
                    }],
                    headers={
                        "Authorization": f"Basic {self._get_auth_header()}",
                        "Content-Type": "application/json"
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    tasks = data.get("tasks", [])
                    if tasks and len(tasks) > 0:
                        result = tasks[0].get("result", [])
                        if result and len(result) > 0:
                            items = result[0].get("items", [])
                            return items
                elif response.status_code == 401:
                    logger.error("DataForSEO authentication failed (401)")
                elif response.status_code == 429:
                    logger.warning("DataForSEO rate limit hit (429)")
                else:
                    logger.warning(f"DataForSEO referring domains returned {response.status_code}")
                    
        except httpx.TimeoutException:
            logger.error("DataForSEO referring domains request timed out")
        except Exception as e:
            logger.error(f"Error fetching referring domains: {e}")
        
        return []
    
    async def get_backlinks_for_domain(
        self, 
        target_domain: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get backlinks for a target domain.
        
        Args:
            target_domain: Domain to analyze (e.g., "example.com")
            limit: Maximum number of results (default 100)
            
        Returns:
            List of backlink data dictionaries
        """
        if not self.api_key or not self.api_username:
            logger.warning("DataForSEO credentials not configured")
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v3/backlinks/backlinks/live",
                    json=[{
                        "target": target_domain,
                        "limit": min(limit, 1000),
                        "include_subdomains": True
                    }],
                    headers={
                        "Authorization": f"Basic {self._get_auth_header()}",
                        "Content-Type": "application/json"
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    tasks = data.get("tasks", [])
                    if tasks and len(tasks) > 0:
                        result = tasks[0].get("result", [])
                        if result and len(result) > 0:
                            items = result[0].get("items", [])
                            return items
                elif response.status_code == 401:
                    logger.error("DataForSEO authentication failed (401)")
                elif response.status_code == 429:
                    logger.warning("DataForSEO rate limit hit (429)")
                else:
                    logger.warning(f"DataForSEO backlinks returned {response.status_code}")
                    
        except httpx.TimeoutException:
            logger.error("DataForSEO backlinks request timed out")
        except Exception as e:
            logger.error(f"Error fetching backlinks: {e}")
        
        return []
    
    async def check_backlink_exists(
        self, 
        source_url: str, 
        target_url: str
    ) -> bool:
        """
        Check if a backlink exists from source to target.
        
        Args:
            source_url: The URL that might link to target
            target_url: The URL being linked to
            
        Returns:
            True if backlink exists, False otherwise
        """
        if not self.api_key or not self.api_username:
            logger.warning("DataForSEO credentials not configured")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                # Use backlinks endpoint with source_url filter
                response = await client.post(
                    f"{self.base_url}/v3/backlinks/backlinks/live",
                    json=[{
                        "target": target_url,
                        "source": source_url,
                        "limit": 10
                    }],
                    headers={
                        "Authorization": f"Basic {self._get_auth_header()}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    tasks = data.get("tasks", [])
                    if tasks and len(tasks) > 0:
                        result = tasks[0].get("result", [])
                        if result and len(result) > 0:
                            items = result[0].get("items", [])
                            return len(items) > 0
                elif response.status_code == 401:
                    logger.error("DataForSEO authentication failed (401)")
                elif response.status_code == 429:
                    logger.warning("DataForSEO rate limit hit (429)")
                    
        except httpx.TimeoutException:
            logger.error("DataForSEO check backlink request timed out")
        except Exception as e:
            logger.error(f"Error checking backlink: {e}")
        
        return False
