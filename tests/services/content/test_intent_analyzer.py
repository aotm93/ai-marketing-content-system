"""
Tests for Search Intent Analyzer
"""

import pytest
from src.services.content.intent_analyzer import (
    SearchIntentAnalyzer, UserIntent, IntentSignal
)


class TestSearchIntentAnalyzer:
    """Test intent-based title generation"""

    def test_analyze_problem_solving_intent(self):
        """Should detect problem-solving intent from keywords"""
        analyzer = SearchIntentAnalyzer()

        result = analyzer.analyze_intent(
            "HDPE cracking in cold weather",
            related_keywords=["prevent", "fix", "solution"]
        )

        assert result.intent == UserIntent.PROBLEM_SOLVING
        assert result.confidence > 0.7
        assert "cracking" in result.semantic_context

    def test_analyze_technical_specification_intent(self):
        """Should detect technical specification intent"""
        analyzer = SearchIntentAnalyzer()

        result = analyzer.analyze_intent(
            "HDPE chemical resistance properties",
            related_keywords=["resistance", "properties", "specifications"]
        )

        assert result.intent == UserIntent.SPECIFICATION
        assert result.confidence > 0.7

    def test_analyze_comparison_intent(self):
        """Should detect comparison intent"""
        analyzer = SearchIntentAnalyzer()

        result = analyzer.analyze_intent(
            "HDPE vs LDPE for outdoor applications",
            related_keywords=["versus", "compared", "difference"]
        )

        assert result.intent == UserIntent.COMPARISON
        assert result.confidence > 0.8

    def test_generate_problem_solving_title(self):
        """Should generate specific problem-solving title, not generic"""
        analyzer = SearchIntentAnalyzer()

        signal = IntentSignal(
            keyword="HDPE cracking in cold weather",
            intent=UserIntent.PROBLEM_SOLVING,
            confidence=0.9,
            semantic_context=["cracking", "cold", "prevent"]
        )

        title = analyzer.generate_intent_based_title(signal)

        # Should NOT contain generic phrases
        assert "What You Need to Know" not in title
        assert "Review" not in title
        assert "Best" not in title

        # Should contain specific problem context
        assert "cracking" in title.lower() or "crack" in title.lower()
        assert "cold" in title.lower()

    def test_generate_technical_title(self):
        """Should generate technical deep-dive title"""
        analyzer = SearchIntentAnalyzer()

        signal = IntentSignal(
            keyword="HDPE chemical resistance",
            intent=UserIntent.SPECIFICATION,
            confidence=0.85,
            semantic_context=["chemical", "resistance", "properties"]
        )

        title = analyzer.generate_intent_based_title(signal)

        # Should focus on technical depth
        assert "chemical resistance" in title.lower()
        assert any(word in title.lower() for word in ["properties", "analysis", "data", "specifications"])

    def test_generate_comparison_title(self):
        """Should generate specific comparison title"""
        analyzer = SearchIntentAnalyzer()

        signal = IntentSignal(
            keyword="HDPE vs LDPE outdoor",
            intent=UserIntent.COMPARISON,
            confidence=0.9,
            semantic_context=["outdoor", "applications", "durability"]
        )

        title = analyzer.generate_intent_based_title(signal)

        # Should be specific comparison, not generic
        assert "HDPE" in title and "LDPE" in title
        assert "outdoor" in title.lower()
        assert "Which is Better?" not in title  # Avoid generic endings

    def test_analyze_buying_guide_intent(self):
        """Should detect buying/supplier intent from commercial keywords"""
        analyzer = SearchIntentAnalyzer()

        result = analyzer.analyze_intent(
            "plastic bottles wholesale supplier",
            related_keywords=["moq", "quote", "lead time"]
        )

        assert result.intent == UserIntent.BUYING_GUIDE
        assert result.confidence > 0.7

    def test_generate_buying_guide_title(self):
        """Should generate commercial titles with concrete buyer value"""
        analyzer = SearchIntentAnalyzer()

        signal = IntentSignal(
            keyword="plastic bottles wholesale supplier",
            intent=UserIntent.BUYING_GUIDE,
            confidence=0.9,
            semantic_context=["plastic", "bottles", "wholesale", "supplier"]
        )

        title = analyzer.generate_intent_based_title(signal)

        assert "plastic bottles wholesale supplier" in title.lower()
        assert any(word in title.lower() for word in ["moq", "lead time", "certifications", "pricing"])
        assert "what you need to know" not in title.lower()

    def test_expand_semantic_keywords(self):
        """Should expand keywords based on semantic context"""
        analyzer = SearchIntentAnalyzer()

        expanded = analyzer.expand_semantic_keywords(
            "HDPE pipe",
            max_expansions=5
        )

        # Should generate related technical terms
        assert len(expanded) > 0
        assert all(isinstance(k, str) for k in expanded)
        # Should not just add generic suffixes
        assert not any("review" in k.lower() for k in expanded)

    def test_avoid_generic_patterns(self):
        """Should avoid generic SEO patterns"""
        analyzer = SearchIntentAnalyzer()

        signal = IntentSignal(
            keyword="plastic materials",
            intent=UserIntent.SPECIFICATION,
            confidence=0.8,
            semantic_context=["plastic", "materials"]
        )

        title = analyzer.generate_intent_based_title(signal)

        # Must NOT contain these generic patterns
        forbidden = ["What You Need to Know", "Best", "Review", "Top", "Ultimate Guide"]
        assert not any(pattern in title for pattern in forbidden)

    def test_route_product_head_query_to_procurement_lane(self):
        analyzer = SearchIntentAnalyzer()

        route = analyzer.route_content_lane(
            "dropper bottle 100ml",
            catalog_context={
                "page_type": "wholesale_faq",
                "supporting_products": [{"name": "100ml Dropper Bottle"}],
                "target_category_name": "Dropper Bottles",
            },
        )

        assert route.content_lane == "procurement_conversion"
        assert route.search_stage == "decision"
        assert route.serp_role in {"supplier_evaluation", "procurement_faq"}
        assert route.confidence >= 0.7

    def test_route_comparison_query_to_traffic_entry_lane(self):
        analyzer = SearchIntentAnalyzer()

        route = analyzer.route_content_lane(
            "glass vs pet dropper bottle for serum",
            catalog_context={
                "page_type": "spec_comparison",
                "target_category_name": "Dropper Bottles",
            },
        )

        assert route.content_lane == "traffic_entry"
        assert route.search_stage == "consideration"
        assert route.serp_role == "material_comparison"
        assert route.signal_scores["traffic"] > route.signal_scores["commercial"]
