# Content Generation Title And Internal Link Fix Context

Task statement: Automatic content generation produces low-value titles such as generic `MOQ, Lead Time, Supplier` formats, and generated article content contains too many internal links.

Desired outcome: Generated titles should communicate specific buyer/search value instead of repeating generic procurement labels. Internal links should be capped and only included when genuinely relevant and useful.

Stated solution: Internal links should not exceed 5 and should be real recommendations with meaningful topical relevance.

Probable intent hypothesis: Reduce thin/templated SEO signals and avoid Google interpreting excessive internal linking as manipulative or spammy.

Known facts/evidence:
- `src/services/content/hook_optimizer.py` has catalog-aware title logic, procurement signal CTR boosts, and fallbacks that include `MOQ`, `Lead Time`, `Supplier`, or similar generic buyer terms.
- `src/agents/content_creator.py` injects up to 3 internal link opportunities into the generation prompt and then integrates up to 3 links after generation.
- `src/agents/internal_link.py` can recommend up to 10 new links per batch through `_calculate_max_links` and currently scores relevance from a 50-point base.
- `src/scheduler/jobs.py` has catalog link construction and a separate internal linking job that skips posts once existing internal links are at least 5.
- `src/services/quality_gate.py` still expects/recommends 3+ internal links, which may conflict with a stricter anti-overlinking policy if not revised carefully.

Constraints:
- Keep behavior small, reviewable, and tested.
- No new dependencies.
- Preserve useful catalog/category/product CTAs when relevant.
- Avoid adding generic internal links solely to satisfy a count.

Unknowns/open questions:
- Whether the internal link cap of 5 means total internal links in the final article, or newly inserted links only.
- Whether product/category/tag CTA links count toward the cap.
- Whether generic procurement title tails should be banned entirely, or only when not explicitly supported by the query/catalog context.

Decision-boundary unknowns:
- Can the implementation remove existing incentives that recommend minimum link counts?
- Can it reject publishing/generation outputs when the title is too generic or the link set exceeds/relevance-fails policy?

Likely codebase touchpoints:
- `src/services/content/hook_optimizer.py`
- `src/agents/content_creator.py`
- `src/agents/internal_link.py`
- `src/scheduler/jobs.py`
- `src/services/quality_gate.py`
- Existing tests under `tests/unit/content`, `tests/services/content`, and `tests/unit/services`.
