"""
Tests for route-aware keyword balancing.
"""

from src.services.keyword_strategy import ContentAwareKeywordGenerator
from src.services.product_knowledge import CategoryInsight, ProductInsight
from src.services.website_analyzer import WebsiteProfile


class TestKeywordStrategyRouting:
    """Validate route coverage balancing at topic selection time."""

    def test_balance_route_coverage_boosts_underrepresented_routes(self):
        profile = WebsiteProfile(
            product_categories=["spray bottles"],
            industry_terms=["wholesale", "PET", "cosmetic packaging"],
            content_themes=["customization"],
            target_audience="B2B wholesale buyers",
            business_type="packaging supplier",
            sample_keywords=["30ml pet spray bottle"],
            customer_pain_points=["comparing MOQ and lead time"],
            category_details=[
                CategoryInsight(
                    id=1,
                    name="Spray Bottles",
                    slug="spray-bottles",
                    url="https://example.com/category/spray-bottles",
                    product_count=12,
                )
            ],
            tag_details=[
                CategoryInsight(id=11, name="PET", slug="pet", url="https://example.com/tag/pet", product_count=8)
            ],
            product_records=[
                ProductInsight(
                    id=1,
                    name="30ml PET Fine Mist Spray Bottle",
                    slug="30ml-pet-fine-mist-spray-bottle",
                    url="https://example.com/product/30ml-pet-fine-mist-spray-bottle",
                    category_names=["Spray Bottles"],
                    tag_names=["PET"],
                    material="PET",
                    capacity="30ml",
                    closure_type="Fine Mist Spray",
                    use_case="Cosmetic",
                    moq="10000",
                    lead_time="15-20 days",
                )
            ],
        )

        generator = ContentAwareKeywordGenerator(profile)
        candidates = [
            generator._build_candidate(
                keyword="spray bottles wholesale supplier",
                intent="commercial",
                journey_stage="consideration",
                category="spray bottles",
                semantic_group="cat",
            ),
            generator._build_candidate(
                keyword="pet packaging wholesale",
                intent="commercial",
                journey_stage="consideration",
                category="PET",
                semantic_group="tag",
            ),
        ]
        pre_scores = {candidate.route_target_type: candidate.routing_score for candidate in candidates}

        balanced = generator.balance_route_coverage(
            candidates=candidates,
            selected_keywords=["spray bottles wholesale", "spray bottles supplier"],
        )
        post_scores = {candidate.route_target_type: candidate.routing_score for candidate in balanced}

        assert post_scores["tag"] > pre_scores["tag"]
        assert post_scores["tag"] >= post_scores["category"]

    def test_balance_route_coverage_uses_7_day_distribution(self):
        profile = WebsiteProfile(
            product_categories=["spray bottles"],
            industry_terms=["wholesale", "PET", "cosmetic packaging"],
            content_themes=["customization"],
            target_audience="B2B wholesale buyers",
            business_type="packaging supplier",
            sample_keywords=["30ml pet spray bottle"],
            customer_pain_points=["comparing MOQ and lead time"],
            category_details=[
                CategoryInsight(
                    id=1,
                    name="Spray Bottles",
                    slug="spray-bottles",
                    url="https://example.com/category/spray-bottles",
                    product_count=12,
                )
            ],
            tag_details=[
                CategoryInsight(id=11, name="PET", slug="pet", url="https://example.com/tag/pet", product_count=8)
            ],
            product_records=[
                ProductInsight(
                    id=1,
                    name="30ml PET Fine Mist Spray Bottle",
                    slug="30ml-pet-fine-mist-spray-bottle",
                    url="https://example.com/product/30ml-pet-fine-mist-spray-bottle",
                    category_names=["Spray Bottles"],
                    tag_names=["PET"],
                    material="PET",
                    capacity="30ml",
                    closure_type="Fine Mist Spray",
                    use_case="Cosmetic",
                    moq="10000",
                    lead_time="15-20 days",
                )
            ],
        )

        generator = ContentAwareKeywordGenerator(profile)
        category_candidate = generator._build_candidate(
            keyword="spray bottles wholesale supplier",
            intent="commercial",
            journey_stage="consideration",
            category="spray bottles",
            semantic_group="cat",
        )
        tag_candidate = generator._build_candidate(
            keyword="pet packaging wholesale",
            intent="commercial",
            journey_stage="consideration",
            category="PET",
            semantic_group="tag",
        )
        pre_scores = {
            category_candidate.route_target_type: category_candidate.routing_score,
            tag_candidate.route_target_type: tag_candidate.routing_score,
        }

        balanced = generator.balance_route_coverage(
            candidates=[category_candidate, tag_candidate],
            selected_keywords=["spray bottles wholesale", "pet packaging wholesale"],
            recent_keywords_7d=[
                "spray bottles wholesale",
                "spray bottles supplier",
                "spray bottles moq",
                "spray bottles wholesale manufacturer",
            ],
        )
        post_scores = {candidate.route_target_type: candidate.routing_score for candidate in balanced}

        assert post_scores["tag"] > pre_scores["tag"]
        assert post_scores["tag"] - pre_scores["tag"] > post_scores["category"] - pre_scores["category"]
