"""
Content Generation Jobs
Implements the actual content generation workflow for Autopilot

This module defines the job functions that are registered with AutopilotScheduler
and executed by JobRunner.
"""

import logging
from typing import Dict, Any, Optional
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
    SEO optimization job
    
    Analyzes existing content and optimizes SEO meta:
    - Improves titles
    - Rewrites meta descriptions
    - Updates focus keywords
    """
    logger.info("Starting SEO optimization job")
    
    post_id = data.get("post_id")
    if not post_id:
        return {"status": "error", "error": "post_id required"}
    
    # TODO: Implement actual SEO optimization
    return {
        "status": "completed",
        "post_id": post_id,
        "optimizations": ["title", "description"],
        "message": "SEO optimization placeholder"
    }


async def content_refresh_job(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Content refresh job (P1)
    
    Updates existing content to improve rankings:
    - Adds new sections
    - Updates outdated information
    - Adds FAQ sections
    - Improves internal linking
    """
    logger.info("Starting content refresh job")
    
    post_id = data.get("post_id")
    if not post_id:
        return {"status": "error", "error": "post_id required"}
    
    # TODO: Implement in P1
    return {
        "status": "skipped",
        "message": "Content refresh will be implemented in P1"
    }


async def internal_linking_job(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Internal linking job (P1)
    
    Optimizes internal links across the site:
    - Adds links to new content
    - Updates anchor text
    - Removes broken links
    """
    logger.info("Starting internal linking job")
    
    # TODO: Implement in P1
    return {
        "status": "skipped", 
        "message": "Internal linking will be implemented in P1"
    }


# Job registry for easy registration with autopilot
JOB_REGISTRY = {
    "content_generation": content_generation_job,
    "seo_optimization": seo_optimization_job,
    "content_refresh": content_refresh_job,
    "internal_linking": internal_linking_job,
}


def register_all_jobs(autopilot):
    """Register all jobs with the autopilot scheduler"""
    for job_type, job_func in JOB_REGISTRY.items():
        autopilot.register_job(job_type, job_func)
    logger.info(f"Registered {len(JOB_REGISTRY)} jobs with autopilot")
