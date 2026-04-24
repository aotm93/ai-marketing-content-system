from typing import Dict, Any, Optional, List
import hashlib
import logging
from .base_agent import BaseAgent
from src.services.content.professional_writer import ProfessionalContentWriter
from src.services.content.intent_analyzer import SearchIntentAnalyzer

logger = logging.getLogger(__name__)


class ContentCreatorAgent(BaseAgent):
    """
    Content Creator Agent - Acts as the Content Writer
    Creates SEO-optimized content with full SEO context synchronization
    """
    EDITORIAL_BLUEPRINTS = [
        {
            "name": "diagnostic_playbook",
            "opening": "Start with a direct verdict, then map the top 3 failure triggers or buying risks.",
            "flow": "Use a diagnostic table before recommendations; each section ends with a 'what to do next' note.",
            "evidence": "Prioritize measurements, thresholds, and supplier validation checks over narrative fluff.",
            "closing": "Close with a decision tree that routes readers to category, tag, or product pages.",
        },
        {
            "name": "procurement_briefing",
            "opening": "Open with a procurement snapshot: MOQ, lead time, and compliance implications in one paragraph.",
            "flow": "Structure sections as briefing modules (cost, quality, risk, timeline, negotiation).",
            "evidence": "Use short benchmark bullets and one comparison matrix per major decision point.",
            "closing": "End with a shortlist protocol and clear CTA sequencing for next actions.",
        },
        {
            "name": "spec_tradeoff_lab",
            "opening": "Open with the key tradeoff readers are likely to face when choosing options.",
            "flow": "Alternate between spec explanation and application scenarios to avoid repetitive structure.",
            "evidence": "Include pass/fail conditions, test methods, and not-recommended scenarios.",
            "closing": "Conclude with a fit-by-scenario checklist that maps to concrete next pages.",
        },
        {
            "name": "buyer_qa_interview",
            "opening": "Start with answer-first Q&A style so buyers get practical guidance immediately.",
            "flow": "Use section headers phrased as buyer questions, then answer with criteria and examples.",
            "evidence": "Ground answers with concrete data, qualification questions, and red-flag signals.",
            "closing": "Finish with a ranked next-step path (browse, shortlist, validate, quote).",
        },
    ]

    def __init__(self, name: str = "ContentCreator", ai_provider=None, event_bus=None, **kwargs):
        super().__init__(name=name, ai_provider=ai_provider, event_bus=event_bus)
        self.professional_writer = ProfessionalContentWriter()
        self.intent_analyzer = SearchIntentAnalyzer()
        logger.info(f"{self.name} initialized with professional content generation")

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
        category_context = task.get("category_context", {})
        tag_context = task.get("tag_context", {})
        primary_catalog_context = task.get("primary_catalog_context", {})
        decision_questions = task.get("decision_questions", [])
        commercial_facts = task.get("commercial_facts", [])
        supporting_tags = task.get("supporting_tags", [])
        content_lane = task.get("content_lane", seo_context.get("content_lane") if seo_context else "procurement_conversion")
        content_lane_confidence = task.get("content_lane_confidence", seo_context.get("content_lane_confidence") if seo_context else None)
        search_stage = task.get("search_stage", seo_context.get("search_stage") if seo_context else None)
        serp_role = task.get("serp_role", seo_context.get("serp_role") if seo_context else None)
        page_type = task.get("page_type", seo_context.get("page_type") if seo_context else "category_support")
        article_content_type = task.get("article_content_type", "general")
        planned_outline = task.get("planned_outline", [])
        
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
            page_type=page_type,
            category_context=category_context,
            tag_context=tag_context,
            primary_catalog_context=primary_catalog_context,
            decision_questions=decision_questions,
            commercial_facts=commercial_facts,
            supporting_tags=supporting_tags,
            content_lane=content_lane,
            content_lane_confidence=content_lane_confidence,
            search_stage=search_stage,
            serp_role=serp_role,
            semantic_keywords=semantic_keywords,
            internal_links=internal_links,
            article_content_type=article_content_type,
            planned_outline=planned_outline,
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
        page_type: str,
        category_context: dict,
        tag_context: dict,
        primary_catalog_context: dict,
        decision_questions: List[str],
        commercial_facts: List[str],
        supporting_tags: List[str],
        content_lane: str,
        content_lane_confidence: Optional[float],
        search_stage: Optional[str],
        serp_role: Optional[str],
        semantic_keywords: List[str],
        internal_links: List[dict],
        article_content_type: Optional[str] = None,    # NEW: content type from ContentPlannerService
        planned_outline: Optional[list] = None,         # NEW: type-specific section outline
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
        editorial_blueprint = self._select_editorial_blueprint(
            keyword=keyword,
            title_must_use=title_must_use,
            page_type=page_type,
            hook_type=hook_type,
            content_lane=content_lane,
        )
        
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

4. **EDITORIAL BLUEPRINT (ANTI-TEMPLATE MODE)**:
   - Blueprint: {editorial_blueprint['name']}
   - Opening approach: {editorial_blueprint['opening']}
   - Section flow: {editorial_blueprint['flow']}
   - Evidence pattern: {editorial_blueprint['evidence']}
   - Closing pattern: {editorial_blueprint['closing']}
   - Do NOT fall back to one-size-fits-all article sequencing.

5. **CONTENT LANE / SEARCH STAGE**:
   - Lane: {content_lane}
   - Search stage: {search_stage or 'unspecified'}
   - SERP role: {serp_role or 'general'}
   - Lane confidence: {content_lane_confidence if content_lane_confidence is not None else 'N/A'}
   {self._get_content_lane_requirements(content_lane, search_stage, serp_role)}

## RESEARCH DATA
"""

        # Inject content type guidance (when ContentPlannerService ran successfully)
        content_type_guidance = self._get_content_type_guidance(article_content_type)
        if content_type_guidance:
            prompt += content_type_guidance
        prompt += f"""

## PAGE TYPE
- Page Type: {page_type}
{self._get_page_type_requirements(page_type, category_context, tag_context, primary_catalog_context)}
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

        if category_context and category_context.get("name"):
            prompt += f"""

## TARGET CATEGORY
- Primary category to support: {category_context.get('name')}
- Category URL: {category_context.get('url', 'N/A')}
- Category slug: {category_context.get('slug', 'N/A')}
- Treat this article as a supporting entry point that should naturally guide readers to the category page
"""

        if tag_context and tag_context.get("name"):
            prompt += f"""

## TARGET TAG PAGE
- Important tag/archive page to support: {tag_context.get('name')}
- Tag URL: {tag_context.get('url', 'N/A')}
- Tag slug: {tag_context.get('slug', 'N/A')}
- Use this page as an equal-priority next step when the article discusses a narrower material, feature, closure, or application angle
"""

        if primary_catalog_context and primary_catalog_context.get("name"):
            prompt += f"""

## PRIMARY LANDING PAGE
- Primary destination type: {primary_catalog_context.get('type', 'catalog')}
- Primary destination name: {primary_catalog_context.get('name')}
- Primary destination URL: {primary_catalog_context.get('url', 'N/A')}
- This should be the main CTA path unless the article explicitly narrows to a more specific product example
"""

        if products:
            prompt += """

## SUPPORTING PRODUCTS / EXAMPLES
Use these real catalog examples to ground the content. Mention them only where relevant and explain why they fit.
"""
            for product in products[:3]:
                if isinstance(product, dict):
                    facts = [
                        product.get("capacity"),
                        product.get("material"),
                        product.get("closure_type"),
                        product.get("neck_finish"),
                        product.get("use_case"),
                    ]
                    fact_text = ", ".join(value for value in facts if value)
                    prompt += f"- {product.get('name', 'Unnamed product')} ({fact_text or 'commercial example'})"
                    if product.get("url"):
                        prompt += f" - URL: {product['url']}"
                    prompt += "\n"
                else:
                    prompt += f"- {product}\n"

        if supporting_tags:
            prompt += f"""

## SUPPORTING TAGS
Use these terms where they naturally help align with catalog taxonomy:
{', '.join(supporting_tags[:8])}
"""

        if decision_questions:
            prompt += """

## DECISION QUESTIONS THE ARTICLE MUST ANSWER
"""
            for question in decision_questions[:5]:
                prompt += f"- {question}\n"

        faq_requirements = self._build_faq_requirements(
            keyword=keyword,
            page_type=page_type,
            primary_catalog_context=primary_catalog_context,
            category_context=category_context,
            tag_context=tag_context,
            decision_questions=decision_questions,
            products=products,
        )
        if faq_requirements:
            prompt += f"""

## FAQ REQUIREMENTS
{faq_requirements}
"""

        if commercial_facts:
            prompt += """

## COMMERCIAL FACTS TO WEAVE INTO THE ARTICLE
Use these as concrete buying or sourcing anchors instead of generic filler:
"""
            for fact in commercial_facts[:8]:
                prompt += f"- {fact}\n"
        
        # Use planned_outline (from ContentPlannerService) when available; fall back to ContentOutline
        if planned_outline:
            prompt += "\n## ARTICLE STRUCTURE (Follow Closely)\n"
            prompt += "**Sections** (type-specific — follow this order):\n"
            for i, section in enumerate(planned_outline, 1):
                section_title = section.get("title", f"Section {i}")
                section_type = section.get("section_type", "general")
                key_points = section.get("key_points", [])
                writing_notes = section.get("writing_notes", "")
                prompt += f"\n{i}. **{section_title}** ({section_type})\n"
                if writing_notes:
                    prompt += f"   Writer note: {writing_notes}\n"
                for point in key_points[:3]:
                    prompt += f"   - {point}\n"
        elif outline:
            # Fallback: use ContentOutline from ContentIntelligence (existing logic preserved)
            prompt += "\n## ARTICLE STRUCTURE (Follow Closely)\n"
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

        cta_requirements = self._build_cta_requirements(
            primary_catalog_context=primary_catalog_context,
            category_context=category_context,
            tag_context=tag_context,
            keyword=keyword,
            products=products,
        )
        if cta_requirements:
            prompt += f"""

## CTA REQUIREMENTS
{cta_requirements}
"""

        # Add professional content requirements based on intent
        intent_signal = self.intent_analyzer.analyze_intent(keyword)
        content_reqs = self.professional_writer.get_content_requirements(intent_signal.intent)

        if content_reqs:
            prompt += f"""

## PROFESSIONAL CONTENT REQUIREMENTS (Intent: {intent_signal.intent.value})
"""
            if content_reqs.get('root_cause_analysis'):
                prompt += "- Explain root causes with specific technical details\n"
            if content_reqs.get('actionable_solutions'):
                prompt += "- Provide data-backed, actionable solutions\n"
            if content_reqs.get('technical_parameters'):
                prompt += "- Include specific technical parameters and data\n"
            if content_reqs.get('require_standards'):
                prompt += "- Reference industry standards\n"
            if content_reqs.get('selection_criteria'):
                prompt += "- Give explicit selection criteria readers can use to compare products or suppliers\n"
            if content_reqs.get('supplier_evaluation'):
                prompt += "- Include MOQ, lead time, certifications, QC process, sampling, and audit checkpoints\n"
            if content_reqs.get('commercial_specifics'):
                prompt += "- Explain quote structure, cost drivers, and red flags that affect B2B purchasing decisions\n"
            if content_reqs.get('mechanism_analysis'):
                prompt += "- Explain mechanism, failure mode, or process with technically precise language\n"
            if content_reqs.get('test_methods'):
                prompt += "- Mention test methods, standards, or measurement conditions where relevant\n"
            if content_reqs.get('design_implications'):
                prompt += "- Translate technical findings into design, manufacturing, or sourcing implications\n"
            if content_reqs.get('avoid_generic'):
                prompt += "- Avoid generic advice like 'be careful' or 'follow best practices'\n"
                prompt += "- Skip basic introductory explanations\n"

        # Add comprehensive writing guidelines
        prompt += f"""

## WRITING GUIDELINES

**Length**: 2000+ words (comprehensive coverage required)

**Keyword Integration**:
- Use primary keyword "{keyword}" and its synonyms naturally throughout
- Include semantic keywords to build topical authority
- First paragraph MUST contain the primary keyword
- Focus on semantic relevance, not keyword density

**Content Quality Standards**:
1. **Title-Content Alignment**: Every section must deliver on the title's promise
2. **Data-Driven**: Use statistics and research data provided
3. **Actionable**: Include practical steps and "Pro Tips" callout boxes
4. **Featured Snippet Optimization**:
   - Provide a concise 40-60 word answer in the first paragraph
   - Use clear formatting (lists, tables) for step-by-step content
   - Structure FAQ with direct question-answer format
5. **Expert Tone**: Demonstrate E-E-A-T (Experience, Expertise, Authoritativeness, Trust)
6. **Rich Formatting**: Use H2, H3, bullet points, tables, and blockquotes
7. **Internal Links**: Naturally mention 2-3 related articles with anchor text

**NON-NEGOTIABLE VALUE RULES**:
- Do NOT write generic filler such as broad market overviews, empty trend talk, or vague statements like "quality is important"
- Every main section must answer a concrete decision question, such as what to choose, what causes failure, how to verify a supplier, what specs matter, or which trade-offs affect cost
- If the keyword is commercial or supplier-oriented, include a comparison table or checklist covering MOQ, lead time, customization, compliance, quality control, and quotation factors
- If the keyword is technical, include measurable parameters, operating conditions, failure causes, or test criteria instead of high-level summaries
- If research data is limited, still provide a rigorous evaluation framework, inspection checklist, or decision matrix rather than generic prose
- Avoid empty hype, trend cliches, and broad all-purpose explainer language unless directly supported by evidence
- Include a clear path from article to category, tag, or product exploration when catalog context is available
- When product examples are provided, explain why each example fits a use case, not just that it exists
- End with a buyer-oriented CTA section that clearly routes readers to the best next landing page

**Products to Mention**:
{self._format_products_for_prompt(products)}

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

    def _select_editorial_blueprint(
        self,
        keyword: str,
        title_must_use: str,
        page_type: str,
        hook_type: Optional[str],
        content_lane: str,
    ) -> Dict[str, str]:
        """Select a deterministic blueprint to diversify structure across articles."""
        key = f"{keyword}|{title_must_use}|{page_type}|{content_lane}|{hook_type or 'general'}"
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % len(self.EDITORIAL_BLUEPRINTS)
        return self.EDITORIAL_BLUEPRINTS[index]

    def _get_content_lane_requirements(self, content_lane: str, search_stage: Optional[str], serp_role: Optional[str]) -> str:
        """Return lane-specific constraints so title role propagates into the article body."""
        role_hint = self._get_serp_role_guidance(serp_role)
        if content_lane == "traffic_entry":
            return (
                "- Open from scenario, application fit, comparison, or problem framing\n"
                "- Make the article feel like a professional search-entry page, not an encyclopedia article\n"
                "- Explain why the specs or trade-offs matter in a real packaging or sourcing scenario\n"
                "- Bridge readers toward the correct category/tag/product page only after clarifying fit, risk, or selection logic\n"
                f"- Treat the reader as a {search_stage or 'mid-funnel'} searcher who needs decision value, not beginner education\n"
                f"{role_hint}"
            )
        return (
            "- Open from buyer decision stakes: supplier fit, MOQ/cost drivers, sample/QC steps, or quotation variables\n"
            "- Make the article read like a procurement-conversion page, not a generic guide\n"
            "- Include rigorous evaluation framework, inspection checklist, or decision matrix where relevant\n"
            "- Keep application context and buyer decision perspective visible even when discussing commercial details\n"
            f"- Treat the reader as a {search_stage or 'decision-stage'} buyer who is validating suppliers and shortlists\n"
            f"{role_hint}"
        )

    def _get_serp_role_guidance(self, serp_role: Optional[str]) -> str:
        """Add role-level writing direction so the article matches the exact SERP job."""
        guidance = {
            "application_fit": "- Focus on use-case fit, product application, and how to choose the right format for the formula or packaging scenario",
            "material_comparison": "- Focus on side-by-side trade-offs, compatibility, durability, cost, and scenario-based recommendation logic",
            "spec_selection": "- Focus on spec thresholds such as capacity, closure, neck finish, dosing, and material selection criteria",
            "supplier_evaluation": "- Focus on supplier fit, audit signals, qualification criteria, quote comparison, and shortlisting logic",
            "procurement_faq": "- Focus on concrete buyer questions around MOQ, lead time, samples, customization, QC, packaging, and shipping terms",
            "problem_risk": "- Focus on failure risks, mismatch scenarios, buyer mistakes, and how to avoid downstream sourcing or usage problems",
        }
        return guidance.get(serp_role or "", "- Keep the article tightly aligned to the exact search job implied by the keyword.")

    def _get_content_type_guidance(self, article_content_type: Optional[str]) -> str:
        """Build content-type-specific opening/closing guidance block for the prompt."""
        if not article_content_type or article_content_type == "general":
            return ""
        from src.services.content.content_type_templates import CONTENT_TYPE_TEMPLATES
        from src.models.seo_context import ArticleContentType
        try:
            ct = ArticleContentType(article_content_type)
        except ValueError:
            return ""
        template = CONTENT_TYPE_TEMPLATES.get(ct)
        if not template:
            return ""
        return (
            f"\n## CONTENT TYPE: {ct.value.upper()}\n"
            f"**Opening approach**: {template.opening_instruction}\n"
            f"**Closing approach**: {template.closing_instruction}\n"
            f"Follow the structural pattern for {ct.value} content — do not default to a generic blog post skeleton.\n"
        )

    def _format_products_for_prompt(self, products: list) -> str:
        """Format product examples for prompt readability."""
        if not products:
            return "None specified"

        formatted = []
        for product in products[:5]:
            if isinstance(product, dict):
                details = [
                    product.get("capacity"),
                    product.get("material"),
                    product.get("closure_type"),
                    product.get("use_case"),
                ]
                detail_text = ", ".join(value for value in details if value)
                formatted.append(f"{product.get('name', 'Unnamed product')} ({detail_text or 'catalog example'})")
            else:
                formatted.append(str(product))
        return "; ".join(formatted)

    def _get_page_type_requirements(
        self,
        page_type: Optional[str],
        category_context: dict,
        tag_context: dict,
        primary_catalog_context: dict,
    ) -> str:
        """Return page-type-specific output constraints."""
        landing_page = (
            primary_catalog_context.get("name")
            or category_context.get("name")
            or tag_context.get("name")
            or "the target catalog page"
        )
        landing_type = primary_catalog_context.get("type", "catalog")
        landing_reference = f"{landing_type} page for {landing_page}"
        requirements = {
            "category_support": f"""
- Explain how buyers should navigate and shortlist options inside {landing_page}
- Include a section that points readers to the relevant category or tag page as the next browsing step
- Cover key selection variables such as material, capacity, closure, decoration, and compliance
- Include at least one shortlist or buyer checklist block
- Make the CTA explain why the primary {landing_reference} is the best next step""",
            "product_selection": f"""
- Structure the article like a buyer selection guide, not a general blog post
- Include a comparison table for 2-4 product/spec options
- Explain which buyer scenario each option fits and where it fails
- Add a shortlist checklist covering MOQ, lead time, samples, customization, and QC questions
- End by routing readers to the primary {landing_reference} before isolated product links""",
            "spec_comparison": f"""
- Include at least one comparison/specification table
- Compare fit, trade-offs, and not-recommended scenarios instead of broad descriptions
- Highlight decision thresholds such as material compatibility, capacity range, closure fit, or decoration limits
- End with a concise recommendation framework for choosing between options
- The CTA should clarify whether the primary {landing_reference} or a mapped product page is the better next step""",
            "wholesale_faq": f"""
- Organize the article around actual buyer questions and direct answers
- Must include MOQ, lead time, sample policy, customization, packaging, and shipping guidance
- Use FAQ-style headings where appropriate
- Include a next-step CTA directing readers first to the primary {landing_reference}, then to supporting product pages when the buyer is already validating a shortlist""",
        }
        return requirements.get(page_type or "", "- Write as a commercial support article with concrete buying guidance.")

    def _build_faq_requirements(
        self,
        keyword: str,
        page_type: str,
        primary_catalog_context: dict,
        category_context: dict,
        tag_context: dict,
        decision_questions: List[str],
        products: List[dict],
    ) -> str:
        """Build FAQ instructions that tie answers back to buyer navigation."""
        primary = self._resolve_primary_cta_target(
            keyword=keyword,
            primary_catalog_context=primary_catalog_context,
            category_context=category_context,
            tag_context=tag_context,
            products=products,
        )
        questions = decision_questions[:4] or self._build_faq_template_questions(
            keyword=keyword,
            page_type=page_type,
            primary=primary,
            category_context=category_context,
            tag_context=tag_context,
            products=products,
        )
        primary_name = primary.get("name") or primary_catalog_context.get("name", "the recommended landing page")
        lines = ["- Include 3-5 FAQ items with direct answer-first responses"]
        for question in questions:
            lines.append(f"- Cover: {question}")
        lines.append(f"- At least one FAQ answer should tell readers when to browse {primary_name} as the next step")
        return "\n".join(lines)

    def _build_faq_template_questions(
        self,
        keyword: str,
        page_type: str,
        primary: dict,
        category_context: dict,
        tag_context: dict,
        products: List[dict],
    ) -> List[str]:
        """Provide stable FAQ templates for category, tag, and product routing."""
        primary_type = primary.get("type", "category")
        primary_name = primary.get("name") or category_context.get("name") or tag_context.get("name") or keyword
        first_product = products[0] if products else {}
        product_name = first_product.get("name", keyword)

        route_templates = {
            "category": [
                f"When should buyers browse the {primary_name} category instead of asking for a quote immediately?",
                f"Which specs, MOQ, and decoration options should buyers compare across the {primary_name} range?",
                f"How do buyers narrow the {primary_name} category into a workable shortlist?",
            ],
            "tag": [
                f"When should buyers use the {primary_name} tag page to narrow by material, feature, or application?",
                f"Which MOQ, lead time, and compliance checks matter most for {primary_name} options?",
                f"How do buyers move from the {primary_name} tag page to a shortlist of candidate products?",
            ],
            "product": [
                f"When is {product_name} specific enough to evaluate directly instead of browsing broader options first?",
                f"Which MOQ, sampling, and leak-test questions should buyers confirm for {product_name}?",
                f"When should buyers return from {product_name} to a category or tag page to compare alternatives?",
            ],
        }

        page_type_templates = {
            "wholesale_faq": [
                f"What MOQ, lead time, sample policy, and packaging terms apply to {keyword}?",
                f"Which supplier checks prevent delays or quality surprises when sourcing {keyword}?",
            ],
            "product_selection": [
                f"Which material, capacity, and closure combinations are the best fit for {keyword}?",
                f"What trade-offs should buyers compare before shortlisting {keyword}?",
            ],
            "spec_comparison": [
                f"Which spec differences matter most when comparing {keyword} options?",
                f"When does the lower-cost option become the wrong choice for {keyword}?",
            ],
            "category_support": [
                f"How should buyers compare the main options available for {keyword}?",
                f"What is the fastest way to shortlist {keyword} by use case, material, and closure?",
            ],
        }

        questions = route_templates.get(primary_type, []) + page_type_templates.get(page_type, [])
        deduped = []
        for question in questions:
            if question not in deduped:
                deduped.append(question)
        return deduped[:5]

    def _build_cta_requirements(
        self,
        primary_catalog_context: dict,
        category_context: dict,
        tag_context: dict,
        keyword: str,
        products: List[dict],
    ) -> str:
        """Describe the primary and secondary CTA flow for buyer-oriented articles."""
        primary = self._resolve_primary_cta_target(
            keyword=keyword,
            primary_catalog_context=primary_catalog_context,
            category_context=category_context,
            tag_context=tag_context,
            products=products,
        )
        primary_name = primary.get("name")
        primary_type = primary.get("type", "catalog")
        if not primary_name:
            return ""

        secondary_name = None
        if primary_type == "tag" and category_context.get("name"):
            secondary_name = category_context.get("name")
        elif primary_type == "category" and tag_context.get("name"):
            secondary_name = tag_context.get("name")
        elif primary_type == "product":
            secondary_name = tag_context.get("name") or category_context.get("name")
        elif products:
            secondary_name = products[0].get("name")

        template_map = {
            "category": [
                f"- Add a closing CTA section that tells readers to browse the broader category page: {primary_name}",
                f"- Position {primary_name} as the best next step when buyers still need to compare multiple formats, materials, or closures",
                "- Frame the category CTA as a shortlist-building step before sample requests or quotes",
            ],
            "tag": [
                f"- Add a closing CTA section that sends readers to the narrower tag/archive page: {primary_name}",
                f"- Explain that {primary_name} helps buyers filter by a specific material, feature, closure, or application angle",
                "- Frame the tag CTA as the fastest way to narrow down a shortlist before reviewing individual SKUs",
            ],
            "product": [
                f"- Add a closing CTA section that points directly to the shortlisted product page: {primary_name}",
                f"- Explain that {primary_name} is appropriate only when the buyer already has a narrow shortlist and needs to validate specs, MOQ, and sampling",
                "- Frame the product CTA as a validation step, not as a substitute for comparing alternatives",
            ],
        }
        lines = template_map.get(primary_type, [
            f"- Add a closing CTA section with a natural HTML link to the primary landing page: {primary_name}",
            f"- Explain why buyers should browse {primary_name} before making a final shortlist or quote request",
        ])
        if secondary_name:
            lines.append(f"- Add a secondary CTA path to {secondary_name} for readers who need a narrower material/spec option")
        if products:
            product_name = products[0].get("name")
            if product_name:
                lines.append(f"- When mentioning {product_name}, frame it as a shortlist example rather than the only recommended option")
        return "\n".join(lines)

    def _resolve_primary_cta_target(
        self,
        keyword: str,
        primary_catalog_context: dict,
        category_context: dict,
        tag_context: dict,
        products: List[dict],
    ) -> dict:
        """Choose whether the CTA should lead with category, tag, or product."""
        keyword_lower = (keyword or "").lower()
        if products:
            product = products[0]
            product_name = (product.get("name") or "").lower()
            product_terms = [
                str(product.get("capacity", "")).lower(),
                str(product.get("material", "")).lower(),
                str(product.get("closure_type", "")).lower(),
            ]
            if (
                product_name and product_name in keyword_lower
            ) or len([term for term in product_terms if term and term in keyword_lower]) >= 2:
                return {
                    "type": "product",
                    "name": product.get("name"),
                    "url": product.get("url"),
                }

        if primary_catalog_context.get("name"):
            return {
                "type": primary_catalog_context.get("type", "catalog"),
                "name": primary_catalog_context.get("name"),
                "url": primary_catalog_context.get("url"),
            }

        if tag_context.get("name"):
            return {"type": "tag", "name": tag_context.get("name"), "url": tag_context.get("url")}
        if category_context.get("name"):
            return {"type": "category", "name": category_context.get("name"), "url": category_context.get("url")}
        if products:
            return {"type": "product", "name": products[0].get("name"), "url": products[0].get("url")}
        return {}
    
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
