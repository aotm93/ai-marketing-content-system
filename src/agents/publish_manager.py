"""
Upgraded Publish Manager Agent
Uses the new WordPress integration (P0) for actual publishing

This agent coordinates the publishing workflow:
1. Prepare content for publishing
2. Upload media assets
3. Create/update WordPress post
4. Set SEO meta via Rank Math
5. Record in audit log
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from .base_agent import BaseAgent
from src.integrations import WordPressAdapter
from src.integrations.publisher_adapter import PublishableContent, PublishResult, PublishStatus
from src.integrations.rankmath_adapter import SEOMeta
from src.config import settings

logger = logging.getLogger(__name__)


class PublishManagerAgent(BaseAgent):
    """
    Publish Manager Agent - Acts as the Publishing Coordinator
    
    Upgraded for P0:
    - Uses WordPressAdapter for real REST API publishing
    - Integrates with Rank Math for SEO meta
    - Supports draft, scheduled, and direct publishing
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize WordPress adapter
        self._wp_adapter: Optional[WordPressAdapter] = None
        self._init_adapter()
    
    def _init_adapter(self):
        """Initialize WordPress adapter with settings"""
        try:
            self._wp_adapter = WordPressAdapter(
                base_url=settings.wordpress_url,
                username=settings.wordpress_username,
                password=settings.wordpress_password,
                seo_plugin=settings.seo_plugin
            )
            logger.info("WordPress adapter initialized")
        except Exception as e:
            logger.error(f"Failed to initialize WordPress adapter: {e}")
            self._wp_adapter = None
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute publishing task"""
        task_type = task.get("type", "publish_post")
        
        if task_type == "publish_post":
            return await self._publish_post(task)
        elif task_type == "schedule_post":
            return await self._schedule_post(task)
        elif task_type == "update_post":
            return await self._update_post(task)
        elif task_type == "set_seo":
            return await self._set_seo_meta(task)
        elif task_type == "health_check":
            return await self._health_check()
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _publish_post(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publish post to WordPress
        
        Task structure:
        {
            "type": "publish_post",
            "title": "Post Title",
            "content": "Post HTML content",
            "excerpt": "Optional excerpt",
            "categories": ["Category1", "Category2"],
            "tags": ["tag1", "tag2"],
            "seo_title": "SEO Title",
            "seo_description": "Meta description",
            "focus_keyword": "target keyword",
            "featured_image_data": bytes (optional),
            "status": "draft" | "publish" | "scheduled",
            "publish_date": "2026-01-27T10:00:00" (for scheduled)
        }
        """
        if not self._wp_adapter:
            self._init_adapter()
            if not self._wp_adapter:
                return {
                    "status": "error",
                    "error": "WordPress adapter not available. Check configuration."
                }
        
        # Build publishable content
        content = PublishableContent(
            title=task.get("title", "Untitled"),
            content=task.get("content", ""),
            excerpt=task.get("excerpt"),
            slug=task.get("slug"),
            status=task.get("status", settings.default_post_status),
            seo_title=task.get("seo_title"),
            seo_description=task.get("seo_description"),
            focus_keyword=task.get("focus_keyword"),
            categories=task.get("categories", []),
            tags=task.get("tags", []),
            featured_image_data=task.get("featured_image_data"),
            featured_image_alt=task.get("featured_image_alt"),
            publish_date=task.get("publish_date"),
            source_id=task.get("source_id"),
            source_type=task.get("source_type", "agent")
        )
        
        logger.info(f"Publishing post: {content.title}")
        
        try:
            result = await self._wp_adapter.publish(content)
            
            # Publish event
            await self.publish_event("content_published", {
                "title": content.title,
                "status": result.status.value,
                "post_id": result.post_id,
                "post_url": result.post_url
            })
            
            return {
                "status": result.status.value,
                "post_id": result.post_id,
                "url": result.post_url,
                "message": result.message,
                "meta": result.meta
            }
            
        except Exception as e:
            logger.error(f"Publishing failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _schedule_post(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule post for future publication"""
        task["status"] = "scheduled"
        
        if "publish_date" not in task:
            return {
                "status": "error",
                "error": "publish_date is required for scheduled posts"
            }
        
        return await self._publish_post(task)
    
    async def _update_post(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing post"""
        if not self._wp_adapter:
            return {"status": "error", "error": "WordPress adapter not available"}
        
        post_id = task.get("post_id")
        if not post_id:
            return {"status": "error", "error": "post_id is required"}
        
        content = PublishableContent(
            title=task.get("title", ""),
            content=task.get("content", ""),
            excerpt=task.get("excerpt"),
            seo_title=task.get("seo_title"),
            seo_description=task.get("seo_description"),
            focus_keyword=task.get("focus_keyword")
        )
        
        try:
            result = await self._wp_adapter.update(str(post_id), content)
            
            await self.publish_event("content_updated", {
                "post_id": post_id,
                "status": result.status.value
            })
            
            return {
                "status": result.status.value,
                "post_id": result.post_id,
                "url": result.post_url,
                "message": result.message
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _set_seo_meta(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Set SEO meta for an existing post"""
        if not self._wp_adapter:
            return {"status": "error", "error": "WordPress adapter not available"}
        
        post_id = task.get("post_id")
        if not post_id:
            return {"status": "error", "error": "post_id is required"}
        
        seo_meta = SEOMeta(
            title=task.get("seo_title"),
            description=task.get("seo_description"),
            focus_keyword=task.get("focus_keyword"),
            canonical_url=task.get("canonical_url"),
            og_title=task.get("og_title"),
            og_description=task.get("og_description")
        )
        
        try:
            result = await self._wp_adapter.set_seo_meta(str(post_id), seo_meta)
            return {
                "status": result.status.value,
                "post_id": result.post_id,
                "message": result.message
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _health_check(self) -> Dict[str, Any]:
        """Check WordPress connection and SEO integration"""
        if not self._wp_adapter:
            return {
                "status": "error",
                "wordpress": {"status": "not_configured"},
                "seo": {"status": "not_configured"}
            }
        
        try:
            health = await self._wp_adapter.health_check()
            return {
                "status": "success" if health.get("wordpress", {}).get("status") == "connected" else "warning",
                **health
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
