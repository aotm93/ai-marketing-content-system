"""
Tests for Professional Content Writer
"""

import pytest
from src.services.content.professional_writer import ProfessionalContentWriter
from src.services.content.intent_analyzer import IntentSignal, UserIntent
from src.models.content_intelligence import OutlineSection, ContentType


class TestProfessionalContentWriter:
    """Test professional content generation"""

    def test_problem_solving_prompt_avoids_generic_phrases(self):
        """Should generate specific problem-solving prompts"""
        writer = ProfessionalContentWriter()

        signal = IntentSignal(
            keyword="HDPE cracking in cold weather",
            intent=UserIntent.PROBLEM_SOLVING,
            confidence=0.9,
            semantic_context=["cracking", "cold", "weather"]
        )

        section = OutlineSection(
            title="Root Causes of Cold Weather Cracking",
            content_type=ContentType.PROBLEM_STATEMENT,
            key_points=["thermal stress", "material properties"],
            estimated_word_count=400,
            order=1
        )

        prompt = writer.build_section_prompt(section, signal)

        # Must NOT contain generic phrases
        forbidden = [
            "comprehensive guide",
            "everything you need to know",
            "in this article",
            "let's explore"
        ]
        assert not any(phrase in prompt.lower() for phrase in forbidden)

        # Must contain specific requirements
        assert "root cause" in prompt.lower() or "cause" in prompt.lower()
        assert "data" in prompt.lower() or "specific" in prompt.lower()

    def test_technical_spec_prompt_requires_depth(self):
        """Should require technical depth, not basic explanations"""
        writer = ProfessionalContentWriter()

        signal = IntentSignal(
            keyword="HDPE chemical resistance",
            intent=UserIntent.SPECIFICATION,
            confidence=0.85,
            semantic_context=["chemical", "resistance"]
        )

        section = OutlineSection(
            title="Chemical Resistance Properties",
            content_type=ContentType.DATA_ANALYSIS,
            key_points=["resistance data", "test methods"],
            estimated_word_count=500,
            order=2
        )

        prompt = writer.build_section_prompt(section, signal)

        # Must require technical content
        assert any(word in prompt.lower() for word in ["technical", "data", "specific", "parameter"])
        # Must avoid basic explanations
        assert "what is" not in prompt.lower()

    def test_get_content_requirements_for_problem_solving(self):
        """Should return specific requirements for problem-solving content"""
        writer = ProfessionalContentWriter()

        reqs = writer.get_content_requirements(UserIntent.PROBLEM_SOLVING)

        assert "root_cause_analysis" in reqs
        assert "actionable_solutions" in reqs
        assert reqs["avoid_generic"] is True
