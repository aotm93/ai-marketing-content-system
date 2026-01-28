"""
Rank Math SEO Adapter
Implements P0-4, P0-5: SEO meta writing and self-check functionality

Rank Math stores SEO data in WordPress post meta:
- rank_math_title: SEO title
- rank_math_description: Meta description
- rank_math_focus_keyword: Primary focus keyword
- rank_math_robots: Robots meta (noindex, nofollow, etc.)
- rank_math_canonical_url: Canonical URL
- rank_math_primary_category: Primary category ID
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from .wordpress_client import WordPressClient, WordPressAPIError

logger = logging.getLogger(__name__)


@dataclass
class SEOMeta:
    """SEO metadata structure for Rank Math"""
    title: Optional[str] = None
    description: Optional[str] = None
    focus_keyword: Optional[str] = None
    secondary_keywords: List[str] = field(default_factory=list)
    canonical_url: Optional[str] = None
    robots: Optional[str] = None  # e.g., "noindex,nofollow"
    primary_category: Optional[int] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    twitter_title: Optional[str] = None
    twitter_description: Optional[str] = None
    
    def to_meta_dict(self) -> Dict[str, Any]:
        """Convert to WordPress meta format"""
        meta = {}
        
        if self.title:
            meta["rank_math_title"] = self.title
        if self.description:
            meta["rank_math_description"] = self.description
        if self.focus_keyword:
            meta["rank_math_focus_keyword"] = self.focus_keyword
        if self.secondary_keywords:
            # Rank Math stores secondary keywords as comma-separated
            meta["rank_math_focus_keyword"] = ",".join(
                [self.focus_keyword or ""] + self.secondary_keywords
            ).strip(",")
        if self.canonical_url:
            meta["rank_math_canonical_url"] = self.canonical_url
        if self.robots:
            meta["rank_math_robots"] = self.robots.split(",")
        if self.primary_category:
            meta["rank_math_primary_category"] = self.primary_category
        if self.og_title:
            meta["rank_math_facebook_title"] = self.og_title
        if self.og_description:
            meta["rank_math_facebook_description"] = self.og_description
        if self.twitter_title:
            meta["rank_math_twitter_title"] = self.twitter_title
        if self.twitter_description:
            meta["rank_math_twitter_description"] = self.twitter_description
            
        return meta


class RankMathAdapter:
    """
    Adapter for Rank Math SEO plugin integration
    
    Handles:
    - Writing SEO meta to posts
    - Reading existing SEO data
    - Self-check/verification
    - Best practices validation
    """
    
    # Rank Math meta key mappings
    META_KEYS = {
        "title": "rank_math_title",
        "description": "rank_math_description",
        "focus_keyword": "rank_math_focus_keyword",
        "canonical_url": "rank_math_canonical_url",
        "robots": "rank_math_robots",
        "primary_category": "rank_math_primary_category",
        "schema_type": "rank_math_schema_type",
        "og_title": "rank_math_facebook_title",
        "og_description": "rank_math_facebook_description",
        "og_image": "rank_math_facebook_image",
        "twitter_title": "rank_math_twitter_title",
        "twitter_description": "rank_math_twitter_description",
    }
    
    def __init__(self, wordpress_client: WordPressClient):
        """
        Initialize Rank Math adapter
        
        Args:
            wordpress_client: Configured WordPress client instance
        """
        self.wp_client = wordpress_client
        logger.info("RankMathAdapter initialized")
    
    async def set_seo_meta(self, post_id: int, seo_meta: SEOMeta) -> Dict[str, Any]:
        """
        Set SEO meta for a post
        
        Args:
            post_id: WordPress post ID
            seo_meta: SEOMeta object with SEO data
            
        Returns:
            Updated post data
        """
        meta = seo_meta.to_meta_dict()
        
        if not meta:
            logger.warning(f"No SEO meta to set for post {post_id}")
            return {"post_id": post_id, "meta_updated": False}
        
        logger.info(f"Setting SEO meta for post {post_id}: {list(meta.keys())}")
        
        try:
            result = await self.wp_client.update_post(post_id, {"meta": meta})
            return {
                "post_id": post_id,
                "meta_updated": True,
                "meta_keys": list(meta.keys()),
                "post_link": result.get("link")
            }
        except WordPressAPIError as e:
            logger.error(f"Failed to set SEO meta: {e}")
            raise SEOWriteError(f"Failed to write SEO meta: {e}")
    
    async def get_seo_meta(self, post_id: int) -> Dict[str, Any]:
        """
        Get SEO meta from a post
        
        Args:
            post_id: WordPress post ID
            
        Returns:
            Dictionary of SEO meta values
        """
        try:
            post = await self.wp_client.get_post(post_id)
            meta = post.get("meta", {})
            
            seo_data = {}
            for key, meta_key in self.META_KEYS.items():
                if meta_key in meta:
                    seo_data[key] = meta[meta_key]
            
            return seo_data
        except Exception as e:
            logger.error(f"Failed to get SEO meta: {e}")
            raise
    
    async def self_check(self, post_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform SEO integration self-check
        
        This implements P0-5: SEO self-check interface
        
        Tests:
        1. WordPress connection
        2. Authentication
        3. Meta writing capability
        4. Meta reading capability
        5. Rank Math detection
        
        Args:
            post_id: Optional post ID to test with (will create temp post if not provided)
            
        Returns:
            Diagnostic results with status and recommendations
        """
        results = {
            "status": "unknown",
            "checks": [],
            "recommendations": [],
            "rank_math_detected": False
        }
        
        # Check 1: WordPress connection
        try:
            health = await self.wp_client.health_check()
            if health.get("status") == "connected":
                results["checks"].append({
                    "name": "WordPress Connection",
                    "status": "pass",
                    "message": f"Connected to {health.get('site_name')}"
                })
            else:
                results["checks"].append({
                    "name": "WordPress Connection",
                    "status": "fail",
                    "message": health.get("error", "Connection failed")
                })
                results["status"] = "error"
                return results
        except Exception as e:
            results["checks"].append({
                "name": "WordPress Connection",
                "status": "fail",
                "message": str(e)
            })
            results["status"] = "error"
            return results
        
        # Check 2: Test post creation/meta writing
        test_post_id = post_id
        created_post = False
        
        try:
            if not test_post_id:
                # Create a test draft post
                from .wordpress_client import WordPressPost, PostStatus
                test_post = WordPressPost(
                    title="[SEO Self-Check Test] - Delete Me",
                    content="This is a test post for SEO integration verification.",
                    status=PostStatus.DRAFT
                )
                post_result = await self.wp_client.create_post(test_post)
                test_post_id = post_result["id"]
                created_post = True
                
                results["checks"].append({
                    "name": "Post Creation",
                    "status": "pass",
                    "message": f"Test post created with ID: {test_post_id}"
                })
        except Exception as e:
            results["checks"].append({
                "name": "Post Creation",
                "status": "fail",
                "message": str(e)
            })
            results["recommendations"].append(
                "Ensure the WordPress user has post creation permissions"
            )
        
        # Check 3: Write SEO meta
        if test_post_id:
            try:
                test_meta = SEOMeta(
                    title="Test SEO Title",
                    description="Test meta description for SEO verification",
                    focus_keyword="test keyword"
                )
                
                await self.set_seo_meta(test_post_id, test_meta)
                
                results["checks"].append({
                    "name": "SEO Meta Writing",
                    "status": "pass",
                    "message": "Successfully wrote SEO meta to post"
                })
            except Exception as e:
                results["checks"].append({
                    "name": "SEO Meta Writing",
                    "status": "fail",
                    "message": str(e)
                })
                results["recommendations"].append(
                    "Rank Math meta fields may not be exposed to REST API. "
                    "Consider installing the MU-plugin to register meta fields."
                )
        
        # Check 4: Read SEO meta back
        if test_post_id:
            try:
                read_meta = await self.get_seo_meta(test_post_id)
                
                if read_meta.get("title") == "Test SEO Title":
                    results["checks"].append({
                        "name": "SEO Meta Reading",
                        "status": "pass",
                        "message": "SEO meta verified successfully"
                    })
                    results["rank_math_detected"] = True
                else:
                    results["checks"].append({
                        "name": "SEO Meta Reading",
                        "status": "warning",
                        "message": "SEO meta written but not readable via REST API"
                    })
                    results["recommendations"].append(
                        "Meta fields are writable but not readable. "
                        "This may be a Rank Math REST API configuration issue."
                    )
            except Exception as e:
                results["checks"].append({
                    "name": "SEO Meta Reading",
                    "status": "fail",
                    "message": str(e)
                })
        
        # Cleanup: Delete test post if we created one
        if created_post and test_post_id:
            try:
                await self.wp_client.delete_post(test_post_id, force=True)
                results["checks"].append({
                    "name": "Cleanup",
                    "status": "pass",
                    "message": "Test post deleted"
                })
            except Exception as e:
                results["checks"].append({
                    "name": "Cleanup",
                    "status": "warning",
                    "message": f"Could not delete test post: {e}"
                })
        
        # Determine overall status
        failed_checks = [c for c in results["checks"] if c["status"] == "fail"]
        warning_checks = [c for c in results["checks"] if c["status"] == "warning"]
        
        if failed_checks:
            results["status"] = "error"
        elif warning_checks:
            results["status"] = "warning"
        else:
            results["status"] = "success"
        
        # Add general recommendations
        if not results["rank_math_detected"]:
            results["recommendations"].append(
                "Rank Math SEO plugin may not be properly configured. "
                "Ensure Rank Math is installed and activated."
            )
        
        return results
    
    def generate_seo_recommendations(
        self,
        title: str,
        content: str,
        focus_keyword: str
    ) -> Dict[str, Any]:
        """
        Generate SEO recommendations for content
        
        Args:
            title: Post title
            content: Post content
            focus_keyword: Target keyword
            
        Returns:
            Recommendations and scores
        """
        recommendations = []
        scores = {}
        
        # Title checks
        title_length = len(title)
        if title_length < 30:
            recommendations.append("Title is too short. Aim for 50-60 characters.")
            scores["title"] = 40
        elif title_length > 60:
            recommendations.append("Title is too long. Keep it under 60 characters.")
            scores["title"] = 60
        else:
            scores["title"] = 100
        
        # Keyword in title
        if focus_keyword.lower() not in title.lower():
            recommendations.append("Consider including the focus keyword in the title.")
            scores["keyword_in_title"] = 0
        else:
            scores["keyword_in_title"] = 100
        
        # Content length
        word_count = len(content.split())
        if word_count < 300:
            recommendations.append("Content is too short. Aim for at least 300 words.")
            scores["content_length"] = 30
        elif word_count < 1000:
            scores["content_length"] = 70
        else:
            scores["content_length"] = 100
        
        # Keyword density
        keyword_count = content.lower().count(focus_keyword.lower())
        density = (keyword_count / word_count * 100) if word_count > 0 else 0
        
        if density < 0.5:
            recommendations.append("Keyword density is too low. Use the keyword more frequently.")
            scores["keyword_density"] = 40
        elif density > 3:
            recommendations.append("Keyword density is too high. Reduce keyword usage to avoid over-optimization.")
            scores["keyword_density"] = 50
        else:
            scores["keyword_density"] = 100
        
        # Calculate overall score
        overall_score = sum(scores.values()) / len(scores) if scores else 0
        
        return {
            "overall_score": round(overall_score, 1),
            "individual_scores": scores,
            "recommendations": recommendations,
            "word_count": word_count,
            "keyword_density": round(density, 2)
        }


class SEOWriteError(Exception):
    """Failed to write SEO meta"""
    pass


class SEOReadError(Exception):
    """Failed to read SEO meta"""
    pass
