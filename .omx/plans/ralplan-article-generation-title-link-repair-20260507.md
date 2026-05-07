# RALPLAN-DR Initial Plan: Article Title Quality + Internal Link Density Repair

## Plan Intent
Repair automatic article generation so titles avoid low-value generic procurement formats and total internal links per final article are capped at `<=5` with relevance-first insertion (including CTA/category/tag/product links).

## Scope Classification
- Type: Brownfield behavior repair (no architecture redesign)
- Complexity: Medium
- Dependencies: None new
- Constraints: Do not edit production code in this phase; planning artifact only

## Principles (RALPLAN-DR)
1. User-value over SEO-mechanical signals: prioritize specific, insight-led titles over generic procurement term strings.
2. Relevance over quota: insert internal links only when contextually justified; zero additional links is valid if relevance is weak.
3. Single cap policy: enforce one clear article-level internal link budget (`<=5`) across all link sources.
4. Backward-compatible rollout: minimize blast radius via localized rule/threshold changes and coordinated quality gate updates.
5. Verifiable outcomes: each rule change must map to deterministic tests and measurable generation outputs.

## Top Decision Drivers
1. Search-quality risk: excessive internal links can look manipulative; cap and relevance consistency are mandatory.
2. Content quality/CTR tradeoff: removing commercial-title bias must not collapse title clarity or intent alignment.
3. Cross-component consistency: scheduler, creator, link agent, and quality gates currently encode conflicting link expectations.

## Viable Options

### Option A+: Strict rule harmonization with lightweight policy + final arbiter (recommended)
- Summary: Keep current pipeline structure, but add a lightweight shared content policy and one final post-assembly link arbiter so thresholds, scoring, insertion, scheduler context, and quality gates obey the same invariants.
- Pros:
  - Still a contained brownfield repair, with stronger guarantees than local threshold edits.
  - Provides a single source of truth for `<=5` total internal links and zero-minimum contextual links.
  - Prevents future prompt/scheduler/link-agent drift from silently reinflating link count.
- Cons:
  - Slightly larger change than pure local retuning.
  - Requires careful placement of the final HTML arbiter so it runs after all link-producing steps.

### Option A: Local strict rule harmonization
- Summary: Normalize thresholds and scoring logic in-place across title selection, link insertion, scheduler context, and quality gates without a shared policy or final arbiter.
- Pros:
  - Smallest immediate diff.
  - Fast to ship.
- Cons:
  - Does not provide a hard systemic guarantee when multiple components add links.
  - Future prompt or scheduler edits can recreate the same overlinking failure.

### Option B: Policy-object centralization
- Summary: Introduce a shared content policy contract (title constraints + link budget/relevance) consumed by all generators/gates.
- Pros:
  - Strong long-term consistency and easier future tuning.
  - Reduces duplicated constants and drift risk.
- Cons:
  - Larger refactor footprint and higher regression risk now.
  - Slower to ship immediate repair.

### Option C: Post-generation sanitizer gate
- Summary: Leave generators mostly unchanged; add final pass that rewrites weak titles and prunes links to `<=5` by relevance.
- Pros:
  - Rapid containment of production output quality.
  - Minimal upstream logic edits.
- Cons:
  - Can mask upstream quality issues.
  - Potential non-determinism and awkward late-stage edits.

## Recommendation
Adopt **Option A+** now: a targeted repair with two structural minimums from the Architect review:
1. A lightweight shared content policy contract for title and internal-link rules.
2. A final, idempotent post-assembly link arbiter that treats final rendered HTML as the source of truth and prunes/ranks internal links to `<=5` across CTA/category/tag/product/contextual links.

Keep Option B's full policy-object refactor as a follow-up only if drift recurs.

## Architect Review Addendum
- Verdict: ITERATE on the original draft.
- Steelman antithesis: pure local retuning is faster and may be enough for an urgent quality repair.
- Tradeoff tension: tactical speed vs durable invariants across multiple link producers and quality gates.
- Synthesis accepted: retain a narrow repair lane but require shared constants/policy plus one final post-assembly enforcement pass.

## Policy Contract
- Internal link predicate: an internal link is an `<a href>` whose URL is relative (`/path`, `../path`, `#section` where appropriate for same page handling) or same-site/same-domain according to `settings.wordpress_url`; external references, citation URLs, mailto/tel links, and off-domain sources do not count toward the internal-link cap.
- Canonical count source: final rendered HTML after all generation, CTA guidance, references, contextual insertion, and scheduler-provided opportunities have been assembled.
- Final arbiter order: run once at the end of `ContentCreatorAgent._create_article` after `_integrate_internal_links` and any references/CTA-producing content are present; any later internal-linking job must reuse the same policy before updating WordPress content.
- Idempotency invariant: running the arbiter on already-arbitrated HTML must be a no-op.
- Deterministic pruning order: keep higher relevance/explicit catalog destination links first, remove duplicate targets/self links/weak contextual links before removing high-value category/tag/product CTAs, and preserve original document order within equal priority.

## Proposed Code Touchpoints (planned edits later)
1. `src/services/content/hook_optimizer.py`
- Reduce over-weighting of commercial/procurement terms in `_estimate_ctr` and fallback/title selection path.
- Tighten `_generate_catalog_anchored_title`, `_catalog_tail_for_hook`, `_derive_buyer_angle`, and `_build_strict_fallback_variant` so generic formats like `"MOQ, Lead Time, Supplier"` are down-ranked or excluded unless contextually rich.
- Add/use title-policy helpers that detect low-value procurement triplets and require contextual modifiers before such tails are eligible.

2. Shared policy/helper module (new or existing nearest-fit utility under `src/services/content/`)
- Define the canonical constants and helpers, for example:
  - `MAX_TOTAL_INTERNAL_LINKS = 5`
  - `MIN_CONTEXTUAL_INTERNAL_LINKS = 0`
  - `ALLOW_ZERO_CONTEXTUAL_LINKS = True`
  - `MIN_CONTEXTUAL_LINK_RELEVANCE`
  - `is_internal_link(url, site_base_url)` using the internal-link predicate above
  - helpers to count internal links from final HTML, calculate remaining budget, rank/prune opportunities, arbitrate final HTML links, and identify generic procurement title tails.
- Keep it lightweight; do not introduce a broad framework.

3. `src/agents/content_creator.py`
- Replace fixed `internal_links[:3]` assumptions with budget-aware insertion that respects global cap after CTA/catalog/tag/product links.
- Update prompt section (`INTERNAL LINKING OPPORTUNITIES`) and `_integrate_internal_links` behavior to allow fewer/zero contextual links when relevance is insufficient.
- Add the final post-assembly link arbiter after generated content, references, CTA/prompt-driven links, and `_integrate_internal_links` have all run. This arbiter must be idempotent and source-agnostic.

4. `src/agents/internal_link.py`
- Harmonize constants and caps with article-level policy: remove minimum-link pressure (`MIN_LINKS_PER_PAGE=3`) and ensure `_calculate_max_links` cannot force links beyond remaining budget.
- Keep relevance thresholding strict; strengthen guardrails where opportunities are sliced (`opportunities[:5]`) to budget/relevance-first behavior.
- Remove base-score pass-through behavior where a weak target can pass relevance purely from the default baseline.

5. `src/scheduler/jobs.py`
- Ensure `_add_catalog_links` and recent-post opportunities are composed under one total link budget, not additive pressure from multiple sources.
- Keep `internal_linking_job` skip logic aligned with final cap semantics.
- Replace hardcoded `relevance_score=0.7` TODO recent-post opportunities with computed or conservative relevance, and only pass opportunities inside remaining budget.

6. `src/services/quality_gate.py` and `src/agents/quality_gate.py`
- Replace `3+ internal links` requirement with rule set:
  - `total_internal_links <= 5`
  - links must satisfy relevance checks
  - no failure when contextual insertions are 0 due to low relevance.

## Acceptance Criteria
1. Title quality
- Generated titles do not default to generic low-value procurement triplets (e.g., `"MOQ, Lead Time, Supplier"`) unless explicitly supported by rich contextual modifiers.
- Title ranking logic demonstrably favors specific buyer-intent/value framing over raw procurement-term density.

2. Internal link policy
- Final article total internal links are always `<=5`, counting CTA/category/tag/product/contextual links together.
- Final rendered HTML link count is the authoritative pass/fail source, not requested opportunities or pre-generation counts.
- The internal-link counter uses one canonical predicate: same-domain or relative links count; external citations/references do not count.
- The final arbiter runs after all link-producing stages in the content creation path and any later internal-linking update path reuses the same policy before publish/update.
- Running the final arbiter twice produces the same HTML as running it once.
- When more than 5 internal links exist, pruning is deterministic and removes duplicate/self/weak contextual links before high-value catalog navigation links.
- Contextual inserted links may be `0..N` based on remaining budget and relevance; no mandatory minimum.
- Links below configured relevance threshold are not inserted.
- No module may add contextual links without calculating remaining budget or passing through the final arbiter.

3. Quality gate consistency
- Both quality-gate implementations enforce cap/relevance policy and no longer require `3+` links.

4. Pipeline consistency
- Scheduler + content creator + internal link agent produce convergent behavior (no component can re-inflate links above cap).

## Test Strategy (for upcoming test-spec)

### Unit tests
1. `hook_optimizer` title scoring tests
- Verify procurement-term-heavy generic titles are down-ranked against context-rich alternatives.
- Verify strict fallback avoids low-value generic patterns.

2. `content_creator` integration logic tests
- Given pre-existing CTA/catalog links, ensure contextual insertion honors remaining budget.
- Verify zero insertion path when relevance/opportunities are weak.
- Verify final arbiter idempotency: `arbitrate(arbitrate(html)) == arbitrate(html)`.
- Verify internal-link predicate excludes external references/citations from the `<=5` cap.

3. `internal_link` policy tests
- `_calculate_max_links` respects total cap and existing links.
- Relevance threshold blocks weak opportunities.
- Weak candidates do not pass solely because of a base relevance score.

4. `quality_gate` rule tests
- Pass with `0-5` relevant internal links (depending on context).
- Fail when `>5` links or relevance constraints are violated.

### Integration tests
1. End-to-end generation fixture where scheduler supplies mixed link opportunities:
- Assert final article link count `<=5`.
- Assert only relevant links survive.

2. Worst-case additive-path fixture:
- Include prompt-suggested internal links, CTA/category/tag/product links, and contextual insertion opportunities.
- Assert final post-assembly HTML remains `<=5`, proving the arbiter runs after all link-producing stages.
- Assert duplicate/self/weak links are pruned in deterministic order and a second arbiter pass is a no-op.

3. End-to-end title selection fixture:
- Assert selected title is non-generic and buyer-intent/value oriented.

### Regression tests
- Add fixtures reproducing current failure mode (`"MOQ, Lead Time, Supplier"` style + excessive linking pressure) and verify repaired outputs.

## Risks and Mitigations
- Risk: CTR heuristic retuning may reduce perceived commercial intent.
  - Mitigation: golden-set comparison with explicit title quality assertions and controlled threshold tuning.
- Risk: Link cap could reduce internal discovery in some long-form posts.
  - Mitigation: keep cap hard at 5 per requirement; allow relevance-first distribution across highest-value links.
- Risk: Dual quality gates drift again.
  - Mitigation: mirrored tests in both modules and explicit policy assertions.

## ADR (Initial)
- Decision: Implement targeted rule harmonization with lightweight shared policy constants and a final post-assembly link arbiter (Option A+) to repair title quality and internal link overuse without a full architecture refactor.
- Drivers: search-quality safety, behavior consistency across pipeline, rapid low-risk brownfield repair.
- Alternatives considered:
  - Option A local-only rule harmonization: fastest immediate diff but lacks a hard cross-component cap guarantee.
  - Option B policy centralization: stronger long-term design but larger immediate risk/effort.
  - Option C sanitizer gate: fast containment but masks upstream defects.
- Why chosen: best balance of speed, safety, and deterministic verification under current constraints because it preserves a narrow repair lane while adding the minimum structural guarantees needed for `<=5` final internal links.
- Consequences:
  - Near-term: modestly larger diff than local-only retuning, but final HTML has an enforceable link budget and shared title/link constants reduce drift.
  - Long-term: some heuristic duplication remains outside the lightweight policy; may require future centralization.
- Follow-ups:
  1. Evaluate policy-object centralization if drift recurs in 2+ releases.
  2. Add periodic generation audits for title pattern quality and link-density compliance.

## Open Questions
- None blocking for PRD/test-spec drafting under the stated assumption (`<=5` hard cap including all internal link types).
