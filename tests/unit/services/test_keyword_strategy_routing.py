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

    def test_product_descriptor_is_compact_and_non_repetitive(self):
        profile = WebsiteProfile(
            product_categories=["foam bottles"],
            industry_terms=["wholesale"],
            content_themes=["supplier selection"],
            target_audience="B2B buyers",
            business_type="packaging supplier",
            sample_keywords=["foam bottle wholesale"],
            customer_pain_points=["reducing lead time risk"],
            category_details=[],
            tag_details=[],
            product_records=[],
        )
        generator = ContentAwareKeywordGenerator(profile)

        product = ProductInsight(
            id=22,
            name="30ml 60ml 100ml White Black Pump White Lid Plastic Foam Bottle Empty Shampoo Container Wholesale",
            slug="foam-bottle-wholesale",
            url="https://example.com/product/foam-bottle",
            category_names=["Foam Bottles"],
            tag_names=["PET"],
            material="PET",
            capacity="30ml",
            closure_type="Pump",
            use_case="Shampoo",
            moq="10000",
            lead_time="15-20 days",
        )

        descriptor = generator._build_product_keyword_descriptor(product)

        assert "30-100ml" in descriptor
        assert "PET" in descriptor
        assert "Bottle" in descriptor
        assert len(descriptor.split()) <= 6

    def test_blocks_generic_explained_keyword_templates(self):
        profile = WebsiteProfile(
            product_categories=["dropper bottles"],
            industry_terms=["wholesale"],
            content_themes=["quality"],
            target_audience="B2B buyers",
            business_type="packaging supplier",
            sample_keywords=["dropper bottle wholesale"],
            customer_pain_points=["comparing MOQ and lead time"],
            category_details=[],
            tag_details=[],
            product_records=[],
        )
        generator = ContentAwareKeywordGenerator(profile)

        class CatalogMatch:
            page_type = "category_support"
            target_category_name = None
            target_tag_name = None
            primary_taxonomy_name = None
            supporting_products = []

        assessment = generator._assess_keyword_publishability(
            "quality 100ml white pump explained",
            CatalogMatch(),
        )

        assert assessment["publishable"] is False
        assert assessment["reason"] in {"generic template phrasing", "attribute fragment instead of publishable topic"}

    def test_candidate_carries_keyword_quality_and_serp_role(self):
        profile = WebsiteProfile(
            product_categories=["dropper bottles"],
            industry_terms=["wholesale", "supplier"],
            content_themes=["customization"],
            target_audience="B2B buyers",
            business_type="packaging supplier",
            sample_keywords=["100ml dropper bottle supplier"],
            customer_pain_points=["checking sample and MOQ terms"],
            category_details=[],
            tag_details=[],
            product_records=[
                ProductInsight(
                    id=10,
                    name="100ml Dropper Bottle",
                    slug="100ml-dropper-bottle",
                    url="https://example.com/product/100ml-dropper-bottle",
                    category_names=["Dropper Bottles"],
                    tag_names=["Glass"],
                    material="Glass",
                    capacity="100ml",
                    closure_type="Dropper",
                    use_case="Serum",
                    moq="5000",
                    lead_time="20 days",
                )
            ],
        )
        generator = ContentAwareKeywordGenerator(profile)
        candidate = generator._build_candidate(
            keyword="100ml dropper bottle supplier",
            intent="commercial",
            journey_stage="decision",
            category="dropper bottles",
            semantic_group="dropper",
        )

        assert candidate.keyword_publishable is True
        assert candidate.keyword_quality_score >= 0.58
        assert candidate.serp_role in {"supplier_evaluation", "procurement_faq"}
