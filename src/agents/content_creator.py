from typing import Dict, Any, Optional, List
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ContentCreatorAgent(BaseAgent):
    """
    Content Creator Agent - Acts as the Content Writer
    Creates SEO-optimized content with full SEO context synchronization
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
        """
        Create comprehensive SEO-optimized article with synchronized SEO elements.
        
        CRITICAL: Uses title_must_use as the H1 to ensure title-content synchronization.
        """
        keyword = task.get("keyword", "")
        products = task.get("products", [])
        
        # NEW: Full SEOContext for synchronized content generation
        seo_context = task.get("seo_context", {})
        title_must_use = task.get("title_must_use", keyword)  # CRITICAL: This is the selected title
        research_context = task.get("research_context", {})
        outline = task.get("outline", {})
        semantic_keywords = task.get("semantic_keywords", [])
        internal_links = task.get("internal_links", [])
        
        has_seo_context = bool(seo_context) or bool(title_must_use != keyword)
        
        # Log synchronization info
        logger.info(f"Creating content with synchronized title: {title_must_use}")
        if seo_context.get("title_hook_type"):
            logger.info(f"Title hook type: {seo_context['title_hook_type']}")
        if seo_context.get("title_ctr_estimate"):
            logger.info(f"Expected CTR: {seo_context['title_ctr_estimate']:.3f}")

        # Build enhanced prompt with full SEO synchronization
        prompt = self._build_synchronized_prompt(
            keyword=keyword,
            title_must_use=title_must_use,
            hook_type=seo_context.get("title_hook_type") if seo_context else None,
            products=products,
            research_context=research_context,
            outline=outline,
            semantic_keywords=semantic_keywords,
            internal_links=internal_links
        )

        # Use higher token limit for synchronized content
        max_tokens = 4000 if has_seo_context else 3000
        content = await self.generate_text(prompt, max_tokens=max_tokens)
        
        # Validate that content uses the correct H1
        if title_must_use not in content:
            logger.warning(f"Generated content may not use required title: {title_must_use}")
            # Prepend H1 if missing
            if not content.strip().startswith("<h1"):
                content = f"<h1>{title_must_use}</h1>\n\n{content}"
        
        # Add citations if research sources available
        if research_context.get("research_sources"):
            content += self._generate_references_section(research_context["research_sources"])
        
        # Add internal links if provided
        if internal_links:
            content = self._integrate_internal_links(content, internal_links)

        await self.publish_event("content_generated", {
            "keyword": keyword,
            "title_used": title_must_use,
            "content_length": len(content),
            "has_seo_context": has_seo_context,
            "hook_type": seo_context.get("title_hook_type") if seo_context else None
        })

        return {
            "status": "success", 
            "content": content,
            "title_used": title_must_use,
            "has_seo_context": has_seo_context
        }
    
    def _build_synchronized_prompt(
        self,
        keyword: str,
        title_must_use: str,
        hook_type: Optional[str],
        products: list,
        research_context: dict,
        outline: dict,
        semantic_keywords: List[str],
        internal_links: List[dict]
    ) -> str:
        """
        Build synchronized prompt ensuring title-content alignment.
        
        CRITICAL RULES:
        1. MUST use title_must_use as H1
        2. Content must deliver on title's promise
        3. Hook type must be reflected throughout content
        """
        
        # Build hook-specific guidance
        hook_guidance = self._get_hook_guidance(hook_type)
        
        # Base prompt with mandatory title usage
        prompt = f"""# CONTENT CREATION TASK - SYNCHRONIZED SEO

## MANDATORY REQUIREMENTS (DO NOT VIOLATE)

1. **H1 TITLE (MUST USE EXACTLY)**:
   {title_must_use}
   
   ⚠️ CRITICAL: This exact title MUST be used as the H1. Do not modify it.

2. **FOCUS KEYWORD**:
   {keyword}

3. **HOOK TYPE ALIGNMENT**:
   Type: {hook_type or 'general'}
   {hook_guidance}

## RESEARCH DATA
"""
        
        # Add research context
        if research_context:
            prompt += f"""
**Business Context**:
- Business Intent Score: {research_context.get('business_intent', 'N/A')}
- Value Score: {research_context.get('value_score', 'N/A')}
- Research Sources: {', '.join(research_context.get('research_sources', []))}
"""
            
            # Add statistics
            stats = research_context.get('statistics', [])
            if stats:
                prompt += "\n**Key Statistics to Include**:\n"
                for stat in stats[:3]:
                    prompt += f"- {stat.get('value', 'X')}% {stat.get('metric', 'impact')}\n"
            
            # Add pain points
            pain_points = research_context.get('pain_points', [])
            if pain_points:
                prompt += "\n**Address These Pain Points**:\n"
                for pain in pain_points[:2]:
                    prompt += f"- {pain.get('category', 'Issue')}: {pain.get('description', '')}\n"
        
        # Add outline structure
        if outline:
            prompt += f"""

## ARTICLE STRUCTURE (Follow Closely)
"""
            if outline.get('hook'):
                prompt += f"**Opening Hook**: {outline['hook']}\n\n"
            
            sections = outline.get('sections', [])
            if sections:
                prompt += "**Sections**:\n"
                for i, section in enumerate(sections, 1):
                    section_title = section.get('title', f'Section {i}')
                    content_type = section.get('content_type', 'general')
                    key_points = section.get('key_points', [])
                    
                    prompt += f"\n{i}. **{section_title}** ({content_type})\n"
                    if key_points:
                        for point in key_points[:3]:
                            prompt += f"   - {point}\n"
            
            if outline.get('conclusion_type'):
                prompt += f"\n**Conclusion Type**: {outline['conclusion_type'].upper()}\n"
        
        # Add semantic keywords
        if semantic_keywords:
            prompt += f"""

## SEMANTIC KEYWORDS (Integrate Naturally)
{', '.join(semantic_keywords)}
"""
        
        # Add internal links
        if internal_links:
            prompt += """

## INTERNAL LINKING OPPORTUNITIES
"""
            for link in internal_links[:3]:
                prompt += f"- Link to: {link.get('target_title', 'N/A')} ({link.get('target_url', 'N/A')})\n"
                suggestions = link.get('anchor_text_suggestions', [])
                if suggestions:
                    prompt += f"  Suggested anchors: {', '.join(suggestions[:2])}\n"
        
        # Add comprehensive writing guidelines
        prompt += f"""

## WRITING GUIDELINES

**Length**: 2000+ words (comprehensive coverage required)

**Keyword Integration**:
- Primary keyword "{keyword}" should appear naturally 1-2% density
- Include semantic keywords throughout
- First paragraph MUST contain the primary keyword

**Content Quality Standards**:
1. **Title-Content Alignment**: Every section must deliver on the title's promise
2. **Data-Driven**: Use statistics and research data provided
3. **Actionable**: Include practical steps and "Pro Tips" callout boxes
4. **Expert Tone**: Demonstrate E-E-A-T (Experience, Expertise, Authoritativeness, Trust)
5. **Rich Formatting**: Use H2, H3, bullet points, tables, and blockquotes
6. **Internal Links**: Naturally mention 2-3 related articles with anchor text

**Products to Mention**:
{products if products else 'None specified'}

**Output Format**:
- Start with H1: {title_must_use}
- Use proper HTML tags (<h2>, <h3>, <p>, <ul>, etc.)
- Include FAQ section at the end
- No <html>, <head>, or <body> tags

**Content Must Match Hook Type**:
{self._get_hook_specific_requirements(hook_type)}

Write the complete article now:
"""
        
        return prompt
    
    def _get_hook_guidance(self, hook_type: Optional[str]) -> str:
        """Get guidance based on hook type"""
        guidance_map = {
            "data": """
   - Start with compelling statistics
   - Include data tables or comparisons
   - Reference research and studies
   - Use percentages and numbers throughout""",
            "problem": """
   - Open with the pain point
   - Agitate the problem before solution
   - Show consequences of inaction
   - Provide clear resolution""",
            "how_to": """
   - Promise clear step-by-step guidance
   - Include actionable steps
   - Provide checklists
   - Show before/after scenarios""",
            "question": """
   - Address the question directly
   - Provide comprehensive answer
   - Include related FAQs
   - Challenge common assumptions""",
            "story": """
   - Include case study or example
   - Show real-world application
   - Include quotes or testimonials
   - Demonstrate transformation""",
            "controversy": """
   - Present contrasting viewpoints
   - Debunk myths
   - Provide evidence-based conclusions
   - Challenge conventional wisdom"""
        }
        return guidance_map.get(hook_type, "- Use engaging, professional tone")
    
    def _get_hook_specific_requirements(self, hook_type: Optional[str]) -> str:
        """Get specific requirements based on hook type"""
        requirements_map = {
            "data": """
- MUST include at least one data table
- Use specific statistics in headings
- Reference data sources
- Compare before/after with numbers""",
            "problem": """
- First section must describe the problem deeply
- Include "Why This Matters" section
- Show real-world impact
- Transition to solution must be clear""",
            "how_to": """
- Include step-by-step numbered list
- Add "What You'll Need" section
- Provide troubleshooting tips
- Include success metrics""",
            "question": """
- Answer the question in first paragraph
- Include "Why People Ask This" section
- Address related questions
- Provide definitive conclusion""",
            "story": """
- Include narrative elements
- Quote real people or studies
- Show journey/transformation
- Extract lessons learned""",
            "controversy": """
- Present both sides fairly
- Use evidence to support claims
- Include "Myth vs Reality" section
- Provide balanced conclusion"""
        }
        return requirements_map.get(hook_type, "- Maintain professional, authoritative tone throughout")
    
    def _integrate_internal_links(self, content: str, internal_links: List[dict]) -> str:
        """Integrate internal links into content naturally"""
        if not internal_links:
            return content
        
        # This is a simple implementation - could be enhanced with NLP for better placement
        import re
        
        for link in internal_links[:3]:  # Max 3 internal links
            target_title = link.get('target_title', '')
            target_url = link.get('target_url', '')
            suggestions = link.get('anchor_text_suggestions', [target_title])
            
            if target_title and target_url and suggestions:
                # Try to find a good place to insert the link
                anchor = suggestions[0]
                # Simple regex to find the anchor text and replace with link
                pattern = r'\b' + re.escape(anchor) + r'\b'
                replacement = f'<a href="{target_url}">{anchor}</a>'
                content = re.sub(pattern, replacement, content, count=1, flags=re.IGNORECASE)
        
        return content
    
    def _generate_references_section(self, sources: list) -> str:
        """Generate references/citations section"""
        if not sources:
            return ""
        
        references = "\n\n## References\n\n"
        for i, source in enumerate(sources, 1):
            name = source.get('name', 'Unknown Source')
            url = source.get('url', '')
            source_type = source.get('type', 'reference')
            
            if url:
                references += f"{i}. [{name}]({url}) - {source_type.replace('_', ' ').title()}\n"
            else:
                references += f"{i}. {name} - {source_type.replace('_', ' ').title()}\n"
        
        return references

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
