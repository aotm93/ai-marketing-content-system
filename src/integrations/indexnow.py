"""
IndexNow API Client
Supports fast indexing notification to Bing, Yandex, IndexNow.org
"""
import httpx
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class IndexNowClient:
    """
    IndexNow API Client
    
    IndexNow is a protocol that allows site owners to instantly notify search engines
    about the latest content updates on their website.
    """
    
    # IndexNow Endpoints
    ENDPOINTS = [
        "https://www.bing.com/indexnow",
        "https://api.indexnow.org/indexnow",
        "https://yandex.com/indexnow"
    ]
    
    def __init__(self, api_key: str, host: str):
        """
        Initialize IndexNow Client
        
        Args:
            api_key: IndexNow API Key (string)
            host: Hostname (e.g. example.com)
        """
        self.api_key = api_key
        self.host = host
    
    async def submit_url(self, url: str) -> Dict[str, Any]:
        """Submit single URL"""
        return await self.submit_urls([url])
    
    async def submit_urls(self, urls: List[str]) -> Dict[str, Any]:
        """
        Submit multiple URLs
        """
        if not urls:
            return {"success": False, "error": "No URLs provided"}
        
        if len(urls) > 10000:
            return {"success": False, "error": "Too many URLs (max 10,000)"}
        
        payload = {
            "host": self.host,
            "key": self.api_key,
            "urlList": urls
        }
        
        results = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint in self.ENDPOINTS:
                try:
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers={"Content-Type": "application/json; charset=utf-8"}
                    )
                    
                    results.append({
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "success": response.status_code == 200,
                        "response": response.text if response.status_code != 200 else "OK"
                    })
                    
                    logger.info(f"IndexNow submitted to {endpoint}: {response.status_code}")
                    
                except Exception as e:
                    results.append({
                        "endpoint": endpoint,
                        "success": False,
                        "error": str(e)
                    })
                    logger.error(f"IndexNow submission failed for {endpoint}: {e}")
        
        success_count = sum(1 for r in results if r.get("success"))
        
        return {
            "success": success_count > 0,
            "submitted_urls": len(urls),
            "endpoints_succeeded": success_count,
            "endpoints_total": len(self.ENDPOINTS),
            "results": results
        }
    
    def generate_key_file_content(self) -> str:
        """Generate content for the API key text file"""
        return self.api_key
