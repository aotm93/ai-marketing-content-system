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
