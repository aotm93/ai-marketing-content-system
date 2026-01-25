from typing import Dict, Any, List
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class KeywordStrategistAgent(BaseAgent):
    """
    Keyword Strategist Agent - Acts as the SEO Specialist
    Discovers and prioritizes keywords
    """

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute keyword strategy task"""
        task_type = task.get("type", "discover_keywords")

        if task_type == "discover_keywords":
            return await self._discover_keywords(task)
        elif task_type == "prioritize_keywords":
            return await self._prioritize_keywords(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _discover_keywords(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Discover high-value keywords"""
        products = task.get("products", [])

        prompt = f"""
        Generate long-tail keywords for these products: {products}

        Focus on:
        1. Buyer intent keywords (wholesale, bulk, supplier)
        2. Question-based keywords
        3. 3-5+ word phrases
        4. Commercial intent

        Provide 20 high-value keywords.
        """

        keywords = await self.generate_text(prompt)

        await self.publish_event("keywords_discovered", {"keywords": keywords})

        return {"status": "success", "keywords": keywords}

    async def _prioritize_keywords(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Prioritize keywords based on traffic potential"""
        keywords = task.get("keywords", [])

        prompt = f"""
        Prioritize these keywords by traffic potential: {keywords}

        Consider:
        1. Search volume potential
        2. Competition level
        3. Buyer intent strength
        4. Relevance to products

        Rank them 1-10 and explain.
        """

        prioritized = await self.generate_text(prompt)

        return {"status": "success", "prioritized_keywords": prioritized}
