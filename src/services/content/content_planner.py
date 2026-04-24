"""
ContentPlannerService

Classifies article content type and generates a tailored section outline via a
single JSON-mode LLM call. Called from jobs.py between _ensure_catalog_outline()
and ContentCreatorAgent.execute() — enriches SEOContext in-place, non-raising.
"""

import json
import logging
from typing import Optional

from pydantic import BaseModel, ValidationError, field_validator

from src.models.seo_context import SEOContext, ArticleContentType
from src.services.content.content_type_templates import CONTENT_TYPE_TEMPLATES

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.75


class PlannerLLMOutput(BaseModel):
    """Pydantic model for validating the LLM JSON response from ContentPlannerService."""
    content_type: ArticleContentType
    confidence: float
    outline: list  # validated downstream

    @field_validator("content_type", mode="before")
    @classmethod
    def coerce_content_type(cls, v):
        """Coerce invalid/unknown content_type strings to GENERAL instead of raising."""
        try:
            return ArticleContentType(v)
        except (ValueError, KeyError):
            return ArticleContentType.GENERAL


class ContentPlannerService:
    """
    Classifies article content type and generates a tailored section outline.
    Called from jobs.py between _ensure_catalog_outline and ContentCreatorAgent.execute().

    Uses a single JSON-mode LLM call (response_format={"type": "json_object"}) via the
    existing AIProviderInterface — no LangChain chains involved.
    """

    SYSTEM_PROMPT = (
        "You are an SEO content strategist. Classify the article intent and "
        "generate a section outline. Respond ONLY with valid JSON matching this schema:\n"
        "{\n"
        '  "content_type": "<how_to|listicle|comparison|review|pricing|general>",\n'
        '  "confidence": <0.0-1.0>,\n'
        '  "outline": [\n'
        "    {\n"
        '      "title": "<H2 section title>",\n'
        '      "section_type": "<step|list_item|comparison|verdict|faq|cta|prerequisites|etc>",\n'
        '      "key_points": ["<point 1>", "<point 2>"],\n'
        '      "writing_notes": "<specific instruction for the writer of this section>"\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    def __init__(self, ai_provider):
        self.ai_provider = ai_provider

    async def plan(self, seo_context: SEOContext) -> None:
        """
        Enriches seo_context in-place with article_content_type, confidence, and planned_outline.
        Non-raising — logs warning and returns on any failure (LLM error, JSON error, validation error).
        """
        title = seo_context.selected_title or seo_context.topic_title
        keyword = seo_context.target_keyword

        prompt = self._build_prompt(title, keyword, seo_context)

        try:
            raw = await self.ai_provider.generate_text(
                prompt,
                temperature=0.2,
                max_tokens=900,
                response_format={"type": "json_object"}
            )
            parsed = PlannerLLMOutput.model_validate(json.loads(raw))

            # Apply confidence threshold — override to GENERAL if below threshold
            if parsed.confidence < CONFIDENCE_THRESHOLD:
                logger.info(
                    f"ContentPlanner: confidence={parsed.confidence:.2f} below threshold "
                    f"{CONFIDENCE_THRESHOLD} — overriding type '{parsed.content_type.value}' → general"
                )
                seo_context.article_content_type = ArticleContentType.GENERAL
            else:
                seo_context.article_content_type = parsed.content_type

            seo_context.article_content_type_confidence = parsed.confidence
            seo_context.planned_outline = parsed.outline

            logger.info(
                f"ContentPlanner: type={seo_context.article_content_type.value} "
                f"confidence={parsed.confidence:.2f} "
                f"sections={len(parsed.outline)}"
            )

        except Exception as exc:
            logger.warning(f"ContentPlanner LLM call failed: {exc}. Outline will use fallback.")

    def _build_prompt(self, title: str, keyword: str, ctx: SEOContext) -> str:
        """Build the classification prompt with template type hints and article context."""
        type_hints = "\n".join(
            f"- {t.value}: {CONTENT_TYPE_TEMPLATES[t].opening_instruction[:80]}..."
            for t in ArticleContentType
            if t != ArticleContentType.GENERAL
        )
        page_type_note = f"Page type context: {ctx.page_type}" if ctx.page_type else ""
        lane_note = (
            f"Content lane: {ctx.content_lane}. "
            f"Search stage: {ctx.search_stage or 'unspecified'}."
            if ctx.content_lane
            else ""
        )
        role_note = f"SERP role: {ctx.serp_role}." if ctx.serp_role else ""
        catalog_note = (
            f"Primary taxonomy: {ctx.primary_taxonomy_name} ({ctx.primary_taxonomy_type})"
            if ctx.primary_taxonomy_name
            else ""
        )
        lane_guidance = self._build_lane_guidance(ctx.content_lane, ctx.serp_role)

        return (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"Title: {title}\n"
            f"Target keyword: {keyword}\n"
            f"{page_type_note}\n"
            f"{lane_note}\n"
            f"{role_note}\n"
            f"{catalog_note}\n\n"
            f"{lane_guidance}\n\n"
            f"Content type signals:\n{type_hints}\n\n"
            f"Generate 4–6 outline sections appropriate for this article's intent."
        )

    def _build_lane_guidance(self, content_lane: Optional[str], serp_role: Optional[str]) -> str:
        """Give the planner role-specific structure constraints before outline selection."""
        role_guidance = {
            "application_fit": "Prioritize application scenarios, use-case mapping, and suitability criteria.",
            "material_comparison": "Prioritize side-by-side trade-offs, compatibility, and scenario-specific recommendations.",
            "spec_selection": "Prioritize spec thresholds, closure/material/capacity criteria, and decision checkpoints.",
            "supplier_evaluation": "Prioritize supplier qualification, shortlist logic, quote comparison, and audit criteria.",
            "procurement_faq": "Prioritize direct buyer questions around MOQ, lead time, sampling, customization, QC, and shipping.",
            "problem_risk": "Prioritize mistakes, risks, mismatch scenarios, and failure-prevention guidance.",
        }.get(serp_role or "", "Keep the outline tightly aligned to the actual search job behind the keyword.")
        if content_lane == "traffic_entry":
            return (
                "Lane guidance: This page is a search-entry page. Open from scenario, comparison, "
                "application fit, or risk framing. Avoid encyclopedia tone and avoid defaulting to "
                f"MOQ/lead-time-first structure unless the query explicitly demands it. {role_guidance}"
            )
        return (
            "Lane guidance: This page is a procurement-conversion page. Open from buyer decision stakes, "
            "supplier qualification, MOQ/cost drivers, sample/QC process, or quotation variables. "
            f"Keep the content commercially useful rather than generic. {role_guidance}"
        )
