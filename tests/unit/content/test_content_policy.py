from src.services.content.content_policy import (
    MAX_TOTAL_INTERNAL_LINKS,
    arbitrate_internal_links,
    count_internal_links,
    filter_link_opportunities,
    has_generic_procurement_tail,
    is_internal_link,
    remaining_internal_link_budget,
)


SITE = "https://www.example.com"


def test_internal_link_predicate_counts_same_domain_and_relative_only():
    assert is_internal_link("/category/spray-bottles", SITE)
    assert is_internal_link("https://example.com/product/a", SITE)
    assert is_internal_link("http://www.example.com/product/a/", SITE)
    assert not is_internal_link("#faq", SITE)
    assert not is_internal_link("mailto:sales@example.com", SITE)
    assert not is_internal_link("tel:+123456", SITE)
    assert not is_internal_link("https://external.example/article", SITE)


def test_count_and_remaining_budget_ignore_external_references():
    html = """
    <p><a href="/category/a">Category</a></p>
    <p><a href="https://example.com/product/a">Product</a></p>
    <p><a href="https://source.example/report">Source</a></p>
    <p><a href="#toc">Jump</a></p>
    """

    assert count_internal_links(html, SITE) == 2
    assert remaining_internal_link_budget(html, SITE) == MAX_TOTAL_INTERNAL_LINKS - 2


def test_arbitration_prunes_to_five_and_is_idempotent():
    html = """
    <p><a href="/category/a">Category</a></p>
    <p><a href="/tag/pet">Tag</a></p>
    <p><a href="/product/one">Product One</a></p>
    <p><a href="/product/two">Product Two</a></p>
    <p><a href="/blog/relevant">Relevant Guide</a></p>
    <p><a href="/blog/weak">Weak Guide</a></p>
    <p><a href="https://source.example/report">External Reference</a></p>
    """

    once = arbitrate_internal_links(html, site_base_url=SITE)
    twice = arbitrate_internal_links(once, site_base_url=SITE)

    assert count_internal_links(once, SITE) == 5
    assert once == twice
    assert "External Reference" in once
    assert '<a href="https://source.example/report">' in once


def test_filter_link_opportunities_respects_budget_and_relevance():
    current_html = """
    <p><a href="/category/a">Category</a></p>
    <p><a href="/product/a">Product</a></p>
    <p><a href="/tag/a">Tag</a></p>
    <p><a href="/blog/existing">Existing</a></p>
    """
    opportunities = [
        {"target_url": "/blog/existing", "relevance_score": 0.99},
        {"target_url": "/blog/weak", "relevance_score": 0.3},
        {"target_url": "/blog/best", "relevance_score": 0.94},
        {"target_url": "/blog/second", "relevance_score": 0.91},
    ]

    selected = filter_link_opportunities(opportunities, current_html=current_html, site_base_url=SITE)

    assert [item["target_url"] for item in selected] == ["/blog/best"]


def test_generic_procurement_tail_detection():
    assert has_generic_procurement_tail("Spray Bottle Wholesale: MOQ, Lead Time, Supplier")
    assert not has_generic_procurement_tail("Spray Bottle Wholesale: Sample Policy, Quote Criteria, and Timing Risks")
