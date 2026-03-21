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
            semantic_keywords=[],
            internal_links=[]
        )

        prompt_lower = prompt.lower()
        assert "moq, lead time, customization, compliance, quality control, and quotation factors" in prompt_lower
        assert "rigorous evaluation framework, inspection checklist, or decision matrix" in prompt_lower
