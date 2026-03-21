"""
Integration test for ContentCreatorAgent with ProfessionalContentWriter
"""

import pytest
from src.agents.content_creator import ContentCreatorAgent
from src.services.content.professional_writer import ProfessionalContentWriter


class TestContentCreatorIntegration:
    """Test that ContentCreatorAgent uses professional prompts"""

    def test_build_prompt_avoids_generic_phrases(self):
        """Should build prompts without generic phrases"""
        agent = ContentCreatorAgent()

        # Simulate building a prompt for problem-solving content
        prompt = agent._build_synchronized_prompt(
            keyword="HDPE cracking",
            title_must_use="Preventing Cracking in HDPE: Root Causes",
            hook_type="problem",
            products=[],
            research_context={},
            outline={
                "sections": [{
                    "title": "Root Causes",
                    "content_type": "problem_statement",
                    "key_points": ["thermal stress", "material properties"]
                }]
            },
            page_type="category_support",
            category_context={},
            tag_context={},
            primary_catalog_context={},
            decision_questions=[],
            commercial_facts=[],
            supporting_tags=[],
            semantic_keywords=[],
            internal_links=[]
        )

        # Must NOT contain generic phrases
        forbidden = [
            "comprehensive guide",
            "everything you need to know",
            "in this article we will"
        ]
        prompt_lower = prompt.lower()
        assert not any(phrase in prompt_lower for phrase in forbidden)

    def test_build_prompt_requires_decision_value_for_supplier_content(self):
        """Should force commercially useful content instead of generic copy"""
        agent = ContentCreatorAgent()

        prompt = agent._build_synchronized_prompt(
            keyword="plastic bottles wholesale supplier",
            title_must_use="Plastic Bottles Wholesale Supplier: MOQ, Lead Time, Certifications, and Audit Questions",
            hook_type="problem",
            products=[],
            research_context={},
            outline={},
            page_type="wholesale_faq",
            category_context={},
            tag_context={},
            primary_catalog_context={},
            decision_questions=[],
            commercial_facts=[],
            supporting_tags=[],
            semantic_keywords=[],
            internal_links=[]
        )

        prompt_lower = prompt.lower()
        assert "moq, lead time, customization, compliance, quality control, and quotation factors" in prompt_lower
        assert "rigorous evaluation framework, inspection checklist, or decision matrix" in prompt_lower

    def test_build_prompt_includes_category_and_product_context(self):
        """Should include catalog-backed category and product guidance."""
        agent = ContentCreatorAgent()

        prompt = agent._build_synchronized_prompt(
            keyword="30ml pet spray bottle wholesale",
            title_must_use="30ml PET Spray Bottle Wholesale: MOQ, Decoration, and Lead Time",
            hook_type="how_to",
            products=[{
                "name": "30ml PET Fine Mist Spray Bottle",
                "capacity": "30ml",
                "material": "PET",
                "closure_type": "Fine Mist Spray",
                "use_case": "Cosmetic",
                "url": "https://example.com/product/30ml-pet-fine-mist-spray-bottle"
            }],
            research_context={},
            outline={},
            page_type="product_selection",
            category_context={
                "name": "Spray Bottles",
                "slug": "spray-bottles",
                "url": "https://example.com/category/spray-bottles"
            },
            tag_context={
                "name": "PET",
                "slug": "pet",
                "url": "https://example.com/tag/pet"
            },
            primary_catalog_context={
                "type": "tag",
                "name": "PET",
                "slug": "pet",
                "url": "https://example.com/tag/pet"
            },
            decision_questions=["What MOQ and decoration options apply to spray bottles?"],
            commercial_facts=["30ml PET Fine Mist Spray Bottle references MOQ 10000."],
            supporting_tags=["PET", "Fine Mist", "Cosmetic Packaging"],
            semantic_keywords=[],
            internal_links=[]
        )

        prompt_lower = prompt.lower()
        assert "target category" in prompt_lower
        assert "target tag page" in prompt_lower
        assert "primary landing page" in prompt_lower
        assert "supporting products / examples" in prompt_lower
        assert "decision questions the article must answer" in prompt_lower
        assert "faq requirements" in prompt_lower
        assert "cta requirements" in prompt_lower
        assert "points directly to the shortlisted product page" in prompt_lower
        assert "commercial facts to weave into the article" in prompt_lower
        assert "comparison table" in prompt_lower

    def test_build_prompt_uses_route_specific_faq_templates_when_missing_questions(self):
        """Should fall back to product/category/tag FAQ templates instead of generic FAQs."""
        agent = ContentCreatorAgent()

        prompt = agent._build_synchronized_prompt(
            keyword="30ml pet fine mist spray bottle wholesale",
            title_must_use="30ml PET Fine Mist Spray Bottle Wholesale: MOQ, Lead Time, and Samples",
            hook_type="how_to",
            products=[{
                "name": "30ml PET Fine Mist Spray Bottle",
                "capacity": "30ml",
                "material": "PET",
                "closure_type": "Fine Mist Spray",
                "use_case": "Cosmetic",
                "url": "https://example.com/product/30ml-pet-fine-mist-spray-bottle"
            }],
            research_context={},
            outline={},
            page_type="wholesale_faq",
            category_context={
                "name": "Spray Bottles",
                "slug": "spray-bottles",
                "url": "https://example.com/category/spray-bottles"
            },
            tag_context={
                "name": "PET",
                "slug": "pet",
                "url": "https://example.com/tag/pet"
            },
            primary_catalog_context={
                "type": "tag",
                "name": "PET",
                "slug": "pet",
                "url": "https://example.com/tag/pet"
            },
            decision_questions=[],
            commercial_facts=[],
            supporting_tags=["PET", "Fine Mist"],
            semantic_keywords=[],
            internal_links=[]
        )

        prompt_lower = prompt.lower()
        assert "when is 30ml pet fine mist spray bottle specific enough to evaluate directly" in prompt_lower
        assert "what moq, lead time, sample policy, and packaging terms apply" in prompt_lower
