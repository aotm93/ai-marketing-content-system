from src.services.website_analyzer import WebsiteAnalyzer


class TestWebsiteAnalyzer:
    """Tests for website content analysis helpers."""

    def test_extract_product_categories_keeps_full_noun_phrase(self):
        analyzer = WebsiteAnalyzer(wordpress_client=None)

        categories = analyzer._extract_product_categories(
            titles=["How to Choose Plastic Bottles for Skincare Packaging"],
            contents=[
                "Our cosmetic bottles and cream jars support wholesale orders. "
                "Plastic bottles need compatibility and dispensing tests."
            ]
        )

        assert "plastic bottles" in categories
        assert "cream jars" in categories
        assert "plastic" not in categories
        assert "cream" not in categories

    def test_extract_product_categories_filters_pronoun_fragments(self):
        analyzer = WebsiteAnalyzer(wordpress_client=None)

        categories = analyzer._extract_product_categories(
            titles=["How to Choose Your Bottles"],
            contents=["Your bottles should match filling speed and cap torque requirements."]
        )

        assert "your bottles" not in categories

    def test_extract_product_categories_filters_component_only_heads(self):
        analyzer = WebsiteAnalyzer(wordpress_client=None)

        categories = analyzer._extract_product_categories(
            titles=["Understanding White Pumps"],
            contents=["White pumps and caps are discussed, but the publishable entity should remain the bottle family."]
        )

        assert "white pumps" not in categories
        assert "pumps" not in categories
