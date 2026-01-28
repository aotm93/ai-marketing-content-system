"""
WordPress REST API Client
Implements P0-1, P0-2, P0-3: create_post, update_post, get_post, upload_media, taxonomy management
"""

import httpx
import base64
import logging
import mimetypes
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PostStatus(str, Enum):
    """WordPress post status options"""
    PUBLISH = "publish"
    DRAFT = "draft"
    PENDING = "pending"
    PRIVATE = "private"
    FUTURE = "future"  # For scheduled posts


@dataclass
class WordPressPost:
    """WordPress post data structure"""
    title: str
    content: str
    status: PostStatus = PostStatus.DRAFT
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    author: Optional[int] = None
    featured_media: Optional[int] = None
    categories: List[int] = field(default_factory=list)
    tags: List[int] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    date: Optional[str] = None  # ISO 8601 format for scheduled posts
    
    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to WordPress REST API format"""
        data = {
            "title": self.title,
            "content": self.content,
            "status": self.status.value,
        }
        
        if self.slug:
            data["slug"] = self.slug
        if self.excerpt:
            data["excerpt"] = self.excerpt
        if self.author:
            data["author"] = self.author
        if self.featured_media:
            data["featured_media"] = self.featured_media
        if self.categories:
            data["categories"] = self.categories
        if self.tags:
            data["tags"] = self.tags
        if self.meta:
            data["meta"] = self.meta
        if self.date:
            data["date"] = self.date
            
        return data


class WordPressClient:
    """
    WordPress REST API Client
    
    Supports:
    - Post CRUD operations (create, read, update, delete)
    - Media upload (images, documents)
    - Taxonomy management (categories, tags)
    - SEO meta integration
    """
    
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,  # Application password
        timeout: float = 30.0
    ):
        """
        Initialize WordPress client
        
        Args:
            base_url: WordPress site URL (e.g., https://example.com)
            username: WordPress username
            password: WordPress application password
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/wp-json/wp/v2"
        self.username = username
        self.password = password
        self.timeout = timeout
        
        # Create Basic Auth header
        auth_string = f"{username}:{password}"
        auth_bytes = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
        self.auth_header = f"Basic {auth_bytes}"
        
        logger.info(f"WordPress client initialized for {self.base_url}")
    
    def _get_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "Authorization": self.auth_header,
            "Content-Type": content_type,
            "Accept": "application/json",
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to WordPress API"""
        url = f"{self.api_url}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if files:
                    # For file uploads
                    headers = {"Authorization": self.auth_header}
                    response = await client.request(
                        method=method,
                        url=url,
                        files=files,
                        headers=headers,
                        params=params
                    )
                else:
                    response = await client.request(
                        method=method,
                        url=url,
                        json=data,
                        headers=self._get_headers(),
                        params=params
                    )
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                logger.error(f"WordPress API error: {e.response.status_code} - {e.response.text}")
                raise WordPressAPIError(
                    f"API request failed: {e.response.status_code}",
                    status_code=e.response.status_code,
                    response_body=e.response.text
                )
            except httpx.RequestError as e:
                logger.error(f"WordPress connection error: {e}")
                raise WordPressConnectionError(f"Connection failed: {e}")
    
    # ==================== Post Operations ====================
    
    async def create_post(self, post: WordPressPost) -> Dict[str, Any]:
        """
        Create a new WordPress post
        
        Args:
            post: WordPressPost object
            
        Returns:
            Created post data including ID and permalink
        """
        logger.info(f"Creating post: {post.title}")
        result = await self._request("POST", "posts", data=post.to_api_dict())
        logger.info(f"Post created with ID: {result.get('id')}")
        return result
    
    async def update_post(self, post_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing post
        
        Args:
            post_id: WordPress post ID
            data: Fields to update
            
        Returns:
            Updated post data
        """
        logger.info(f"Updating post ID: {post_id}")
        return await self._request("POST", f"posts/{post_id}", data=data)
    
    async def get_post(self, post_id: int) -> Dict[str, Any]:
        """Get a single post by ID"""
        return await self._request("GET", f"posts/{post_id}")
    
    async def get_posts(
        self,
        per_page: int = 10,
        page: int = 1,
        status: Optional[str] = None,
        search: Optional[str] = None,
        categories: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """Get a list of posts with pagination"""
        params = {"per_page": per_page, "page": page}
        if status:
            params["status"] = status
        if search:
            params["search"] = search
        if categories:
            # Join list into comma-separated string if API expects it, or pass as list
            # WP REST API expects 'categories' as comma-separated IDs usually for filter
            params["categories"] = ",".join(map(str, categories))
            
        return await self._request("GET", "posts", params=params)

    async def get_simple_posts_for_linking(self, limit: int = 20) -> List[Dict[str, str]]:
        """
        Get simplified list of recent posts for internal linking context.
        Returns minimal data: id, title, link/slug.
        """
        posts = await self.get_posts(per_page=limit, status="publish")
        return [
            {
                "id": p["id"],
                "title": p["title"]["rendered"],
                "slug": p["slug"],
                "link": p["link"]
            }
            for p in posts
        ]
    
    async def delete_post(self, post_id: int, force: bool = False) -> Dict[str, Any]:
        """Delete a post (move to trash or permanently delete)"""
        return await self._request("DELETE", f"posts/{post_id}", params={"force": force})
    
    # ==================== Media Operations ====================
    
    async def upload_media(
        self,
        file_content: bytes,
        filename: str,
        alt_text: Optional[str] = None,
        caption: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload media file to WordPress
        
        Args:
            file_content: Binary content of the file
            filename: Name of the file
            alt_text: Alternative text for accessibility
            caption: Media caption
            description: Media description
            
        Returns:
            Uploaded media data including ID and URL
        """
        logger.info(f"Uploading media: {filename}")
        
        # Detect MIME type
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        
        files = {
            "file": (filename, file_content, mime_type)
        }
        
        result = await self._request("POST", "media", files=files)
        media_id = result.get("id")
        
        # Update media metadata if provided
        if any([alt_text, caption, description]):
            meta_data = {}
            if alt_text:
                meta_data["alt_text"] = alt_text
            if caption:
                meta_data["caption"] = caption
            if description:
                meta_data["description"] = description
            await self._request("POST", f"media/{media_id}", data=meta_data)
        
        logger.info(f"Media uploaded with ID: {media_id}")
        return result
    
    async def get_media(self, media_id: int) -> Dict[str, Any]:
        """Get media item by ID"""
        return await self._request("GET", f"media/{media_id}")
    
    # ==================== Taxonomy Operations ====================
    
    async def get_categories(self, per_page: int = 100) -> List[Dict[str, Any]]:
        """Get all categories"""
        return await self._request("GET", "categories", params={"per_page": per_page})
    
    async def create_category(
        self,
        name: str,
        slug: Optional[str] = None,
        parent: Optional[int] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new category"""
        data = {"name": name}
        if slug:
            data["slug"] = slug
        if parent:
            data["parent"] = parent
        if description:
            data["description"] = description
        
        logger.info(f"Creating category: {name}")
        return await self._request("POST", "categories", data=data)
    
    async def get_or_create_category(self, name: str, **kwargs) -> int:
        """Get existing category ID or create new one"""
        categories = await self.get_categories()
        for cat in categories:
            if cat.get("name", "").lower() == name.lower():
                return cat["id"]
        
        result = await self.create_category(name, **kwargs)
        return result["id"]
    
    async def get_tags(self, per_page: int = 100) -> List[Dict[str, Any]]:
        """Get all tags"""
        return await self._request("GET", "tags", params={"per_page": per_page})
    
    async def create_tag(
        self,
        name: str,
        slug: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new tag"""
        data = {"name": name}
        if slug:
            data["slug"] = slug
        if description:
            data["description"] = description
        
        logger.info(f"Creating tag: {name}")
        return await self._request("POST", "tags", data=data)
    
    async def get_or_create_tag(self, name: str, **kwargs) -> int:
        """Get existing tag ID or create new one"""
        tags = await self.get_tags()
        for tag in tags:
            if tag.get("name", "").lower() == name.lower():
                return tag["id"]
        
        result = await self.create_tag(name, **kwargs)
        return result["id"]
    
    async def get_or_create_tags(self, tag_names: List[str]) -> List[int]:
        """Get or create multiple tags, return list of IDs"""
        tag_ids = []
        for name in tag_names:
            tag_id = await self.get_or_create_tag(name)
            tag_ids.append(tag_id)
        return tag_ids
    
    # ==================== Health Check ====================
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Test connection to WordPress site
        
        Returns:
            Site info and connection status
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test basic connectivity
                response = await client.get(
                    f"{self.base_url}/wp-json/",
                    headers={"Accept": "application/json"}
                )
                response.raise_for_status()
                site_info = response.json()
                
                # Test authentication
                auth_response = await client.get(
                    f"{self.api_url}/users/me",
                    headers=self._get_headers()
                )
                auth_response.raise_for_status()
                user_info = auth_response.json()
                
                return {
                    "status": "connected",
                    "site_name": site_info.get("name"),
                    "site_url": site_info.get("url"),
                    "authenticated_as": user_info.get("name"),
                    "user_id": user_info.get("id"),
                    "user_roles": user_info.get("roles", [])
                }
        except Exception as e:
            logger.error(f"WordPress health check failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


class WordPressAPIError(Exception):
    """WordPress API returned an error"""
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class WordPressConnectionError(Exception):
    """Failed to connect to WordPress"""
    pass
