import pytest

from src.agents.internal_link import InternalLinkAgent
from src.services.content.content_policy import count_internal_links


@pytest.mark.asyncio
async def test_find_opportunities_allows_zero_when_relevance_is_weak():
    agent = InternalLinkAgent()

    result = await agent.execute(
        {
            "type": "find_opportunities",
            "source_content": "<p>This article discusses spray bottle closure fit and leakage checks.</p>",
            "source_page": "https://example.com/blog/source",
            "available_pages": [
                {
                    "url": "https://example.com/blog/unrelated",
                    "keyword": "coffee beans",
                    "title": "Coffee Roasting Guide",
                }
            ],
        }
    )

    assert result["status"] == "success"
    assert result["recommended_links_to_add"] == 0


@pytest.mark.asyncio
async def test_insert_links_respects_existing_budget():
    agent = InternalLinkAgent()
    content = """
    <p><a href="/category/a">Category</a></p>
    <p><a href="/tag/a">Tag</a></p>
    <p><a href="/product/a">Product A</a></p>
    <p><a href="/product/b">Product B</a></p>
    <p>The neck finish guide helps buyers.</p>
    <p>The filling guide helps buyers.</p>
    """

    result = await agent.execute(
        {
            "type": "insert_links",
            "content": content,
            "opportunities": [
                {"target_url": "/blog/neck", "anchor_text": "neck finish guide", "relevance_score": 95},
                {"target_url": "/blog/filling", "anchor_text": "filling guide", "relevance_score": 94},
            ],
        }
    )

    assert result["status"] == "success"
    assert count_internal_links(result["updated_content"], "https://example.com") == 5
    assert "/blog/neck" in result["updated_content"]
    assert "/blog/filling" not in result["updated_content"]


@pytest.mark.asyncio
async def test_insert_links_counts_absolute_same_domain_links_with_site_base_url():
    agent = InternalLinkAgent()
    content = """
    <p><a href="https://example.com/category/a">Category</a></p>
    <p><a href="https://www.example.com/tag/a">Tag</a></p>
    <p><a href="https://example.com/product/a">Product A</a></p>
    <p><a href="https://example.com/product/b">Product B</a></p>
    <p>The neck finish guide helps buyers.</p>
    <p>The filling guide helps buyers.</p>
    """

    result = await agent.execute(
        {
            "type": "insert_links",
            "content": content,
            "site_base_url": "https://example.com",
            "opportunities": [
                {"target_url": "https://example.com/blog/neck", "anchor_text": "neck finish guide", "relevance_score": 95},
                {"target_url": "https://example.com/blog/filling", "anchor_text": "filling guide", "relevance_score": 94},
            ],
        }
    )

    assert result["status"] == "success"
    assert count_internal_links(result["updated_content"], "https://example.com") == 5
    assert "https://example.com/blog/neck" in result["updated_content"]
    assert "https://example.com/blog/filling" not in result["updated_content"]


def test_analyze_page_links_uses_shared_internal_link_predicate():
    agent = InternalLinkAgent()
    content = """
    <p><a href="https://example.com/category/a">Category</a></p>
    <p><a href="/product/a">Product</a></p>
    <p><a href="https://external.example/report">Reference</a></p>
    """

    analysis = agent._analyze_page_links(content, "https://example.com/blog/source", "https://example.com")

    assert analysis["internal_links"] == 2
    assert analysis["external_links"] == 1
