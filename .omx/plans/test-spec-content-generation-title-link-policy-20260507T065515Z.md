# Test Spec: Content Generation Title Quality And Internal Link Policy

## Purpose
Verify that automatic article generation avoids generic procurement-tail titles and never persists final article HTML with more than 5 internal links.

## Test-First Expectations
Add failing regression tests before implementation where feasible, especially for:
- Generic procurement-tail title selection.
- Worst-case additive internal-link path exceeding 5 links.
- Quality gates requiring `3+` internal links.

## Unit Test Coverage

### Shared Policy Helpers
- `is_internal_link(url, site_base_url)` returns true for same-domain and relative URLs.
- It returns false for external URLs, `mailto:`, `tel:`, off-domain citation/reference URLs, and fragment-only `#section` links.
- Same-domain comparison normalizes `http/https`, optional `www`, trailing slash, and configured port.
- Internal-link counting uses final rendered HTML and the canonical predicate.
- Remaining-budget calculation returns `max(0, 5 - current_internal_count)`.
- Pruning keeps at most 5 internal links and removes duplicate/self/weak contextual links first.
- Arbitration is idempotent: `arbitrate(arbitrate(html)) == arbitrate(html)`.

### Title Policy / Hook Optimizer
- A generic procurement-heavy title candidate such as `Keyword: MOQ, Lead Time, Supplier` is down-ranked against a context-rich buyer/search-value title.
- Strict fallback titles avoid low-value generic procurement triplets.
- Procurement terms remain allowed when the query and context explicitly support them and the tail includes meaningful modifiers, such as sample policy, quote criteria, audit risk, capacity/material/closure fit, or specific buyer decision logic.
- Commercial term density alone does not raise a title above a more specific intent-matched alternative.

### Content Creator
- Prompted internal-link opportunities are capped by remaining budget, not fixed `[:3]` slicing alone.
- `_integrate_internal_links` inserts zero contextual links when relevance is weak or remaining budget is zero.
- Final post-assembly arbiter runs after generated content, references, CTA text, and contextual insertion are present.
- Final output contains `<=5` internal links even when the model emits extra same-domain links in CTA sections.
- A second arbiter pass is a no-op.

### Internal Link Agent
- `_calculate_max_links` respects total article cap and existing internal-link count.
- There is no minimum-link pressure; zero recommendations is valid.
- Weak opportunities do not pass only because of a base relevance score.
- `insert_links` applies no more than the remaining budget and skips duplicates/self links.

### Scheduler Jobs
- `_add_catalog_links` and recent-post opportunities share the same budget and do not append unbounded category/tag/product/recent-post links.
- Placeholder recent-post relevance is replaced with computed or conservative relevance.
- The standalone internal-linking job skips or re-arbitrates before WordPress update so the persisted content remains `<=5` internal links.
- Add an assertion that no later publish/update stage mutates links after arbitration without reusing the policy.

### Quality Gates
- `src/services/quality_gate.py` passes content with 0-5 internal links when other quality criteria are satisfied.
- `src/agents/quality_gate.py` no longer recommends `3+` links as a generic structural requirement.
- Both gates flag `>5` internal links as an SEO risk.
- External citations/references do not cause a false `>5 internal links` failure.

## Integration Fixtures

### Worst-Case Additive Link Path
Fixture content includes:
- Existing category link.
- Existing tag link.
- Product CTA link.
- Prompt-suggested contextual links.
- Generated CTA same-domain links.
- External citation/reference links.

Assertions:
- Final rendered HTML has `<=5` internal links.
- External references remain allowed and do not count toward the cap.
- Duplicate targets, self links, and weak contextual links are pruned before high-value catalog navigation links.
- Re-running the final arbiter does not change the HTML.

### Title Regression Fixture
Input includes a wholesale/procurement-like topic and catalog context that previously selected generic tails.

Assertions:
- Selected title does not collapse to `MOQ, Lead Time, Supplier` or equivalent field-label strings.
- Selected title includes concrete buyer/search value.
- If procurement terms appear, they are tied to meaningful context or decision logic.

### Publish/Update Path Fixture
Simulate content after generation and before publish/update.

Assertions:
- The content creator output is arbitrated before publication.
- Any later internal-linking job either skips when budget is full or reuses the arbiter before update.
- Persisted HTML remains `<=5` internal links.

## Suggested Test Commands
Run focused tests first, then broader relevant suites:

```powershell
pytest tests/unit/content tests/services/content tests/agents/test_content_creator_integration.py
pytest tests/unit/services/test_quality_gate_catalog.py tests/unit/services/test_jobs_catalog_routing.py
pytest tests/integration/test_publish_flow.py tests/integration/test_content_intelligence.py
```

Adjust exact test targets after implementation adds or moves fixtures.

## Completion Evidence
Implementation is not complete until the final report can show:
- Focused tests passing for title policy, link policy helpers, content creator, internal-link agent, scheduler, and both quality gates.
- At least one integration fixture proving final HTML `<=5` internal links in the worst-case additive path.
- At least one regression fixture proving generic procurement-tail titles are rejected/down-ranked.
- No known publish/update path can bypass arbitration.
