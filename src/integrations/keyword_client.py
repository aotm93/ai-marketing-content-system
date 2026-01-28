"""
Keyword Research API Client
Implements integration with external Keyword Data Providers (e.g., DataForSEO, SEMrush, Ahrefs mock)

Features:
- Fetch keyword metrics (Volume, KD, CPC)
- Generate related keywords from seed
- Filter for 'Goldilocks' keywords (High Volume, Low Difficulty)
"""

import logging
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from src.config import settings

logger = logging.getLogger(__name__)

@dataclass
class KeywordOpportunity:
    keyword: str
    volume: int
    difficulty: int
    cpc: float = 0.0
    intent: str = "informational"
    source: str = "api"

class KeywordClient:
    """
    Client for External Keyword Research API
    """
    
    def __init__(self, provider: str = "generic", api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.provider = provider or settings.keyword_api_provider
        self.api_key = api_key or settings.keyword_api_key
        self.base_url = base_url or settings.keyword_api_base_url
        
        if not self.api_key:
            logger.warning("Keyword API Key not configured")

    async def get_keyword_suggestions(self, seed_keyword: str, limit: int = 10) -> List[KeywordOpportunity]:
        """
        Get similar/related keywords with metrics
        """
        if not self.api_key:
            return []
            
        try:
            # Check which provider is configured. 
            # This is a generic implementation adaptable to DataForSEO or similar
            if self.provider == "dataforseo":
                return await self._fetch_dataforseo(seed_keyword, limit)
            else:
                # Default generic/mock implementation for now
                return await self._fetch_generic(seed_keyword, limit)
                
        except Exception as e:
            logger.error(f"Keyword API fetch failed: {e}")
            return []

    async def _fetch_generic(self, seed: str, limit: int) -> List[KeywordOpportunity]:
        """
        Generic implementation - likely what your backend uses if it's a proxy
        """
        if not self.base_url:
            return []
            
        async with httpx.AsyncClient() as client:
            # Assuming a standard /suggestions or /related endpoint
            response = await client.get(
                f"{self.base_url}/keywords/suggestions",
                params={"q": seed, "limit": limit},
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            data = response.json()
            
            results = []
            for item in data.get("data", []):
                results.append(KeywordOpportunity(
                    keyword=item.get("keyword"),
                    volume=item.get("volume", 0),
                    difficulty=item.get("difficulty", 50),
                    cpc=item.get("cpc", 0.0),
                    source="external_api"
                ))
            return results

    async def _fetch_dataforseo(self, seed: str, limit: int) -> List[KeywordOpportunity]:
        """Mock DataForSEO style implementation"""
        # ... logic specific to DataForSEO structure ...
        pass

    async def get_easy_wins(self, seed_keyword: str) -> List[KeywordOpportunity]:
        """
        Find High Volume, Low Keyword Difficulty opportunities
        """
        all_keywords = await self.get_keyword_suggestions(seed_keyword, limit=50)
        
        # Filter: Volume > 100, KD < 30
        easy_wins = [
            k for k in all_keywords 
            if k.volume >= 100 and k.difficulty <= 30
        ]
        
        # Sort by best ratio
        easy_wins.sort(key=lambda x: x.volume, reverse=True)
        return easy_wins[:10]
