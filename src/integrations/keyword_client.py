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
import base64
import time
from typing import List, Optional, Dict, Any
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

# Simple in-memory cache with TTL (defined after KeywordOpportunity to avoid forward reference)
_cache: Dict[str, tuple[Any, float]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes

class KeywordClient:
    """
    Client for External Keyword Research API
    """
    
    def __init__(self, provider: str = "generic", api_key: Optional[str] = None, api_username: Optional[str] = None, base_url: Optional[str] = None):
        self.provider = provider or settings.keyword_api_provider
        self.api_key = api_key or settings.keyword_api_key
        self.api_username = api_username or settings.keyword_api_username
        self.base_url = base_url or settings.keyword_api_base_url
        
        if not self.api_key:
            logger.warning("Keyword API Key/Password not configured")

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
        """
        Fetch keyword data from DataForSEO API.
        Uses HTTP Basic Auth with base64 encoded username:password.
        """
        if not self.api_key or not self.api_username:
            logger.warning("DataForSEO credentials not configured (api_username and api_key required)")
            return []
        
        # Check cache first
        cache_key = f"{seed}:{limit}"
        if cache_key in _cache:
            cached_result, timestamp = _cache[cache_key]
            if time.time() - timestamp < _CACHE_TTL_SECONDS:
                logger.debug(f"Returning cached results for '{seed}'")
                return cached_result
            else:
                # Cache expired
                del _cache[cache_key]
        
        try:
            base_url = self.base_url or "https://api.dataforseo.com"
            
            # Create HTTP Basic Auth header
            credentials = f"{self.api_username}:{self.api_key}"
            auth_header = base64.b64encode(credentials.encode()).decode()
            
            async with httpx.AsyncClient() as client:
                all_results: List[KeywordOpportunity] = []
                
                # 1. Call keyword_suggestions endpoint
                try:
                    response = await client.post(
                        f"{base_url}/v3/dataforseo_labs/google/keyword_suggestions/live",
                        json=[{
                            "keyword": seed,
                            "limit": min(limit, 100)
                        }],
                        headers={"Authorization": f"Basic {auth_header}", "Content-Type": "application/json"},
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        tasks = data.get("tasks", [])
                        if tasks and len(tasks) > 0:
                            result = tasks[0].get("result", [])
                            if result and len(result) > 0:
                                items = result[0].get("items", [])
                                for item in items[:limit]:
                                    all_results.append(KeywordOpportunity(
                                        keyword=item.get("keyword", ""),
                                        volume=item.get("search_volume", 0),
                                        difficulty=item.get("competition_index", 50),
                                        cpc=item.get("cpc", 0.0),
                                        intent=self._map_dataforseo_intent(item.get("search_intent_info", {})),
                                        source="dataforseo_suggestions"
                                    ))
                    elif response.status_code == 401:
                        logger.error("DataForSEO authentication failed (401)")
                        return []
                    elif response.status_code == 429:
                        logger.warning("DataForSEO rate limit hit (429)")
                        return []
                    else:
                        logger.warning(f"DataForSEO suggestions endpoint returned {response.status_code}")
                        
                except httpx.TimeoutException:
                    logger.warning("DataForSEO suggestions request timed out")
                except Exception as e:
                    logger.error(f"Error fetching keyword suggestions: {e}")
                
                # 2. Call related_keywords endpoint if we need more results
                if len(all_results) < limit:
                    try:
                        response = await client.post(
                            f"{base_url}/v3/dataforseo_labs/google/related_keywords/live",
                            json=[{
                                "keyword": seed,
                                "limit": min(limit - len(all_results), 100)
                            }],
                            headers={"Authorization": f"Basic {auth_header}", "Content-Type": "application/json"},
                            timeout=30.0
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            tasks = data.get("tasks", [])
                            if tasks and len(tasks) > 0:
                                result = tasks[0].get("result", [])
                                if result and len(result) > 0:
                                    items = result[0].get("items", [])
                                    for item in items[:limit - len(all_results)]:
                                        all_results.append(KeywordOpportunity(
                                            keyword=item.get("keyword", ""),
                                            volume=item.get("search_volume", 0),
                                            difficulty=item.get("competition_index", 50),
                                            cpc=item.get("cpc", 0.0),
                                            intent=self._map_dataforseo_intent(item.get("search_intent_info", {})),
                                            source="dataforseo_related"
                                        ))
                    except httpx.TimeoutException:
                        logger.warning("DataForSEO related keywords request timed out")
                    except Exception as e:
                        logger.error(f"Error fetching related keywords: {e}")
                
                # 3. Get bulk difficulty for all keywords (optional enhancement)
                if all_results:
                    try:
                        keywords_for_difficulty = [{"keyword": k.keyword} for k in all_results[:100]]
                        response = await client.post(
                            f"{base_url}/v3/dataforseo_labs/google/bulk_keyword_difficulty/live",
                            json=keywords_for_difficulty,
                            headers={"Authorization": f"Basic {auth_header}", "Content-Type": "application/json"},
                            timeout=30.0
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            tasks = data.get("tasks", [])
                            if tasks and len(tasks) > 0:
                                result = tasks[0].get("result", [])
                                if result and len(result) > 0:
                                    items = result[0].get("items", [])
                                    # Update difficulty for matching keywords
                                    difficulty_map = {item.get("keyword", "").lower(): item.get("competition_index", 50) for item in items}
                                    for opp in all_results:
                                        if opp.keyword.lower() in difficulty_map:
                                            opp.difficulty = difficulty_map[opp.keyword.lower()]
                    except Exception as e:
                        logger.debug(f"Could not fetch bulk difficulty: {e}")
                
                # Store in cache
                _cache[cache_key] = (all_results, time.time())
                return all_results
                
        except httpx.TimeoutException:
            logger.error("DataForSEO request timed out")
            return []
        except Exception as e:
            logger.error(f"DataForSEO fetch failed: {e}")
            return []
    
    def _map_dataforseo_intent(self, intent_info: Dict[str, Any]) -> str:
        """Map DataForSEO intent info to our internal intent format."""
        intent = intent_info.get("main_intent", "informational")
        intent_map = {
            "informational": "informational",
            "navigational": "navigational",
            "commercial": "commercial",
            "transactional": "transactional"
        }
        return intent_map.get(intent.lower(), "informational")

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
