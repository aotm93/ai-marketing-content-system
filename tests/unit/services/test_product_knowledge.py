"""
Tests for catalog matching with category/tag routing.
"""

from src.services.product_knowledge import (
    CategoryInsight,
    ProductInsight,
    ProductCatalogMatcher,
)


class TestProductCatalogMatcher:
    """Validate primary taxonomy selection rules."""

    def test_prefers_tag_page_for_attribute_led_keyword(self):
        matcher = ProductCatalogMatcher()

        categories = [
            CategoryInsight(
                id=1,
                name="Spray Bottles",
                slug="spray-bottles",
                url="https://example.com/category/spray-bottles",
                product_count=12,
            )
        ]
        tags = [
            CategoryInsight(
                id=11,
                name="PET",
                slug="pet",
                url="https://example.com/tag/pet",
                product_count=8,
            )
        ]
        products = [
            ProductInsight(
                id=101,
                name="30ml Fine Mist Spray Bottle",
                slug="30ml-fine-mist-spray-bottle",
                url="https://example.com/product/30ml-fine-mist-spray-bottle",
                category_names=["Spray Bottles"],
                tag_names=["PET"],
                material="PET",
                capacity="30ml",
                closure_type="Fine Mist Spray",
            )
        ]

        match = matcher.match_topic("pet spray bottle wholesale", categories, products, tags)

        assert match.primary_taxonomy_type == "tag"
        assert match.primary_taxonomy_name == "PET"
        assert match.target_tag_url == "https://example.com/tag/pet"

    def test_prefers_category_page_for_browse_keyword(self):
        matcher = ProductCatalogMatcher()

        categories = [
            CategoryInsight(
                id=1,
                name="Spray Bottles",
                slug="spray-bottles",
                url="https://example.com/category/spray-bottles",
                product_count=12,
            )
        ]
        tags = [
            CategoryInsight(
                id=11,
                name="PET",
                slug="pet",
                url="https://example.com/tag/pet",
                product_count=8,
            )
        ]
        products = [
            ProductInsight(
                id=101,
                name="30ml Fine Mist Spray Bottle",
                slug="30ml-fine-mist-spray-bottle",
                url="https://example.com/product/30ml-fine-mist-spray-bottle",
                category_names=["Spray Bottles"],
                tag_names=["PET"],
                material="PET",
                capacity="30ml",
                closure_type="Fine Mist Spray",
            )
        ]

        match = matcher.match_topic("spray bottles wholesale supplier", categories, products, tags)

        assert match.primary_taxonomy_type == "category"
        assert match.primary_taxonomy_name == "Spray Bottles"
        assert match.target_category_url == "https://example.com/category/spray-bottles"
