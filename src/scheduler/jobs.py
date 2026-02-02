"""
Content Generation Jobs
Implements the actual content generation workflow for Autopilot

This module defines the job functions that are registered with AutopilotScheduler
and executed by JobRunner.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from src.config import settings
from src.integrations import WordPressAdapter
from src.integrations.publisher_adapter import PublishableContent, PublishStatus

logger = logging.getLogger(__name__)

# Global cache for website analysis
_website_profile_cache = {
    "profile": None,
    "timestamp": None,
    "default_cache_duration": 604800  # 7 days in seconds (default)
}


def get_website_analysis_cache_duration() -> int:
    """
    Get website analysis cache duration from database config
    Returns duration in seconds (default: 7 days)
    """
    try:
        from src.models.config import SystemConfig
        from src.core.database import get_db

        db = next(get_db())
        config = db.query(SystemConfig).filter(
            SystemConfig.key == "website_analysis_cache_days"
        ).first()

        if config and config.value:
            days = int(config.value)
            return days * 86400  # Convert days to seconds

    except Exception as e:
        logger.debug(f"Failed to read cache config from DB: {e}")

    # Return default: 7 days
    return _website_profile_cache["default_cache_duration"]


async def analyze_website_now():
    """
    Perform website analysis immediately and update cache

    Returns:
        WebsiteProfile or None if analysis fails
    """
    global _website_profile_cache

    try:
        from src.services.website_analyzer import WebsiteAnalyzer
        from src.integrations.wordpress_client import WordPressClient

        logger.info("Starting website analysis...")

        wp_client = WordPressClient(
            base_url=settings.wordpress_url,
            username=settings.wordpress_username,
            password=settings.wordpress_password
        )

        analyzer = WebsiteAnalyzer(wp_client)
        profile = await analyzer.analyze_website(max_posts=30)

        # Update cache
        _website_profile_cache["profile"] = profile
        _website_profile_cache["timestamp"] = datetime.now()

        logger.info(f"✅ Website analysis complete: {len(profile.product_categories)} categories, "
                   f"Business: {profile.business_type}, "
                   f"Target: {profile.target_audience}")
        return profile

    except Exception as e:
        logger.error(f"❌ Website analysis failed: {e}")
        return None


async def get_cached_website_profile():
    """
    Get cached website profile or analyze if cache expired
    Returns None if analysis fails
    """
    global _website_profile_cache

    # Get cache duration from database config
    cache_duration = get_website_analysis_cache_duration()

    # Check if cache is valid
    if _website_profile_cache["profile"] is not None and _website_profile_cache["timestamp"] is not None:
        cache_age = (datetime.now() - _website_profile_cache["timestamp"]).total_seconds()
        if cache_age < cache_duration:
            cache_days = cache_age / 86400
            logger.info(f"Using cached website profile (age: {cache_days:.1f} days, expires in {(cache_duration - cache_age) / 86400:.1f} days)")
            return _website_profile_cache["profile"]

    # Cache expired or not available, trigger analysis
    logger.info("Cache expired or empty, triggering website analysis...")
    return await analyze_website_now()


async def content_generation_job(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main content generation job (Advanced SEO Implementation)
    
    Strategy Layers:
    1. Opportunity Discovery: GSC > Keyword API > Static Fallback
    2. Semantic Context: Fetch related LSI keywords
    3. Internal Linking: Fetch existing posts context
    4. Expert Content Creation: E-E-A-T focused generation with tables/schema
    5. Publishing: Optimized meta & structure
    """
    logger.info("Starting ADVANCED SEO content generation job")
    
    config = data.get("config", {})
    # Handle config object
    if hasattr(config, "to_dict"):
        config_dict = config.__dict__
    else:
        config_dict = config if isinstance(config, dict) else {}

    auto_publish = config_dict.get("auto_publish", False)
    
    result = {
        "job_type": "content_generation",
        "started_at": datetime.now().isoformat(),
        "steps": []
    }
    
    try:
        # --- Layer 1: Opportunity Discovery (with deduplication) ---
        target_keyword = None
        target_context = {}
        keyword_record = None

        # Get already used keywords from database
        from src.models.keyword import Keyword, KeywordStatus
        from src.core.database import get_db
        from datetime import timedelta

        db = next(get_db())

        # Initialize website_profile at function scope
        website_profile = None

        # All used keywords (for deduplication)
        used_keywords = db.query(Keyword.keyword).filter(
            Keyword.status.in_([KeywordStatus.IN_PROGRESS, KeywordStatus.PUBLISHED])
        ).all()
        used_keyword_set = {kw[0].lower() for kw in used_keywords}

        # Keywords used today (for semantic diversity check)
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_keywords = db.query(Keyword.keyword).filter(
            Keyword.status.in_([KeywordStatus.IN_PROGRESS, KeywordStatus.PUBLISHED]),
            Keyword.created_at >= today_start
        ).all()
        today_keyword_list = [kw[0] for kw in today_keywords]

        logger.info(f"Found {len(used_keyword_set)} total used keywords, {len(today_keyword_list)} used today")

        # 1.1 Try GSC (Optimization)
        try:
            from src.integrations.gsc_client import GSCClient
            if settings.gsc_site_url and settings.gsc_credentials_json:
                gsc = GSCClient(
                    site_url=settings.gsc_site_url,
                    credentials_json=settings.gsc_credentials_json
                )
                opportunities = gsc.get_low_hanging_fruits(limit=20)  # Fetch more to filter

                # Filter out used keywords and select first unused
                for opp in opportunities:
                    if opp.query.lower() not in used_keyword_set:
                        target_keyword = opp.query
                        target_context = {
                            "source": "GSC (Optimization)",
                            "metric": f"Pos: {opp.position}, Impr: {opp.impressions}"
                        }
                        logger.info(f"Selected unused GSC keyword: {target_keyword}")
                        break
        except Exception as e:
            logger.warning(f"GSC fetch failed: {e}")

        # 1.2 Try Content-Aware Keywords (Learns from website - high priority)
        if not target_keyword:
            try:
                from src.services.keyword_strategy import get_keyword_strategy

                # Get cached website profile (or analyze if needed)
                website_profile = await get_cached_website_profile()

                if website_profile:
                    logger.info(f"Using website profile: {len(website_profile.product_categories)} categories, "
                               f"Business: {website_profile.business_type}, "
                               f"Audience: {website_profile.target_audience}")

                    # Generate keywords based on website content
                    keyword_strategy = get_keyword_strategy(website_profile)
                else:
                    # Fallback to default keywords if analysis failed
                    logger.warning("Website analysis unavailable, using default keyword strategy")
                    keyword_strategy = get_keyword_strategy(None)

                keyword_pool = keyword_strategy.generate_keyword_pool(limit=100)

                # Filter out used keywords
                available_candidates = [
                    kw for kw in keyword_pool
                    if kw.keyword.lower() not in used_keyword_set
                ]

                # Apply semantic diversity filter (avoid similar keywords on same day)
                if today_keyword_list:
                    available_candidates = keyword_strategy.filter_by_semantic_diversity(
                        candidates=available_candidates,
                        selected_keywords=today_keyword_list,
                        min_diversity_score=0.4  # 40% different words required
                    )

                if available_candidates:
                    # Prioritize long-tail keywords (easier to rank)
                    long_tail = [kw for kw in available_candidates if kw.is_long_tail]
                    selected = long_tail[0] if long_tail else available_candidates[0]

                    target_keyword = selected.keyword
                    target_context = {
                        "source": "Content-Aware (Website Analysis)",
                        "metric": f"Stage: {selected.journey_stage.value}, Intent: {selected.intent.value}"
                    }
                    logger.info(f"Selected content-aware keyword: {target_keyword} (Stage: {selected.journey_stage.value})")
            except Exception as e:
                logger.warning(f"Content-aware keyword generation failed: {e}")

        # 1.3 Try Keyword API (Expansion)
        kw_client = None
        if not target_keyword and settings.keyword_api_key:
            try:
                from src.integrations.keyword_client import KeywordClient
                kw_client = KeywordClient()

                # Use first product category as seed (dynamic)
                seed = "packaging bottles"
                if website_profile and website_profile.product_categories:
                    seed = website_profile.product_categories[0]
                    logger.info(f"Using dynamic seed from website: {seed}")

                suggestions = await kw_client.get_easy_wins(seed)

                # Filter out used keywords
                for kw in suggestions:
                    if kw.keyword.lower() not in used_keyword_set:
                        target_keyword = kw.keyword
                        target_context = {
                            "source": "KeywordAPI (Expansion)",
                            "metric": f"Vol: {kw.volume}, KD: {kw.difficulty}"
                        }
                        logger.info(f"Selected unused Keyword API keyword: {target_keyword}")
                        break
            except Exception as e:
                logger.warning(f"Keyword API fetch failed: {e}")

        # 1.4 Fallback (generic packaging keywords)
        if not target_keyword:
            fallback_keywords = [
                # Product types
                "cosmetic packaging bottles wholesale",
                "bulk packaging containers supplier",
                "custom bottles with logo",
                # Material & features
                "glass bottles for cosmetics",
                "plastic jars wholesale",
                "pump bottles supplier",
                # Business queries
                "packaging supplier for small business",
                "wholesale packaging manufacturer",
                "custom packaging solutions",
                # How-to guides
                "how to choose packaging supplier",
                "packaging materials comparison",
                "sustainable packaging options",
                # Industry specific
                "cosmetic packaging trends 2026",
                "food grade packaging bottles",
                "pharmaceutical packaging containers",
                # B2B focused
                "bulk order packaging bottles",
                "private label packaging supplier",
                "OEM packaging manufacturer",
            ]
            # Select first unused fallback
            for fb_kw in fallback_keywords:
                if fb_kw.lower() not in used_keyword_set:
                    target_keyword = fb_kw
                    target_context = {"source": "Fallback"}
                    logger.info(f"Selected unused fallback keyword: {target_keyword}")
                    break

            # If all fallbacks used, use first one anyway
            if not target_keyword:
                target_keyword = fallback_keywords[0]
                target_context = {"source": "Fallback (all used)"}
                logger.warning("All fallback keywords used, reusing first one")

        # Save keyword to database with IN_PROGRESS status
        keyword_record = db.query(Keyword).filter(Keyword.keyword == target_keyword).first()
        if not keyword_record:
            keyword_record = Keyword(
                keyword=target_keyword,
                status=KeywordStatus.IN_PROGRESS
            )
            db.add(keyword_record)
        else:
            keyword_record.status = KeywordStatus.IN_PROGRESS
        db.commit()
        logger.info(f"Marked keyword as IN_PROGRESS: {target_keyword}")

        result["steps"].append({ "step": "strategy_target", "data": {"keyword": target_keyword, "context": target_context} })

        # --- Layer 2: Semantic Context ---
        semantic_keywords = []
        if kw_client and target_keyword:
            try:
                # Fetch related terms for LSI
                related = await kw_client.get_keyword_suggestions(target_keyword, limit=5)
                semantic_keywords = [r.keyword for r in related]
            except:
                pass
        
        # --- Layer 3: Internal Linking Context ---
        existing_posts_context = []
        wp_adapter = WordPressAdapter(
            base_url=settings.wordpress_url,
            username=settings.wordpress_username,
            password=settings.wordpress_password,
            seo_plugin=settings.seo_plugin
        )
        
        try:
            # Fetch recent posts for internal linking context
            recent_posts = await wp_adapter.get_simple_posts_for_linking(limit=10)
            existing_posts_context = [f"- {p['title']} (URL: {p['link']})" for p in recent_posts]
        except Exception as e:
            logger.warning(f"Failed to fetch internal linking context: {e}")

        # --- Layer 4: Expert Content Creation (AI) ---
        from src.core.ai_provider import AIProviderFactory
        ai = AIProviderFactory.create_from_config({
            "name": settings.primary_ai_provider,
            "base_url": settings.primary_ai_base_url,
            "api_key": settings.primary_ai_api_key,
            "models": {"text": settings.primary_ai_text_model, "image": settings.primary_ai_image_model}
        })
        
        # 4.1 Strategy & Outline Prompt
        semantic_str = ", ".join(semantic_keywords) if semantic_keywords else "relevant industry terms"
        linking_str = "\n".join(existing_posts_context) if existing_posts_context else "No existing posts to link to."
        
        outline_prompt = f"""
        **Role**: Expert Content Strategist & Niche Authority.
        **Task**: Create a comprehensive outline for "{target_keyword}".
        **Audience**: Users with commercial/informational intent.
        
        **SEO Requirements**:
        1. Primary Keyword: "{target_keyword}"
        2. Semantic Terms to Weave in: {semantic_str}
        3. E-E-A-T: Must demonstrate depth and first-hand expertise.
        
        **Structure Requirements**:
        - **H1**: High-CTR title.
        - **Introduction**: Hook + "The Verdict" (Quick Answer).
        - **Body**: 4-6 Deep Dive Sections. MUST include a "Comparison" or "Data Analysis" section.
        - **Value Add**: A "Step-by-Step Guide", "Checklist", or "Pro Tips" box.
        - **FAQ**: 3-5 real questions humans ask (Schema ready).
        """
        
        outline = await ai.generate_text(outline_prompt, temperature=0.7)
        
        # 4.2 Full Content Prompt
        article_prompt = f"""
        **Role**: Senior Industry Journalist.
        **Task**: Write the FULL article based on this outline:
        {outline}
        
        **Writing Guidelines**:
        - **Length**: 1500-2500 words (Depth is key).
        - **Tone**: Professional yet accessible. Avoid "AI fluff" words (like "realm", "landscape", "testament").
        - **Formatting**: Rich HTML. Use <h2>, <h3>, <ul>, <strong>, <blockquote>.
        - **Data/Tables**: You MUST create at least one HTML data table (<table>).
        
        **Internal Linking Directive**:
        Naturally mention and link to 1-2 of these existing articles where relevant:
        {linking_str}
        (Format: <a href="URL">Title</a>)
        
        **Output Format**:
        Return ONLY the HTML body content (no <html> or <body> tags).
        """
        
        # High timeout for deep content
        content_html = await ai.generate_text(article_prompt, temperature=0.7, max_tokens=3500)
        
        # 4.3 Meta Prompt (SMART DYNAMIC YEAR)
        current_year = datetime.now().year
        meta_prompt = f"""
        Generate JSON SEO Metadata for this article about "{target_keyword}".
        Current Year: {current_year}
        
        Format: {{"title": "...", "meta_description": "...", "excerpt": "..."}}
        
        Guidelines:
        - Title: Use ONE of these formats randomly:
          1. "How to [X]..." (NO year)
          2. "[N] Best [X] ({current_year} Review)" (Use year)
          3. "The Complete [X] Guide" (NO year)
          4. "[X] Explained: What You Need to Know" (NO year)
          5. "Top [N] [X] Trends for {current_year}" (Use year)
        
        - Desc: <160 chars, compelling hook. You make use "Updated for {current_year}" if relevant, but do not overuse.
        """
        meta_json_str = await ai.generate_text(meta_prompt, temperature=0.5)
        
        try:
            import json
            clean_json = meta_json_str.replace("```json", "").replace("```", "").strip()
            meta_data = json.loads(clean_json)
        except:
            meta_data = {"title": f"{target_keyword} Guide", "meta_description": "Read more...", "excerpt": ""}

        result["steps"].append({ "step": "creation", "data": {"words": len(content_html.split()), "model": settings.primary_ai_text_model} })

        # --- Layer 4.4: Generate Featured Image ---
        featured_image_bytes = None
        try:
            from src.agents.media_creator import MediaCreatorAgent
            media_agent = MediaCreatorAgent(ai_provider=ai)
            
            image_task = {
                "type": "create_featured_image",
                "title": meta_data.get("title", target_keyword),
                "keyword": target_keyword
            }
            
            image_result = await media_agent.execute(image_task)
            if image_result.get("status") == "success":
                featured_image_bytes = image_result.get("image")
                logger.info(f"Featured image generated: {len(featured_image_bytes)} bytes")
            
            result["steps"].append({ "step": "image_generation", "data": {"status": "success", "size": len(featured_image_bytes)} })
        except Exception as img_error:
            logger.warning(f"Image generation failed, continuing without image: {img_error}")
            result["steps"].append({ "step": "image_generation", "data": {"status": "skipped", "error": str(img_error)} })

        # --- Layer 5: Publishing ---
        content = PublishableContent(
            title=meta_data.get("title"),
            content=content_html,
            excerpt=meta_data.get("excerpt"),
            status="publish" if auto_publish else "draft",
            seo_title=meta_data.get("title"),
            seo_description=meta_data.get("meta_description"),
            focus_keyword=target_keyword,
            categories=["Blog", "Guides"],
            featured_image_data=featured_image_bytes,
            featured_image_alt=meta_data.get("title"),
            source_type="autopilot_advanced_seo"
        )
        
        publish_result = await wp_adapter.publish(content)

        if publish_result.status == PublishStatus.SUCCESS:
            result["status"] = "success"
            result["post_id"] = publish_result.post_id
            result["post_url"] = publish_result.post_url

            # Update keyword status to PUBLISHED
            if keyword_record:
                keyword_record.status = KeywordStatus.PUBLISHED
                db.commit()
                logger.info(f"Marked keyword as PUBLISHED: {target_keyword}")

            # Create Content record
            from src.models.content import Content, ContentStatus
            content_record = Content(
                keyword_id=keyword_record.id if keyword_record else None,
                title=meta_data.get("title"),
                body=content_html,
                meta_description=meta_data.get("meta_description"),
                status=ContentStatus.PUBLISHED,
                wordpress_post_id=publish_result.post_id
            )
            db.add(content_record)
            db.commit()
            logger.info(f"Created Content record for post {publish_result.post_id}")
        else:
            result["status"] = "failed"
            result["error"] = publish_result.error

            # Mark keyword as DISCOVERED (failed, can retry)
            if keyword_record:
                keyword_record.status = KeywordStatus.DISCOVERED
                db.commit()
                logger.warning(f"Marked keyword as DISCOVERED (publish failed): {target_keyword}")
            
    except Exception as e:
        logger.error(f"Advanced generation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        result["status"] = "failed"
        result["error"] = str(e)

        # Rollback keyword status on failure
        try:
            if 'keyword_record' in locals() and keyword_record:
                keyword_record.status = KeywordStatus.DISCOVERED
                db.commit()
                logger.info(f"Rolled back keyword status to DISCOVERED: {target_keyword}")
        except Exception as rollback_error:
            logger.error(f"Failed to rollback keyword status: {rollback_error}")
    finally:
        # Close database session
        if 'db' in locals():
            db.close()

    result["completed_at"] = datetime.now().isoformat()
    return result


async def seo_optimization_job(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    SEO optimization job (P1)
    
    Analyzes existing content and optimizes SEO meta:
    - Improves titles for higher CTR
    - Rewrites meta descriptions
    - Updates focus keywords
    - Ensures proper keyword density
    """
    logger.info("Starting SEO optimization job")
    
    post_id = data.get("post_id")
    if not post_id:
        return {"status": "error", "error": "post_id required"}
    
    result = {
        "job_type": "seo_optimization",
        "post_id": post_id,
        "started_at": datetime.now().isoformat(),
        "optimizations": []
    }
    
    try:
        # Initialize WordPress adapter
        wp_adapter = WordPressAdapter(
            base_url=settings.wordpress_url,
            username=settings.wordpress_username,
            password=settings.wordpress_password,
            seo_plugin=settings.seo_plugin
        )
        
        # Fetch existing post
        post = await wp_adapter.client.get_post(post_id)
        if not post:
            return {"status": "error", "error": f"Post {post_id} not found"}
        
        current_title = post.get("title", {}).get("rendered", "")
        current_content = post.get("content", {}).get("rendered", "")
        current_excerpt = post.get("excerpt", {}).get("rendered", "")
        
        # Get current SEO meta if available
        current_seo = await wp_adapter.get_seo_meta(post_id)
        current_focus_kw = current_seo.get("focus_keyword", "")
        
        # Extract main topic from content for keyword analysis
        import re
        text_only = re.sub(r'<[^>]+>', ' ', current_content)
        word_count = len(text_only.split())
        
        # Initialize AI provider
        from src.core.ai_provider import AIProviderFactory
        ai = AIProviderFactory.create_from_config({
            "name": settings.primary_ai_provider,
            "base_url": settings.primary_ai_base_url,
            "api_key": settings.primary_ai_api_key,
            "models": {"text": settings.primary_ai_text_model, "image": settings.primary_ai_image_model}
        })
        
        # AI prompt for SEO optimization
        optimization_prompt = f"""
        Analyze this article and generate optimized SEO metadata.
        
        **Current Title**: {current_title}
        **Current Focus Keyword**: {current_focus_kw or "Not set"}
        **Word Count**: {word_count}
        **Content Preview**: {text_only[:1000]}...
        
        **Task**: Generate JSON with optimized SEO meta:
        {{
            "seo_title": "High-CTR title (50-60 chars). See guidelines below.",
            "meta_description": "Compelling description (150-160 chars).",
            "focus_keyword": "Primary target keyword phrase (2-4 words)",
            "secondary_keywords": ["keyword1", "keyword2", "keyword3"]
        }}
        
        **Guidelines**:
        - Current Year: {datetime.now().year}
        - Title Strategy: 
          - For "Best/Top/Review" intent: MUST include "({datetime.now().year})" or "in {datetime.now().year}" to signal freshness.
          - For "Guide/How-to" intent: Do NOT use year unless it's a "State of the Industry" report.
          - Use diverse formats: "How-to", "vs", "Listicle", "Guide".
        - Description: Focus on benefits. Can use "Updated for {datetime.now().year}" for freshness.
        
        Return ONLY valid JSON.
        """
        
        seo_json_str = await ai.generate_text(optimization_prompt, temperature=0.5)
        
        # Parse AI response
        import json
        try:
            clean_json = seo_json_str.replace("```json", "").replace("```", "").strip()
            optimized_seo = json.loads(clean_json)
        except:
            logger.warning("Failed to parse AI SEO response, using fallback")
            optimized_seo = {
                "seo_title": current_title,
                "meta_description": current_excerpt[:160] if current_excerpt else "",
                "focus_keyword": current_focus_kw or "",
                "secondary_keywords": []
            }
        
        # Apply optimizations via WordPress adapter
        seo_update = {
            "seo_title": optimized_seo.get("seo_title", ""),
            "seo_description": optimized_seo.get("meta_description", ""),
            "focus_keyword": optimized_seo.get("focus_keyword", "")
        }
        
        update_result = await wp_adapter.update_seo_meta(post_id, seo_update)
        
        if update_result:
            result["optimizations"] = ["seo_title", "meta_description", "focus_keyword"]
            result["status"] = "success"
            result["new_seo"] = seo_update
        else:
            result["status"] = "partial"
            result["message"] = "Optimization generated but update failed"
            result["new_seo"] = seo_update
            
    except Exception as e:
        logger.error(f"SEO optimization failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        result["status"] = "failed"
        result["error"] = str(e)
    
    result["completed_at"] = datetime.now().isoformat()
    return result


async def content_refresh_job(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Content refresh job (P1) - GSC Driven
    
    Updates existing content to improve rankings:
    - Identifies declining pages via GSC
    - Adds new sections based on gaps
    - Adds FAQ sections for featured snippets
    - Updates outdated information
    - Saves as draft for review
    """
    logger.info("Starting content refresh job")
    
    result = {
        "job_type": "content_refresh",
        "started_at": datetime.now().isoformat(),
        "refreshed_posts": []
    }
    
    # Can be triggered with specific post_id or auto-detect via GSC
    post_id = data.get("post_id")
    auto_detect = data.get("auto_detect", True)
    max_posts = data.get("max_posts", 3)
    
    try:
        # Initialize WordPress adapter
        wp_adapter = WordPressAdapter(
            base_url=settings.wordpress_url,
            username=settings.wordpress_username,
            password=settings.wordpress_password,
            seo_plugin=settings.seo_plugin
        )
        
        posts_to_refresh = []
        
        # Strategy 1: Specific post requested
        if post_id:
            posts_to_refresh.append({"post_id": post_id, "reason": "manual_request"})
        
        # Strategy 2: Auto-detect declining pages via GSC
        elif auto_detect and settings.gsc_site_url and settings.gsc_credentials_json:
            try:
                from src.integrations.gsc_client import GSCClient
                gsc = GSCClient(
                    site_url=settings.gsc_site_url,
                    credentials_json=settings.gsc_credentials_json
                )
                
                declining = gsc.get_declining_pages(compare_days=28, decline_threshold=0.2)
                
                for page in declining[:max_posts]:
                    # Extract post ID from URL (assumes standard WP permalink)
                    page_url = page.get("page", "")
                    # Try to get post by URL
                    posts_to_refresh.append({
                        "page_url": page_url,
                        "reason": f"GSC decline: {page.get('change_percent')}%",
                        "metrics": page
                    })
                    
            except Exception as e:
                logger.warning(f"GSC auto-detect failed: {e}")
        
        if not posts_to_refresh:
            return {
                "status": "skipped",
                "message": "No posts identified for refresh",
                "completed_at": datetime.now().isoformat()
            }
        
        # Initialize AI provider
        from src.core.ai_provider import AIProviderFactory
        ai = AIProviderFactory.create_from_config({
            "name": settings.primary_ai_provider,
            "base_url": settings.primary_ai_base_url,
            "api_key": settings.primary_ai_api_key,
            "models": {"text": settings.primary_ai_text_model, "image": settings.primary_ai_image_model}
        })
        
        # Process each post
        for post_info in posts_to_refresh:
            try:
                # Get post content
                if post_info.get("post_id"):
                    post = await wp_adapter.client.get_post(post_info["post_id"])
                    target_post_id = post_info["post_id"]
                else:
                    # Search by URL - simplified lookup
                    logger.info(f"Looking up post for URL: {post_info.get('page_url')}")
                    continue  # Skip URL-based for now, needs slug extraction
                
                if not post:
                    continue
                    
                current_content = post.get("content", {}).get("rendered", "")
                current_title = post.get("title", {}).get("rendered", "")
                
                # Analyze content gaps
                import re
                text_only = re.sub(r'<[^>]+>', ' ', current_content)
                word_count = len(text_only.split())
                has_faq = bool(re.search(r'faq|frequently asked', current_content, re.IGNORECASE))
                has_table = '<table' in current_content.lower()
                
                # Generate refresh content
                refresh_prompt = f"""
                **Role**: Content Refresh Specialist
                **Task**: Enhance this existing article to improve search rankings.
                
                **Current Article**:
                - Title: {current_title}
                - Word Count: {word_count}
                - Has FAQ: {has_faq}
                - Has Table: {has_table}
                
                **Content Preview**:
                {text_only[:2000]}
                
                **Refresh Requirements**:
                1. {"Add a comprehensive FAQ section (5 questions) with Schema markup" if not has_faq else "FAQ exists, skip"}
                2. {"Add a comparison/data table" if not has_table else "Table exists, skip"}
                3. Add 200-400 words of fresh, valuable content
                3. Add 200-400 words of fresh, valuable content
                4. Update outdated information. You MAY mention "{datetime.now().year}" only if relevant to current trends/prices.
                5. Strengthen E-E-A-T signals
                
                **Output Format**:
                Return ONLY the NEW HTML sections to ADD (not the full article).
                Format as:
                <!-- REFRESH START -->
                [New sections here]
                <!-- REFRESH END -->
                """
                
                refresh_content = await ai.generate_text(refresh_prompt, temperature=0.7, max_tokens=2000)
                
                # Append refresh content to original
                enhanced_content = current_content + "\n\n" + refresh_content
                
                # Update post as draft (for review)
                update_data = {
                    "content": enhanced_content,
                    "status": "draft"  # Save as draft for human review
                }
                
                await wp_adapter.client.update_post(target_post_id, update_data)
                
                result["refreshed_posts"].append({
                    "post_id": target_post_id,
                    "title": current_title,
                    "reason": post_info.get("reason"),
                    "additions": {
                        "faq_added": not has_faq,
                        "table_added": not has_table,
                        "words_added": len(refresh_content.split())
                    },
                    "status": "draft_created"
                })
                
            except Exception as post_error:
                logger.error(f"Failed to refresh post: {post_error}")
                result["refreshed_posts"].append({
                    "post_id": post_info.get("post_id"),
                    "error": str(post_error)
                })
        
        result["status"] = "success" if result["refreshed_posts"] else "no_changes"
        result["total_refreshed"] = len([p for p in result["refreshed_posts"] if "error" not in p])
        
    except Exception as e:
        logger.error(f"Content refresh job failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        result["status"] = "failed"
        result["error"] = str(e)
    
    result["completed_at"] = datetime.now().isoformat()
    return result


async def internal_linking_job(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Internal linking job (P1)
    
    Optimizes internal links for new content:
    - Builds site-wide link graph
    - Identifies semantically relevant pages
    - Adds 2-4 contextual internal links
    - Only modifies new/draft posts (safe operation)
    """
    logger.info("Starting internal linking job")
    
    result = {
        "job_type": "internal_linking",
        "started_at": datetime.now().isoformat(),
        "processed_posts": []
    }
    
    # Target a specific new post or find recent drafts
    post_id = data.get("post_id")
    process_recent_drafts = data.get("process_recent_drafts", False)
    max_links_to_add = data.get("max_links", 3)
    
    try:
        # Initialize WordPress adapter
        wp_adapter = WordPressAdapter(
            base_url=settings.wordpress_url,
            username=settings.wordpress_username,
            password=settings.wordpress_password,
            seo_plugin=settings.seo_plugin
        )
        
        # Get existing posts for link graph
        existing_posts = await wp_adapter.client.get_simple_posts_for_linking(limit=50)
        
        if not existing_posts:
            return {
                "status": "skipped",
                "message": "No existing posts found for linking",
                "completed_at": datetime.now().isoformat()
            }
        
        # Build link graph: title -> {url, excerpt, keywords}
        link_graph = []
        for post in existing_posts:
            link_graph.append({
                "title": post.get("title", ""),
                "url": post.get("link", ""),
                "excerpt": post.get("excerpt", "")[:200] if post.get("excerpt") else "",
                "id": post.get("id")
            })
        
        # Determine posts to process
        posts_to_process = []
        
        if post_id:
            post = await wp_adapter.client.get_post(post_id)
            if post:
                posts_to_process.append(post)
        elif process_recent_drafts:
            # Get recent draft posts (created in last 7 days)
            drafts = await wp_adapter.client.get_posts(status="draft", per_page=10)
            posts_to_process.extend(drafts)
        
        if not posts_to_process:
            return {
                "status": "skipped",
                "message": "No posts to process for internal linking",
                "completed_at": datetime.now().isoformat()
            }
        
        # Initialize AI provider
        from src.core.ai_provider import AIProviderFactory
        ai = AIProviderFactory.create_from_config({
            "name": settings.primary_ai_provider,
            "base_url": settings.primary_ai_base_url,
            "api_key": settings.primary_ai_api_key,
            "models": {"text": settings.primary_ai_text_model, "image": settings.primary_ai_image_model}
        })
        
        # Process each post
        for post in posts_to_process:
            try:
                target_post_id = post.get("id")
                current_content = post.get("content", {}).get("rendered", "")
                current_title = post.get("title", {}).get("rendered", "")
                
                # Skip if already has many internal links
                existing_link_count = current_content.lower().count('href="' + settings.wordpress_url.lower())
                if existing_link_count >= 5:
                    result["processed_posts"].append({
                        "post_id": target_post_id,
                        "status": "skipped",
                        "reason": f"Already has {existing_link_count} internal links"
                    })
                    continue
                
                # Build available posts string for AI
                available_posts = "\n".join([
                    f"- [{p['title']}]({p['url']}) - {p['excerpt']}"
                    for p in link_graph
                    if p['id'] != target_post_id  # Don't link to self
                ])
                
                # Strip HTML for content analysis
                import re
                text_only = re.sub(r'<[^>]+>', ' ', current_content)
                
                # AI prompt for internal linking
                linking_prompt = f"""
                **Role**: Internal Linking Specialist
                **Task**: Identify where to add internal links in this article.
                
                **Target Article**:
                Title: {current_title}
                Content: {text_only[:2000]}
                
                **Available Pages to Link**:
                {available_posts}
                
                **Instructions**:
                1. Find {max_links_to_add} natural spots in the content to add internal links
                2. Choose semantically relevant target pages
                3. Select anchor text that exists in the content
                
                **Output Format (JSON)**:
                [
                    {{
                        "anchor_text": "exact phrase from content",
                        "target_url": "url of target page",
                        "target_title": "title of target page",
                        "context": "brief explanation of relevance"
                    }}
                ]
                
                Return ONLY valid JSON array.
                """
                
                link_json_str = await ai.generate_text(linking_prompt, temperature=0.5)
                
                # Parse AI response
                import json
                try:
                    clean_json = link_json_str.replace("```json", "").replace("```", "").strip()
                    links_to_add = json.loads(clean_json)
                except:
                    logger.warning("Failed to parse AI linking response")
                    links_to_add = []
                
                # Apply links to content
                enhanced_content = current_content
                links_added = 0
                
                for link_info in links_to_add[:max_links_to_add]:
                    anchor = link_info.get("anchor_text", "")
                    target_url = link_info.get("target_url", "")
                    
                    if anchor and target_url and anchor in enhanced_content:
                        # Only replace first occurrence to avoid over-linking
                        link_html = f'<a href="{target_url}">{anchor}</a>'
                        enhanced_content = enhanced_content.replace(anchor, link_html, 1)
                        links_added += 1
                
                if links_added > 0:
                    # Update post
                    update_data = {"content": enhanced_content}
                    await wp_adapter.client.update_post(target_post_id, update_data)
                    
                    result["processed_posts"].append({
                        "post_id": target_post_id,
                        "title": current_title,
                        "status": "success",
                        "links_added": links_added,
                        "link_details": links_to_add[:links_added]
                    })
                else:
                    result["processed_posts"].append({
                        "post_id": target_post_id,
                        "status": "no_changes",
                        "reason": "No suitable linking opportunities found"
                    })
                    
            except Exception as post_error:
                logger.error(f"Failed to process post for linking: {post_error}")
                result["processed_posts"].append({
                    "post_id": post.get("id"),
                    "status": "error",
                    "error": str(post_error)
                })
        
        result["status"] = "success"
        result["total_processed"] = len(result["processed_posts"])
        result["total_links_added"] = sum(
            p.get("links_added", 0) for p in result["processed_posts"]
        )
        
    except Exception as e:
        logger.error(f"Internal linking job failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        result["status"] = "failed"
        result["error"] = str(e)
    
    result["completed_at"] = datetime.now().isoformat()
    return result



async def cannibalization_analysis_job(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cannibalization detection job (BUG-013)
    
    Periodically scans for keyword cannibalization using GSC data
    and generates a report.
    """
    logger.info("Starting cannibalization detection job")
    
    result = {
        "job_type": "cannibalization_analysis",
        "started_at": datetime.now().isoformat(),
        "issues_found": 0
    }
    
    try:
        from src.services.cannibalization import CannibalizationDetector
        detector = CannibalizationDetector()
        
        # Fetch GSC data
        gsc_data_dicts = []
        if settings.gsc_site_url and settings.gsc_credentials_json:
            try:
                from src.integrations.gsc_client import GSCClient
                gsc = GSCClient(
                    site_url=settings.gsc_site_url,
                    credentials_json=settings.gsc_credentials_json
                )
                
                # Fetch last 30 days of data
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                queries = gsc.get_search_analytics(
                    start_date=start_date,
                    end_date=end_date,
                    dimensions=["query", "page"],
                    row_limit=5000
                )
                
                gsc_data_dicts = [q.to_dict() for q in queries]
                result["rows_fetched"] = len(gsc_data_dicts)
                
            except Exception as e:
                logger.error(f"Failed to fetch GSC data: {e}")
                return {
                    "status": "failed", 
                    "error": f"GSC fetch failed: {str(e)}",
                    "completed_at": datetime.now().isoformat()
                }
        else:
            return {
                "status": "skipped", 
                "message": "GSC not configured",
                "completed_at": datetime.now().isoformat()
            }
            
        if not gsc_data_dicts:
            return {
                "status": "skipped",
                "message": "No GSC data available",
                "completed_at": datetime.now().isoformat()
            }

        # Run analysis
        report = await detector.analyze(
            gsc_data=gsc_data_dicts, 
            min_impressions=data.get("min_impressions", 20)
        )
        
        # Log findings
        result.update({
            "status": "success",
            "issues_found": report.total_issues,
            "critical_issues": report.issues_by_severity.get("critical", 0),
            "high_issues": report.issues_by_severity.get("high", 0),
            "health_score": report.health_score,
            "summary": report.summary,
            "top_priorities": report.top_priorities
        })
        
        logger.info(f"Cannibalization analysis complete: {report.total_issues} issues found")
        
    except Exception as e:
        logger.error(f"Cannibalization analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        result["status"] = "failed"
        result["error"] = str(e)
    
    result["completed_at"] = datetime.now().isoformat()
    return result


# Job registry for easy registration with autopilot
JOB_REGISTRY = {
    "content_generation": content_generation_job,
    "seo_optimization": seo_optimization_job,
    "content_refresh": content_refresh_job,
    "internal_linking": internal_linking_job,
    "cannibalization_analysis": cannibalization_analysis_job,
}


def register_all_jobs(autopilot):
    """Register all jobs with the autopilot scheduler"""
    for job_type, job_func in JOB_REGISTRY.items():
        autopilot.register_job(job_type, job_func)
    logger.info(f"Registered {len(JOB_REGISTRY)} jobs with autopilot")
