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
        catalog_note = (
            f"Primary taxonomy: {ctx.primary_taxonomy_name} ({ctx.primary_taxonomy_type})"
            if ctx.primary_taxonomy_name
            else ""
        )

        return (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"Title: {title}\n"
            f"Target keyword: {keyword}\n"
            f"{page_type_note}\n"
            f"{catalog_note}\n\n"
            f"Content type signals:\n{type_hints}\n\n"
            f"Generate 4–6 outline sections appropriate for this article's intent."
        )
