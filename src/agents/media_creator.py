from typing import Dict, Any
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MediaCreatorAgent(BaseAgent):
    """
    Media Creator Agent - Acts as the Graphic Designer
    Creates visual content for articles
    """

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute media creation task"""
        task_type = task.get("type", "create_featured_image")

        if task_type == "create_featured_image":
            return await self._create_featured_image(task)
        elif task_type == "create_infographic":
            return await self._create_infographic(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _create_featured_image(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create featured image for article"""
        title = task.get("title", "")
        keyword = task.get("keyword", "")

        prompt = f"""
        Professional featured image for article: {title}
        Theme: {keyword}
        Style: Clean, modern, professional
        Focus: Bottle packaging, wholesale business
        """

        image_bytes = await self.ai_provider.generate_image(prompt)

        await self.publish_event("image_generated", {
            "title": title,
            "size": len(image_bytes)
        })

        return {"status": "success", "image": image_bytes}

    async def _create_infographic(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create infographic for article"""
        topic = task.get("topic", "")

        prompt = f"""
        Infographic about: {topic}
        Style: Professional, data-driven
        Include: Charts, icons, statistics
        Theme: Bottle packaging industry
        """

        image_bytes = await self.ai_provider.generate_image(prompt)

        return {"status": "success", "infographic": image_bytes}
