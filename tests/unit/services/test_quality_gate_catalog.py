"""
Tests for catalog-aware quality gate validation.
"""

import pytest

from src.services.quality_gate import EnhancedQualityGate


class TestCatalogAwareQualityGate:
    """Validate commercial/catalog quality checks."""

    @pytest.mark.asyncio
    async def test_blocks_missing_category_and_product_support(self):
        service = EnhancedQualityGate()

        diagnostic = await service.full_diagnostic(
            content="""
            <h1>Spray Bottle Wholesale Guide</h1>
            <p>This article talks generally about packaging quality and market trends.</p>
            <h2>Overview</h2>
            <p>Buyers should look for quality and reliability.</p>
            <h2>FAQ</h2>
            <p>FAQ content here.</p>
            """,
            content_id="catalog_missing",
            target_keyword="spray bottle wholesale",
            components=["summary", "faq"],
            page_type="wholesale_faq",
            catalog_context={
                "page_type": "wholesale_faq",
                "target_category_name": "Spray Bottles",
                "target_category_url": "https://example.com/category/spray-bottles",
                "supporting_products": [
                    {"name": "30ml PET Fine Mist Spray Bottle", "url": "https://example.com/product/30ml-pet-fine-mist-spray-bottle"}
                ],
                "decision_questions": ["What MOQ and lead time apply to spray bottle sourcing?"],
                "commercial_facts": ["30ml PET Fine Mist Spray Bottle references MOQ 10000."],
            }
        )

        titles = [issue.title for issue in diagnostic.issues]
        assert any("taxonomy link" in title.lower() for title in titles)
        assert any("supporting product" in title.lower() for title in titles)
        assert diagnostic.can_publish is False

    @pytest.mark.asyncio
    async def test_accepts_tag_link_as_catalog_path(self):
        service = EnhancedQualityGate()
        service.MIN_WORD_COUNT = 60

        content = """
        <h1>PET Packaging Wholesale: MOQ, Material, and Supplier Checks</h1>
        <p>Buyers comparing <a href="https://example.com/tag/pet">PET</a> packaging options usually start with MOQ, lead time, closure fit, and decoration flexibility.</p>
        <p>The article uses the PET tag page as the next step because that landing page groups multiple bottle and jar formats sharing the same resin family.</p>
        <h2>Specification Table</h2>
        <table><tr><th>Item</th><th>Material</th><th>MOQ</th></tr><tr><td>30ml PET Fine Mist Spray Bottle</td><td>PET</td><td>10000</td></tr></table>
        <p>The <a href="https://example.com/product/30ml-pet-fine-mist-spray-bottle">30ml PET Fine Mist Spray Bottle</a> is one example buyers can sample when they need cosmetic packaging with fast decoration review.</p>
        <h2>FAQ</h2>
        <p>FAQ: What MOQ, lead time, and sample policy apply to PET packaging sourcing?</p>
        <p>Answer: Buyers should compare sample timing, leak testing, carton packing, and decoration approval before moving into bulk production.</p>
        """

        diagnostic = await service.full_diagnostic(
            content=content,
            content_id="tag_support",
            target_keyword="pet packaging wholesale",
            components=["summary", "faq", "table", "comparison_table"],
            page_type="wholesale_faq",
            catalog_context={
                "page_type": "wholesale_faq",
                "target_tag_name": "PET",
                "target_tag_url": "https://example.com/tag/pet",
                "supporting_products": [
                    {"name": "30ml PET Fine Mist Spray Bottle", "url": "https://example.com/product/30ml-pet-fine-mist-spray-bottle"}
                ],
                "decision_questions": ["What MOQ and lead time apply to PET packaging sourcing?"],
                "commercial_facts": ["30ml PET Fine Mist Spray Bottle references MOQ 10000."],
            }
        )

        assert diagnostic.can_publish is True

    @pytest.mark.asyncio
    async def test_accepts_wholesale_faq_with_catalog_support(self):
        service = EnhancedQualityGate()
        service.MIN_WORD_COUNT = 250

        content = """
        <h1>30ml PET Spray Bottle Wholesale: MOQ, Decoration, and Lead Time</h1>
        <p>Buyers sourcing from our <a href="https://example.com/category/spray-bottles">Spray Bottles</a> category usually compare MOQ, lead time, sample availability, and customization options first.</p>
        <p>For cosmetic packaging projects, buyers also need to compare material stability, closure compatibility, shipping method, and logo decoration before they shortlist a supplier. A useful wholesale FAQ page should answer procurement questions directly instead of giving generic market commentary.</p>
        <h2>Specification Comparison</h2>
        <table><tr><th>Option</th><th>Capacity</th><th>Material</th><th>MOQ</th></tr><tr><td>30ml PET Fine Mist Spray Bottle</td><td>30ml</td><td>PET</td><td>10000</td></tr></table>
        <p>The <a href="https://example.com/product/30ml-pet-fine-mist-spray-bottle">30ml PET Fine Mist Spray Bottle</a> fits cosmetic packaging projects that need fine mist spray, logo printing, and fast sample review.</p>
        <p>In practice, a buyer may compare this option with a travel-size sprayer, a lotion pump bottle, and a glass mist bottle to understand trade-offs in weight, breakage risk, filling line fit, and unit economics. This is where material, neck finish, sample review speed, and packaging method become real sourcing criteria.</p>
        <img src="https://example.com/images/spray-bottle.jpg" alt="30ml PET spray bottle" />
        <h2>Buyer Checklist</h2>
        <ul><li>Confirm MOQ</li><li>Check lead time</li><li>Review closure compatibility and neck finish</li><li>Verify SGS or FDA requirements</li></ul>
        <p>Before placing a bulk order, buyers should request samples, confirm whether logo printing or labeling is available, ask about export carton packing, and review whether the closure is matched to the chosen neck finish. If the project needs rapid launch timing, the lead time for custom color, printing, and packaging can matter as much as the quoted unit price.</p>
        <p>Many buyers also compare the spray bottle with the broader <a href="https://example.com/category/cosmetic-packaging">cosmetic packaging</a> range so they can evaluate whether a jar, airless bottle, or lotion pump format would create better shelf fit. That broader category review often prevents a rushed choice based only on price.</p>
        <h2>FAQ</h2>
        <p>FAQ: What MOQ, lead time, sample policy, customization, and shipping terms apply?</p>
        <p>Answer: MOQ often starts with the stock configuration, while custom color, hot stamping, screen printing, or special packaging may raise the MOQ and extend lead time. Buyers should compare sample timing, carton packing method, decoration proof approval, and shipping mode before confirming production.</p>
        <p>Answer: If a buyer needs a matching cap or alternate closure, the safest route is to confirm neck finish tolerance, compatibility testing, and leakage checks before mass production. Buyers can also review the <a href="https://example.com/blog/spray-bottle-neck-finish-guide">spray bottle neck finish guide</a> to validate closure fitment.</p>
        """

        diagnostic = await service.full_diagnostic(
            content=content,
            content_id="catalog_strong",
            target_keyword="30ml pet spray bottle wholesale",
            components=["summary", "faq", "table", "comparison_table", "buyer_checklist", "moq_and_lead_time", "customization"],
            page_type="wholesale_faq",
            catalog_context={
                "page_type": "wholesale_faq",
                "target_category_name": "Spray Bottles",
                "target_category_url": "https://example.com/category/spray-bottles",
                "supporting_products": [
                    {"name": "30ml PET Fine Mist Spray Bottle", "url": "https://example.com/product/30ml-pet-fine-mist-spray-bottle"}
                ],
                "decision_questions": ["What MOQ and lead time apply to spray bottle sourcing?"],
                "commercial_facts": ["30ml PET Fine Mist Spray Bottle references MOQ 10000."],
            }
        )

        assert diagnostic.can_publish is True
        assert diagnostic.overall_score >= 60

    @pytest.mark.asyncio
    async def test_traffic_entry_meta_and_cta_are_scored_for_lane_fit(self):
        service = EnhancedQualityGate()
        service.MIN_WORD_COUNT = 80

        content = """
        <h1>Glass vs PET Dropper Bottle for Serum</h1>
        <p>Choosing between glass and PET depends on formula stability, light protection, breakage tolerance, and dosing expectations.</p>
        <p>Readers can <a href="https://example.com/category/dropper-bottles">browse dropper bottles</a> to compare options after reviewing the material trade-offs.</p>
        <h2>Comparison</h2>
        <p>Glass supports better premium positioning, while PET reduces breakage risk and freight weight for travel-size formats.</p>
        """

        diagnostic = await service.full_diagnostic(
            content=content,
            content_id="traffic_lane_ok",
            target_keyword="glass vs pet dropper bottle for serum",
            page_type="spec_comparison",
            catalog_context={
                "page_type": "spec_comparison",
                "content_lane": "traffic_entry",
                "search_stage": "consideration",
                "target_category_name": "Dropper Bottles",
                "target_category_url": "https://example.com/category/dropper-bottles",
            },
            meta_title="Glass vs PET Dropper Bottle for Serum: Material Choice and Tradeoffs",
            meta_description="Compare glass vs PET dropper bottle options for serum packaging, formula fit, and breakage trade-offs before you shortlist the right format.",
            content_lane="traffic_entry",
            search_stage="consideration",
        )

        lane_titles = [issue.title.lower() for issue in diagnostic.issues]
        assert diagnostic.metrics["lane_alignment_score"] is not None
        assert diagnostic.metrics["lane_alignment_score"] >= 70
        assert not any("traffic-entry meta description lacks search-entry framing" in title for title in lane_titles)

    @pytest.mark.asyncio
    async def test_procurement_lane_blocks_weak_meta_and_missing_conversion_cta(self):
        service = EnhancedQualityGate()
        service.MIN_WORD_COUNT = 60

        content = """
        <h1>100ml Dropper Bottle Wholesale</h1>
        <p>This article discusses packaging options in a general way.</p>
        <p>It mentions materials and bottle choices but does not tell the buyer how to shortlist suppliers or request samples.</p>
        """

        diagnostic = await service.full_diagnostic(
            content=content,
            content_id="procurement_lane_weak",
            target_keyword="100ml dropper bottle wholesale",
            page_type="wholesale_faq",
            catalog_context={
                "page_type": "wholesale_faq",
                "content_lane": "procurement_conversion",
                "search_stage": "decision",
                "target_category_name": "Dropper Bottles",
                "target_category_url": "https://example.com/category/dropper-bottles",
            },
            meta_title="100ml Dropper Bottle Wholesale Guide",
            meta_description="Compare 100ml dropper bottle options and material choices for packaging projects.",
            content_lane="procurement_conversion",
            search_stage="decision",
        )

        titles = [issue.title.lower() for issue in diagnostic.issues]
        assert any("procurement-conversion meta description lacks buying intent signals" in title for title in titles)
        assert any("procurement-conversion page lacks a conversion cta" in title for title in titles)
        assert diagnostic.metrics["lane_alignment_score"] < 70
