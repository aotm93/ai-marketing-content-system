from typing import Dict, Any, Optional
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ContentCreatorAgent(BaseAgent):
    """
    Content Creator Agent - Acts as the Content Writer
    Creates SEO-optimized content with research integration
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
        Create comprehensive SEO-optimized article with research integration
        
        Enhanced to use research context and outlines from Content Intelligence Layer
        """
        keyword = task.get("keyword", "")
        products = task.get("products", [])
        
        # NEW: Research context from Content Intelligence Layer
        research_context = task.get("research_context", {})
        outline = task.get("outline", {})
        research_based = bool(research_context) or bool(outline)

        # Build enhanced prompt with research context
        prompt = self._build_enhanced_prompt(
            keyword=keyword,
            products=products,
            research_context=research_context,
            outline=outline
        )

        # Use higher token limit for research-based content
        max_tokens = 4000 if research_based else 3000
        content = await self.generate_text(prompt, max_tokens=max_tokens)
        
        # NEW: Add citations if research sources available
        if research_context.get("research_sources"):
            content += self._generate_references_section(research_context["research_sources"])

        await self.publish_event("content_generated", {
            "keyword": keyword,
            "content_length": len(content),
            "research_based": research_based
        })

        return {
            "status": "success", 
            "content": content,
            "research_based": research_based
        }
    
    def _build_enhanced_prompt(
        self,
        keyword: str,
        products: list,
        research_context: dict,
        outline: dict
    ) -> str:
        """Build enhanced prompt with research context"""
        
        # Base prompt
        prompt = f"""
        Write a comprehensive 2000+ word article optimized for: {keyword}
        """
        
        # Add research context if available
        if research_context:
            prompt += f"""

**RESEARCH CONTEXT** (Use this data to add authority):
- Business Intent Score: {research_context.get('business_intent', 'N/A')}
- Research Sources: {', '.join(research_context.get('research_sources', []))}
- Unique Angle: {research_context.get('angle', 'Focus on practical solutions')}
"""
            
            # Add statistics if available
            stats = research_context.get('statistics', [])
            if stats:
                prompt += "\n**Key Statistics to Include**:\n"
                for stat in stats[:3]:
                    prompt += f"- {stat.get('value', 'X')}% {stat.get('metric', 'impact')}\n"
            
            # Add pain points if available
            pain_points = research_context.get('pain_points', [])
            if pain_points:
                prompt += "\n**Address These Pain Points**:\n"
                for pain in pain_points[:2]:
                    prompt += f"- {pain.get('category', 'Issue')}: {pain.get('description', '')}\n"
        
        # Add outline if available
        if outline:
            prompt += f"""

**ARTICLE OUTLINE** (Follow this structure):
"""
            if outline.get('hook'):
                prompt += f"Hook: {outline['hook']}\n"
            
            sections = outline.get('sections', [])
            for i, section in enumerate(sections, 1):
                section_title = section.get('title', f'Section {i}')
                content_type = section.get('content_type', 'general')
                key_points = section.get('key_points', [])
                
                prompt += f"\n{i}. {section_title} ({content_type})\n"
                if key_points:
                    prompt += "   Key points to cover:\n"
                    for point in key_points[:3]:
                        prompt += f"   - {point}\n"
            
            if outline.get('conclusion_type'):
                prompt += f"\nConclusion: {outline['conclusion_type'].upper()}\n"
        
        # Add standard requirements
        prompt += f"""

**WRITING REQUIREMENTS**:
1. Engaging headline with keyword and hook
2. Clear H2/H3 structure matching the outline
3. Natural keyword integration (1-2% density)
4. **Include specific data points and statistics from research context**
5. **Reference real examples and case studies**
6. **Add expert quotes where relevant**
7. Actionable insights for wholesale buyers
8. Internal links to products: {products}
9. Meta description (150-160 chars)
10. FAQ section with schema markup

**CONTENT QUALITY STANDARDS**:
- Avoid generic advice - be specific and actionable
- Use concrete numbers and percentages from research
- Include "Pro Tips" callout boxes
- End each section with a takeaway
- Match the tone to the business intent score

Write professional, valuable content that demonstrates expertise.
"""
        
        return prompt
    
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
