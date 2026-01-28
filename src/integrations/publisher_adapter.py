"""
Publisher Adapter System
Implements multi-platform publishing abstraction (P0 - WordPress first, P1+ - other platforms)

Follows adapter pattern for extensibility to:
- WordPress (P0)
- Shopify (P1+)
- Webflow (P1+)
- Custom Webhook (P1+)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging

from .wordpress_client import WordPressClient, WordPressPost, PostStatus
from .rankmath_adapter import RankMathAdapter, SEOMeta

logger = logging.getLogger(__name__)


class PublishStatus(str, Enum):
    """Publishing status"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    SCHEDULED = "scheduled"


@dataclass
class PublishableContent:
    """
    Platform-agnostic content structure for publishing
    """
    title: str
    content: str
    excerpt: Optional[str] = None
    slug: Optional[str] = None
    status: str = "draft"  # draft, publish, scheduled
    
    # SEO meta
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    focus_keyword: Optional[str] = None
    
    # Taxonomy
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Media
    featured_image_url: Optional[str] = None
    featured_image_data: Optional[bytes] = None
    featured_image_alt: Optional[str] = None
    
    # Scheduling
    publish_date: Optional[str] = None  # ISO 8601 format
    
    # Internal tracking
    source_id: Optional[str] = None
    source_type: Optional[str] = None


@dataclass
class PublishResult:
    """Result of a publishing operation"""
    status: PublishStatus
    platform: str
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


class PublisherAdapter(ABC):
    """
    Abstract base class for all publisher adapters
    
    Each platform implementation must provide:
    - publish(): Create new content
    - update(): Update existing content
    - delete(): Remove content
    - health_check(): Verify connection
    """
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name"""
        pass
    
    @abstractmethod
    async def publish(self, content: PublishableContent) -> PublishResult:
        """
        Publish content to the platform
        
        Args:
            content: PublishableContent object
            
        Returns:
            PublishResult with status and details
        """
        pass
    
    @abstractmethod
    async def update(self, post_id: str, content: PublishableContent) -> PublishResult:
        """Update existing content"""
        pass
    
    @abstractmethod
    async def delete(self, post_id: str) -> PublishResult:
        """Delete content"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check platform connection health"""
        pass
    
    @abstractmethod
    async def set_seo_meta(self, post_id: str, seo: SEOMeta) -> PublishResult:
        """Set SEO metadata for a post"""
        pass


class WordPressAdapter(PublisherAdapter):
    """
    WordPress publishing adapter
    
    Implements full WordPress integration including:
    - Post creation/update/delete
    - Media upload
    - Category and tag management
    - Rank Math SEO integration
    """
    
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        seo_plugin: str = "rank_math"
    ):
        """
        Initialize WordPress adapter
        
        Args:
            base_url: WordPress site URL
            username: WordPress username
            password: Application password
            seo_plugin: SEO plugin to use (rank_math, yoast, aioseo)
        """
        self.wp_client = WordPressClient(base_url, username, password)
        self.seo_plugin = seo_plugin
        
        if seo_plugin == "rank_math":
            self.seo_adapter = RankMathAdapter(self.wp_client)
        else:
            # TODO: Add Yoast and AIOSEO adapters
            self.seo_adapter = None
            logger.warning(f"SEO plugin '{seo_plugin}' adapter not implemented yet")
        
        logger.info(f"WordPressAdapter initialized for {base_url}")
    
    @property
    def platform_name(self) -> str:
        return "wordpress"
    
    async def publish(self, content: PublishableContent) -> PublishResult:
        """
        Publish content to WordPress
        
        Steps:
        1. Handle featured image upload if provided
        2. Resolve categories and tags
        3. Create post
        4. Set SEO meta
        """
        try:
            logger.info(f"Publishing to WordPress: {content.title}")
            
            # Step 1: Handle featured image
            featured_media_id = None
            if content.featured_image_data:
                try:
                    filename = f"{content.slug or 'featured'}-image.jpg"
                    media_result = await self.wp_client.upload_media(
                        file_content=content.featured_image_data,
                        filename=filename,
                        alt_text=content.featured_image_alt or content.title
                    )
                    featured_media_id = media_result.get("id")
                    logger.info(f"Featured image uploaded: {featured_media_id}")
                except Exception as e:
                    logger.warning(f"Failed to upload featured image: {e}")
            
            # Step 2: Resolve taxonomy
            category_ids = []
            for cat_name in content.categories:
                cat_id = await self.wp_client.get_or_create_category(cat_name)
                category_ids.append(cat_id)
            
            tag_ids = []
            if content.tags:
                tag_ids = await self.wp_client.get_or_create_tags(content.tags)
            
            # Step 3: Create post
            status_map = {
                "draft": PostStatus.DRAFT,
                "publish": PostStatus.PUBLISH,
                "scheduled": PostStatus.FUTURE,
                "pending": PostStatus.PENDING
            }
            
            wp_post = WordPressPost(
                title=content.title,
                content=content.content,
                status=status_map.get(content.status, PostStatus.DRAFT),
                slug=content.slug,
                excerpt=content.excerpt,
                featured_media=featured_media_id,
                categories=category_ids if category_ids else None,
                tags=tag_ids if tag_ids else None,
                date=content.publish_date if content.status == "scheduled" else None
            )
            
            post_result = await self.wp_client.create_post(wp_post)
            post_id = post_result.get("id")
            post_url = post_result.get("link")
            
            logger.info(f"Post created: ID={post_id}, URL={post_url}")
            
            # Step 4: Set SEO meta
            if self.seo_adapter and (content.seo_title or content.seo_description or content.focus_keyword):
                seo_meta = SEOMeta(
                    title=content.seo_title or content.title,
                    description=content.seo_description or content.excerpt,
                    focus_keyword=content.focus_keyword
                )
                
                try:
                    await self.seo_adapter.set_seo_meta(post_id, seo_meta)
                    logger.info(f"SEO meta set for post {post_id}")
                except Exception as e:
                    logger.warning(f"Failed to set SEO meta: {e}")
            
            return PublishResult(
                status=PublishStatus.SUCCESS,
                platform=self.platform_name,
                post_id=str(post_id),
                post_url=post_url,
                message=f"Published successfully as {content.status}",
                meta={
                    "categories": category_ids,
                    "tags": tag_ids,
                    "featured_media": featured_media_id
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to publish to WordPress: {e}")
            return PublishResult(
                status=PublishStatus.FAILED,
                platform=self.platform_name,
                error=str(e),
                message="Publishing failed"
            )
    
    async def update(self, post_id: str, content: PublishableContent) -> PublishResult:
        """Update existing WordPress post"""
        try:
            update_data = {
                "title": content.title,
                "content": content.content,
            }
            
            if content.excerpt:
                update_data["excerpt"] = content.excerpt
            if content.slug:
                update_data["slug"] = content.slug
            
            result = await self.wp_client.update_post(int(post_id), update_data)
            
            # Update SEO if needed
            if self.seo_adapter and (content.seo_title or content.seo_description):
                seo_meta = SEOMeta(
                    title=content.seo_title,
                    description=content.seo_description,
                    focus_keyword=content.focus_keyword
                )
                await self.seo_adapter.set_seo_meta(int(post_id), seo_meta)
            
            return PublishResult(
                status=PublishStatus.SUCCESS,
                platform=self.platform_name,
                post_id=post_id,
                post_url=result.get("link"),
                message="Updated successfully"
            )
            
        except Exception as e:
            logger.error(f"Failed to update WordPress post: {e}")
            return PublishResult(
                status=PublishStatus.FAILED,
                platform=self.platform_name,
                post_id=post_id,
                error=str(e)
            )
    
    async def delete(self, post_id: str) -> PublishResult:
        """Delete WordPress post"""
        try:
            await self.wp_client.delete_post(int(post_id), force=True)
            return PublishResult(
                status=PublishStatus.SUCCESS,
                platform=self.platform_name,
                post_id=post_id,
                message="Deleted successfully"
            )
        except Exception as e:
            return PublishResult(
                status=PublishStatus.FAILED,
                platform=self.platform_name,
                post_id=post_id,
                error=str(e)
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check WordPress connection and capabilities"""
        wp_health = await self.wp_client.health_check()
        
        seo_health = None
        if self.seo_adapter:
            try:
                seo_health = await self.seo_adapter.self_check()
            except Exception as e:
                seo_health = {"status": "error", "error": str(e)}
        
        return {
            "platform": self.platform_name,
            "wordpress": wp_health,
            "seo_plugin": self.seo_plugin,
            "seo_status": seo_health
        }
    
    async def set_seo_meta(self, post_id: str, seo: SEOMeta) -> PublishResult:
        """Set SEO meta for a post"""
        if not self.seo_adapter:
            return PublishResult(
                status=PublishStatus.FAILED,
                platform=self.platform_name,
                post_id=post_id,
                error="SEO adapter not configured"
            )
        
        try:
            await self.seo_adapter.set_seo_meta(int(post_id), seo)
            return PublishResult(
                status=PublishStatus.SUCCESS,
                platform=self.platform_name,
                post_id=post_id,
                message="SEO meta updated"
            )
        except Exception as e:
            return PublishResult(
                status=PublishStatus.FAILED,
                platform=self.platform_name,
                post_id=post_id,
                error=str(e)
            )


class WebhookAdapter(PublisherAdapter):
    """
    Webhook-based publishing adapter (P1+)
    
    Sends content to external systems via HTTP webhook
    """
    
    def __init__(self, webhook_url: str, auth_header: Optional[str] = None):
        self.webhook_url = webhook_url
        self.auth_header = auth_header
        logger.info(f"WebhookAdapter initialized for {webhook_url}")
    
    @property
    def platform_name(self) -> str:
        return "webhook"
    
    async def publish(self, content: PublishableContent) -> PublishResult:
        """Send content to webhook"""
        # TODO: Implement in P1
        return PublishResult(
            status=PublishStatus.FAILED,
            platform=self.platform_name,
            error="WebhookAdapter not fully implemented yet"
        )
    
    async def update(self, post_id: str, content: PublishableContent) -> PublishResult:
        return PublishResult(
            status=PublishStatus.FAILED, 
            platform=self.platform_name,
            error="Not implemented"
        )
    
    async def delete(self, post_id: str) -> PublishResult:
        return PublishResult(
            status=PublishStatus.FAILED,
            platform=self.platform_name, 
            error="Not implemented"
        )
    
    async def health_check(self) -> Dict[str, Any]:
        return {"platform": self.platform_name, "status": "not_implemented"}
    
    async def set_seo_meta(self, post_id: str, seo: SEOMeta) -> PublishResult:
        return PublishResult(
            status=PublishStatus.FAILED,
            platform=self.platform_name,
            error="Not supported for webhooks"
        )


class PublisherFactory:
    """Factory for creating publisher adapters"""
    
    @staticmethod
    def create(platform: str, config: Dict[str, Any]) -> PublisherAdapter:
        """
        Create a publisher adapter for the specified platform
        
        Args:
            platform: Platform name (wordpress, webhook, shopify, etc.)
            config: Platform-specific configuration
            
        Returns:
            Configured PublisherAdapter instance
        """
        if platform == "wordpress":
            return WordPressAdapter(
                base_url=config["url"],
                username=config["username"],
                password=config["password"],
                seo_plugin=config.get("seo_plugin", "rank_math")
            )
        elif platform == "webhook":
            return WebhookAdapter(
                webhook_url=config["url"],
                auth_header=config.get("auth_header")
            )
        else:
            raise ValueError(f"Unsupported platform: {platform}")
