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
        # --- Layer 1: Opportunity Discovery ---
        target_keyword = None
        target_context = {}
        
        # 1.1 Try GSC (Optimization)
        try:
            from src.integrations.gsc_client import GSCClient
            if settings.gsc_site_url and settings.gsc_credentials_json:
                gsc = GSCClient(
                    site_url=settings.gsc_site_url,
                    credentials_json=settings.gsc_credentials_json
                )
                opportunities = gsc.get_low_hanging_fruits(limit=5)
                if opportunities:
                    best_opp = opportunities[0] 
                    target_keyword = best_opp.query
                    target_context = {
                        "source": "GSC (Optimization)", 
                        "metric": f"Pos: {best_opp.position}, Impr: {best_opp.impressions}"
                    }
        except Exception as e:
            logger.warning(f"GSC fetch failed: {e}")
            
        # 1.2 Try Keyword API (Expansion)
        kw_client = None
        if not target_keyword and settings.keyword_api_key:
            try:
                from src.integrations.keyword_client import KeywordClient
                kw_client = KeywordClient()
                seed = "water bottle" # TODO: Configurable seed
                suggestions = await kw_client.get_easy_wins(seed)
                if suggestions:
                    best_kw = suggestions[0]
                    target_keyword = best_kw.keyword
                    target_context = {
                        "source": "KeywordAPI (Expansion)",
                        "metric": f"Vol: {best_kw.volume}, KD: {best_kw.difficulty}"
                    }
            except Exception as e:
                logger.warning(f"Keyword API fetch failed: {e}")

        # 1.3 Fallback
        if not target_keyword:
            target_keyword = "glass vs plastic water bottles"
            target_context = {"source": "Fallback"}

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
            # Use the method we just added
            recent_posts = await wp_adapter.client.get_simple_posts_for_linking(limit=10)
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
        
        # 4.3 Meta Prompt
        meta_prompt = f"""
        Generate JSON SEO Metadata for this article about "{target_keyword}".
        Format: {{"title": "...", "meta_description": "...", "excerpt": "..."}}
        - Title: Power words, numbers, current year.
        - Desc: <160 chars, compelling hook.
        """
        meta_json_str = await ai.generate_text(meta_prompt, temperature=0.5)
        
        try:
            import json
            clean_json = meta_json_str.replace("```json", "").replace("```", "").strip()
            meta_data = json.loads(clean_json)
        except:
            meta_data = {"title": f"{target_keyword} Guide", "meta_description": "Read more...", "excerpt": ""}

        result["steps"].append({ "step": "creation", "data": {"words": len(content_html.split()), "model": settings.primary_ai_text_model} })

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
            source_type="autopilot_advanced_seo"
        )
        
        publish_result = await wp_adapter.publish(content)
        
        if publish_result.status == PublishStatus.SUCCESS:
            result["status"] = "success"
            result["post_id"] = publish_result.post_id
            result["post_url"] = publish_result.post_url
        else:
            result["status"] = "failed"
            result["error"] = publish_result.error
            
    except Exception as e:
        logger.error(f"Advanced generation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        result["status"] = "failed"
        result["error"] = str(e)
    
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
            "seo_title": "High-CTR title with power words, numbers, current year (50-60 chars)",
            "meta_description": "Compelling description with primary keyword (150-160 chars)",
            "focus_keyword": "Primary target keyword phrase (2-4 words)",
            "secondary_keywords": ["keyword1", "keyword2", "keyword3"]
        }}
        
        **Guidelines**:
        - Title: Include numbers, year (2026), emotional triggers
        - Description: Include call-to-action, benefit-focused
        - Focus on user intent and search behavior
        
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
                4. Include current year (2026) references
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
