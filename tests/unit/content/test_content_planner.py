"""Unit tests for ContentPlannerService and content type templates."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.models.seo_context import ArticleContentType, SEOContext
from src.services.content.content_type_templates import CONTENT_TYPE_TEMPLATES


class TestSEOContextBackwardCompat:
    def test_existing_fields_only_no_validation_error(self):
        ctx = SEOContext(source="GSC", target_keyword="packaging solutions", topic_title="Packaging Guide")
        assert ctx.article_content_type is None
        assert ctx.article_content_type_confidence is None
        assert ctx.planned_outline == []
        assert ctx.content_lane == "procurement_conversion"

    def test_new_fields_accepted(self):
        ctx = SEOContext(
            source="GSC",
            target_keyword="kw",
            topic_title="T",
            article_content_type=ArticleContentType.HOW_TO,
            article_content_type_confidence=0.9,
            planned_outline=[{"title": "Step 1", "section_type": "step"}],
            content_lane="traffic_entry",
            search_stage="consideration",
        )
        assert ctx.article_content_type == ArticleContentType.HOW_TO
        assert ctx.article_content_type_confidence == 0.9
        assert len(ctx.planned_outline) == 1
        assert ctx.content_lane == "traffic_entry"
        assert ctx.search_stage == "consideration"


class TestContentTypeTemplates:
    def test_all_types_present(self):
        for ct in ArticleContentType:
            assert ct in CONTENT_TYPE_TEMPLATES, f"Missing template for {ct}"

    def test_each_template_non_empty(self):
        for ct, tmpl in CONTENT_TYPE_TEMPLATES.items():
            assert tmpl.opening_instruction, f"{ct} opening_instruction is empty"
            assert tmpl.closing_instruction, f"{ct} closing_instruction is empty"
            assert len(tmpl.sections) >= 3, f"{ct} has fewer than 3 sections"

    def test_each_section_has_writing_mode(self):
        for ct, tmpl in CONTENT_TYPE_TEMPLATES.items():
            for section in tmpl.sections:
                assert section.writing_mode, f"{ct} section '{section.name}' missing writing_mode"
                assert section.section_type, f"{ct} section '{section.name}' missing section_type"


class TestContentPlannerService:
    def _make_seo_context(self):
        return SEOContext(source="GSC", target_keyword="hdpe bottle packaging", topic_title="HDPE Bottle Guide")

    @pytest.mark.asyncio
    async def test_successful_classification(self):
        from src.services.content.content_planner import ContentPlannerService

        mock_provider = AsyncMock()
        mock_provider.generate_text = AsyncMock(return_value='{"content_type": "how_to", "confidence": 0.9, "outline": [{"title": "Step 1", "section_type": "step", "key_points": ["point"], "writing_notes": "note"}]}')
        svc = ContentPlannerService(mock_provider)
        ctx = self._make_seo_context()
        await svc.plan(ctx)
        assert ctx.article_content_type == ArticleContentType.HOW_TO
        assert ctx.article_content_type_confidence == 0.9
        assert len(ctx.planned_outline) == 1

    @pytest.mark.asyncio
    async def test_low_confidence_falls_back_to_general(self):
        from src.services.content.content_planner import ContentPlannerService

        mock_provider = AsyncMock()
        mock_provider.generate_text = AsyncMock(return_value='{"content_type": "review", "confidence": 0.6, "outline": []}')
        svc = ContentPlannerService(mock_provider)
        ctx = self._make_seo_context()
        await svc.plan(ctx)
        assert ctx.article_content_type == ArticleContentType.GENERAL

    @pytest.mark.asyncio
    async def test_llm_exception_does_not_raise(self):
        from src.services.content.content_planner import ContentPlannerService

        mock_provider = AsyncMock()
        mock_provider.generate_text = AsyncMock(side_effect=RuntimeError("API timeout"))
        svc = ContentPlannerService(mock_provider)
        ctx = self._make_seo_context()
        await svc.plan(ctx)
        assert ctx.article_content_type is None

    @pytest.mark.asyncio
    async def test_malformed_json_does_not_raise(self):
        from src.services.content.content_planner import ContentPlannerService

        mock_provider = AsyncMock()
        mock_provider.generate_text = AsyncMock(return_value="not valid json {{{{")
        svc = ContentPlannerService(mock_provider)
        ctx = self._make_seo_context()
        await svc.plan(ctx)
        assert ctx.article_content_type is None

    def test_build_prompt_includes_content_lane_guidance(self):
        from src.services.content.content_planner import ContentPlannerService

        svc = ContentPlannerService(MagicMock())
        ctx = SEOContext(
            source="GSC",
            target_keyword="dropper bottle material for essential oils",
            topic_title="Dropper Bottle Material Selection",
            content_lane="traffic_entry",
            search_stage="consideration",
        )
        prompt = svc._build_prompt(ctx.topic_title, ctx.target_keyword, ctx)
        assert "Content lane: traffic_entry" in prompt
        assert "search-entry page" in prompt


class TestContentCreatorAgentIntegration:
    """Verify ContentCreatorAgent consumes new SEOContext fields without error."""

    def test_build_synchronized_prompt_with_content_type(self):
        from src.agents.content_creator import ContentCreatorAgent

        agent = ContentCreatorAgent()
        prompt = agent._build_synchronized_prompt(
            keyword="hdpe bottles",
            title_must_use="How to Choose HDPE Bottles",
            hook_type=None,
            products=[],
            research_context={},
            outline={},
            page_type="category_support",
            category_context={},
            tag_context={},
            primary_catalog_context={},
            decision_questions=[],
            commercial_facts=[],
            supporting_tags=[],
            content_lane="traffic_entry",
            content_lane_confidence=0.82,
            search_stage="consideration",
            semantic_keywords=[],
            internal_links=[],
            article_content_type="how_to",
            planned_outline=[{"title": "Step 1: Assess Needs", "section_type": "step", "key_points": ["point"], "writing_notes": "numbered list"}],
        )
        assert "CONTENT TYPE: HOW_TO" in prompt
        assert "Lane: traffic_entry" in prompt
        assert "Step 1: Assess Needs" in prompt
        assert "numbered list" in prompt

    def test_build_synchronized_prompt_fallback_to_generic_outline(self):
        from src.agents.content_creator import ContentCreatorAgent

        agent = ContentCreatorAgent()
        prompt = agent._build_synchronized_prompt(
            keyword="packaging",
            title_must_use="Packaging Guide",
            hook_type=None,
            products=[],
            research_context={},
            outline={"hook": "The answer is here", "sections": [{"title": "Overview", "content_type": "general", "key_points": []}]},
            page_type="category_support",
            category_context={},
            tag_context={},
            primary_catalog_context={},
            decision_questions=[],
            commercial_facts=[],
            supporting_tags=[],
            content_lane="procurement_conversion",
            content_lane_confidence=0.88,
            search_stage="decision",
            semantic_keywords=[],
            internal_links=[],
            article_content_type=None,
            planned_outline=[],
        )
        assert "The answer is here" in prompt
        assert "Lane: procurement_conversion" in prompt

    def test_to_content_creator_task_includes_new_fields(self):
        ctx = SEOContext(
            source="GSC",
            target_keyword="kw",
            topic_title="T",
            article_content_type=ArticleContentType.PRICING,
            planned_outline=[{"title": "Price Range", "section_type": "price_range"}],
            content_lane="traffic_entry",
            search_stage="consideration",
        )
        task = ctx.to_content_creator_task()
        assert task["article_content_type"] == "pricing"
        assert len(task["planned_outline"]) == 1
        assert task["content_lane"] == "traffic_entry"
        assert task["search_stage"] == "consideration"
