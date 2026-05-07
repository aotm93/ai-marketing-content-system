# PRD: Content Generation Title Quality And Internal Link Policy

## Status
Approved planning artifact from `$ralplan` consensus.

## Context
Automatic article generation currently produces low-value procurement-style titles such as generic `MOQ, Lead Time, Supplier` formats. Generated article content can also accumulate too many internal links because scheduler opportunities, CTA/category/tag/product links, prompt instructions, post-generation insertion, and internal-link jobs each apply local heuristics.

The user goal is to avoid manipulative-looking SEO output: internal links should not exceed 5 per final article and should be genuinely relevant recommendations.

Related context snapshot: `.omx/context/content-generation-title-internal-links-20260507T064219Z.md`.
Consensus plan: `.omx/plans/ralplan-article-generation-title-link-repair-20260507.md`.

## Decision
Implement Option A+: targeted rule harmonization with a lightweight shared content policy and a final post-assembly internal-link arbiter.

This is not a full architecture refactor. The repair should keep the existing generation pipeline but add enough shared policy to make title quality and final link count deterministic.

## Goals
- Generated titles should communicate specific buyer/search value, not generic procurement-label strings.
- Final rendered article HTML must contain no more than 5 internal links.
- Internal-link insertion must be relevance-first; zero contextual links is acceptable.
- CTA/category/tag/product links and contextual links must share the same article-level budget.
- Quality gates must stop rewarding or requiring `3+` internal links.

## Non-Goals
- Do not add new dependencies.
- Do not rebuild the content pipeline or introduce a broad policy framework.
- Do not remove useful catalog/category/product CTA links when they are genuinely relevant and fit inside the budget.
- Do not count external citations or references against the internal-link cap.

## Policy Contract
- `MAX_TOTAL_INTERNAL_LINKS = 5`.
- `MIN_CONTEXTUAL_INTERNAL_LINKS = 0`.
- `ALLOW_ZERO_CONTEXTUAL_LINKS = True`.
- Internal links are same-domain/same-site URLs based on `settings.wordpress_url`, or relative site URLs.
- External links, citation/reference URLs, `mailto:`, `tel:`, and off-domain URLs do not count toward the cap.
- Fragment-only links such as `#section` do not count toward the cap unless they resolve to a different same-site URL with a path.
- Same-domain comparison should normalize `http/https`, optional `www`, trailing slash, and configured port where applicable.
- Final rendered HTML is the authoritative source for link-count pass/fail.
- The final arbiter must run after all content generation, CTA guidance, references, and contextual insertion in `ContentCreatorAgent._create_article`.
- Any later publish/update/internal-linking path must reuse the same policy or re-arbitrate before content is written.
- Running the arbiter twice must be a no-op.
- Pruning must be deterministic: remove duplicate targets, self links, and weak contextual links before high-value category/tag/product navigation links; preserve document order within equal priority.

## In Scope
- `src/services/content/hook_optimizer.py`: remove generic procurement-tail advantage and penalize/deny low-value procurement triplets unless context contains rich modifiers.
- Shared lightweight helper under the content service area, for constants and helpers such as internal-link counting, remaining-budget calculation, opportunity pruning, final HTML arbitration, and generic-title-tail detection.
- `src/agents/content_creator.py`: make prompt/insertion budget-aware and add final post-assembly arbitration.
- `src/agents/internal_link.py`: remove minimum-link pressure, strengthen relevance scoring, and respect remaining budget.
- `src/scheduler/jobs.py`: stop appending unbudgeted link opportunities; replace placeholder relevance with computed/conservative relevance and ensure update paths do not bypass the final cap.
- `src/services/quality_gate.py` and `src/agents/quality_gate.py`: replace `3+ links` expectations with cap/relevance checks.

## Acceptance Criteria
- Titles no longer default to generic low-value procurement triplets such as `MOQ, Lead Time, Supplier`.
- Title selection favors specific buyer-intent or search-intent value over raw procurement-term density.
- Final rendered article HTML contains `<=5` internal links using the canonical predicate.
- External references/citations are not counted as internal links.
- Contextual internal links may be zero when relevance is weak or budget is already consumed by higher-value catalog links.
- Weak, duplicate, or self-referential links are not inserted or are pruned by the final arbiter.
- Final arbitration is idempotent.
- Both quality gates stop failing articles solely because they have fewer than 3 internal links.
- Scheduler, content creator, internal-link agent, and publish/update paths cannot produce or persist content with more than 5 internal links.

## Risks
- Reducing procurement-term boosts may lower commercial-title aggressiveness. Mitigate with title ranking tests comparing generic and value-rich alternatives.
- A hard link cap may reduce discovery links in long articles. Mitigate by ranking the highest-value links first rather than forcing a minimum count.
- Shared policy may be only partially adopted. Mitigate with tests on every link-producing and quality-gate path.

## Execution Guidance
Use a single sequential executor or `$ralph` for implementation. A team is optional but not necessary unless implementation is split into independent lanes.

Recommended order:
1. Add policy/helper tests first for internal-link predicate, counting, pruning, and idempotency.
2. Add title-policy regression tests for generic procurement tails.
3. Implement the lightweight policy/helper module.
4. Wire title scoring/fallback to the title policy.
5. Wire content creator and scheduler paths to the link budget and final arbiter.
6. Align internal link agent and quality gates.
7. Run focused tests, then broader relevant test suites.

## Follow-Ups
- Add a sample-batch audit metric: percent of generated titles matching disallowed generic-tail pattern.
- Add a sample-batch audit metric: percent of generated articles with more than 5 internal links.
- Consider fuller policy-object centralization only if drift recurs.
