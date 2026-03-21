"""
Tests for catalog-aware meta descriptions and buyer next-step modules.
"""

from src.models.seo_context import SEOContext
from src.scheduler.jobs import (
    _append_procurement_next_step_block,
    _build_procurement_next_step_block,
    _generate_catalog_meta_description,
)


class TestJobsCatalogRouting:
    """Validate SERP and on-page routing helpers."""

    def test_generates_tag_driven_meta_description(self):
        seo_context = SEOContext(
            source="test",
            target_keyword="pet spray bottle wholesale",
            topic_title="pet spray bottle wholesale",
            selected_title="PET Spray Bottle Wholesale: MOQ, Lead Time, and Supplier Checks",
            target_category_name="Spray Bottles",
            target_category_url="https://example.com/category/spray-bottles",
            target_tag_name="PET",
            target_tag_url="https://example.com/tag/pet",
            primary_taxonomy_type="tag",
            primary_taxonomy_name="PET",
            primary_taxonomy_url="https://example.com/tag/pet",
            page_type="wholesale_faq",
        )

        meta = _generate_catalog_meta_description(seo_context, seo_context.target_keyword, 2026)

        assert "browse our pet tag page" in meta.lower()
        assert "moq" in meta.lower()
        assert len(meta) <= 160

    def test_builds_procurement_next_step_block_with_primary_and_secondary_paths(self):
        seo_context = SEOContext(
            source="test",
            target_keyword="pet spray bottle wholesale",
            topic_title="pet spray bottle wholesale",
            selected_title="PET Spray Bottle Wholesale: MOQ, Lead Time, and Supplier Checks",
            target_category_name="Spray Bottles",
            target_category_url="https://example.com/category/spray-bottles",
            target_tag_name="PET",
            target_tag_url="https://example.com/tag/pet",
            primary_taxonomy_type="tag",
            primary_taxonomy_name="PET",
            primary_taxonomy_url="https://example.com/tag/pet",
            supporting_products=[
                {
                    "name": "30ml PET Fine Mist Spray Bottle",
                    "url": "https://example.com/product/30ml-pet-fine-mist-spray-bottle",
                    "capacity": "30ml",
                    "material": "PET",
                    "closure_type": "Fine Mist Spray",
                }
            ],
        )

        block = _build_procurement_next_step_block(seo_context)

        assert 'class="buyer-next-step"' in block
        assert "https://example.com/tag/pet" in block
        assert "https://example.com/category/spray-bottles" in block
        assert "https://example.com/product/30ml-pet-fine-mist-spray-bottle" in block

    def test_appends_next_step_block_only_once(self):
        seo_context = SEOContext(
            source="test",
            target_keyword="spray bottles wholesale supplier",
            topic_title="spray bottles wholesale supplier",
            selected_title="Spray Bottles Wholesale Supplier: MOQ, Lead Time, and Samples",
            target_category_name="Spray Bottles",
            target_category_url="https://example.com/category/spray-bottles",
            primary_taxonomy_type="category",
            primary_taxonomy_name="Spray Bottles",
            primary_taxonomy_url="https://example.com/category/spray-bottles",
        )

        first = _append_procurement_next_step_block("<h1>Test</h1><p>Body</p>", seo_context)
        second = _append_procurement_next_step_block(first, seo_context)

        assert first.count('class="buyer-next-step"') == 1
        assert second.count('class="buyer-next-step"') == 1

    def test_uses_product_path_for_specific_query(self):
        seo_context = SEOContext(
            source="test",
            target_keyword="30ml pet fine mist spray bottle wholesale",
            topic_title="30ml pet fine mist spray bottle wholesale",
            selected_title="30ml PET Fine Mist Spray Bottle Wholesale: MOQ and Samples",
            target_category_name="Spray Bottles",
            target_category_url="https://example.com/category/spray-bottles",
            target_tag_name="PET",
            target_tag_url="https://example.com/tag/pet",
            primary_taxonomy_type="tag",
            primary_taxonomy_name="PET",
            primary_taxonomy_url="https://example.com/tag/pet",
            supporting_products=[
                {
                    "name": "30ml PET Fine Mist Spray Bottle",
                    "url": "https://example.com/product/30ml-pet-fine-mist-spray-bottle",
                    "capacity": "30ml",
                    "material": "PET",
                    "closure_type": "Fine Mist Spray",
                }
            ],
            page_type="wholesale_faq",
        )

        meta = _generate_catalog_meta_description(seo_context, seo_context.target_keyword, 2026)
        block = _build_procurement_next_step_block(seo_context)

        assert "review 30ml pet fine mist spray bottle" in meta.lower()
        assert "inspect the shortlisted product" in block.lower()
        assert "need comparable alternatives?" in block.lower()
