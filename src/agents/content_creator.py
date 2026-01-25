from typing import Dict, Any
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ContentCreatorAgent(BaseAgent):
    """
    Content Creator Agent - Acts as the Content Writer
    Creates SEO-optimized content
    """

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute content creation task"""
        task_type = task.get("type", "create_article")

        if task_type == "create_article":
            return await self._create_article(task)
        elif task_type == "optimize_content":
            return await self._optimize_content(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _create_article(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive SEO-optimized article"""
        keyword = task.get("keyword", "")
        products = task.get("products", [])

        prompt = f"""
        Write a comprehensive 2000+ word article optimized for: {keyword}

        Requirements:
        1. Engaging headline with keyword
        2. Clear H2/H3 structure
        3. Natural keyword integration (1-2% density)
        4. Actionable insights for wholesale buyers
        5. Internal links to products: {products}
        6. Meta description (150-160 chars)

        Write professional, valuable content.
        """

        content = await self.generate_text(prompt, max_tokens=3000)

        await self.publish_event("content_generated", {
            "keyword": keyword,
            "content_length": len(content)
        })

        return {"status": "success", "content": content}

    async def _optimize_content(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize existing content for SEO"""
        content = task.get("content", "")
        keyword = task.get("keyword", "")

        prompt = f"""
        Optimize this content for keyword: {keyword}

        Content: {content[:1000]}...

        Improve:
        1. Keyword placement
        2. Readability
        3. Internal linking opportunities
        4. Meta description

        Provide optimized version.
        """

        optimized = await self.generate_text(prompt)

        return {"status": "success", "optimized_content": optimized}
