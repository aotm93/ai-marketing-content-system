# PRD - SEO Title Direction Upgrade

## Status
- Workflow: `$ralplan` / consensus planning
- Based on: `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\.omx\specs\deep-interview-seo-title-direction.md`
- Consensus verdict: APPROVE
- Execution mode recommendation: `$ralph` for safer sequential rollout, `$team` if parallel lane execution is preferred

## RALPLAN-DR Summary

### Principles
1. Route before writing: decide page role before generating titles, outlines, or body prompts.
2. Preserve query intent: do not trade search relevance for style variety.
3. Separate lane behavior: traffic-entry pages and procurement-conversion pages must use different title families and article structures.
4. Keep commercial credibility: even traffic-entry pages must retain scenario and buyer-decision value.
5. Change the minimum necessary surface: fit the upgrade into the existing SEOContext and scheduler pipeline without new dependencies.

### Decision Drivers
1. The current bottleneck is systemic title homogenization in `hook_optimizer.py`, not isolated wording.
2. Business strategy requires equal priority for traffic expansion and procurement conversion.
3. Product-head queries must keep a commercial default while informational expansion comes from explicit routing.

### Viable Options

#### Option A - Tail-only cleanup in `HookOptimizer`
- Scope: rewrite `_catalog_tail_for_hook()` and `_shorten_tail()` to produce more varied tails.
- Pros: smallest diff, fastest ship, limited regression surface.
- Cons: does not solve missing page-role routing, planner/body mismatch, or over-commercial defaulting; high chance of cosmetic improvement only.

#### Option B - Lane-aware routing + title-family redesign + prompt propagation (Chosen)
- Scope: add a page-role classifier, store the role in `SEOContext`, generate lane-specific title families, and propagate lane-aware structure into planner/writer prompts.
- Pros: directly addresses the root cause; supports both business goals; aligns title, outline, body, CTA, and quality checks.
- Cons: touches multiple files and tests; requires migration of some assumptions in current unit coverage.

#### Option C - AI-only rewriting pass after title generation
- Scope: keep current pipeline and ask the model to rewrite repetitive titles into something more professional.
- Pros: simple to add, high stylistic flexibility.
- Cons: unstable, harder to test, likely to drift from query relevance, and does not fix routing logic.

### Chosen Direction
Choose Option B. The system needs a deterministic routing layer before title generation so product-head terms can remain conversion-focused while informational demand is served by dedicated entry-page structures.

## Problem Statement
Current generated titles collapse many commercial/product topics into a narrow pattern such as `MOQ, Lead Time, Buyer Checks`, causing:
- weak SERP differentiation,
- limited keyword-intent coverage,
- overuse of procurement FAQ framing,
- body-content homogenization because `title_must_use` is enforced as H1.

## Goals
1. Support two first-class content lanes:
   - `traffic_entry`
   - `procurement_conversion`
2. Use combined routing signals from keyword wording, product type, and search stage.
3. Preserve procurement-default routing for product-head queries.
4. Diversify title families so different search intents produce meaningfully different headlines.
5. Ensure content planning and writing follow the selected lane.
6. Keep compatibility with the existing SEOContext-driven publishing flow.

## Non-goals
- Build encyclopedia-style explainer content.
- Add beginner-tutorial tone.
- Use clickbait framing.
- Keep a one-size-fits-all `MOQ / Lead Time` suffix model.
- Depend on external packages or new services outside the repo.
- Replace exact H1 synchronization.

## Users / Search Intents
- B2B buyers who search product-head terms and want supplier evaluation, MOQ, samples, customization, QC, or quotation guidance.
- Mid-funnel searchers who compare materials, applications, fit, risk, or tradeoffs before procurement.
- Searchers entering from pain-point, scenario, selection, and spec-interpretation topics that should feed commercial pages later.

## Brownfield Evidence
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\services\content\hook_optimizer.py`
  - repeated tail construction and normalization compress many topics into similar titles.
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\services\content\intent_analyzer.py`
  - shallow trigger-based intent classification is insufficient for lane routing.
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\services\content\content_planner.py`
  - planner currently classifies article format but not business page role.
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\agents\content_creator.py`
  - writer prompt already supports page type and article type, making it a good propagation target once lane role exists.
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\scheduler\jobs.py`
  - current flow has a clean insertion point between keyword selection/catalog match and title generation.

## Proposed Solution

### 1. Introduce a page-role classifier
Add a deterministic lane classifier before title generation.

#### Proposed model additions
Add to `SEOContext`:
- `content_lane`: `traffic_entry | procurement_conversion`
- `content_lane_confidence`: float
- `content_lane_signals`: optional structured dict for debugging and tests
- `search_stage`: optional normalized stage like `awareness | consideration | decision`

#### Proposed implementation surface
- New or expanded logic in one of:
  - a dedicated service such as `src/services/content/page_role_router.py`, or
  - an expanded `intent_analyzer.py` if keeping routing logic centralized is cleaner.

#### Routing signals
- Keyword wording
  - commercial: supplier, wholesale, manufacturer, MOQ, quote, customization, audit, lead time
  - traffic-entry: application, vs, difference, problem, compatibility, material choice, use case, selection criteria
- Product type strength
  - exact product head + size/material/product format should bias toward `procurement_conversion`
- Search stage
  - decision-stage terms raise commercial routing score
  - awareness/consideration scenario terms raise traffic-entry routing score
- Catalog fit
  - existing matched product/category/tag context increases procurement confidence

#### Core routing rule
- If query is product-head and catalog-fit is strong, default to `procurement_conversion` unless the search-stage evidence strongly favors `traffic_entry`.

### 2. Redesign title families by lane
Replace the current compressed tail logic with lane-specific title families.

#### Procurement-conversion title families
Use for product-head/commercial pages. Families should vary beyond MOQ-only framing:
- supplier qualification and audit
- quote comparison and cost drivers
- customization and packaging constraints
- sample approval and production risk
- compliance, QC, and shipment readiness
- shortlist / buyer-decision matrix

Example directional outputs:
- `100ml Dropper Bottle Supplier Selection: Samples, QC, and Quote Benchmarks`
- `100ml Dropper Bottle Wholesale: Customization Limits, MOQ Drivers, and Audit Checks`
- `100ml Dropper Bottle Buying Criteria: Lead Time Risks, Packaging Specs, and Supplier Fit`

#### Traffic-entry title families
Use for search-demand expansion without encyclopedia tone:
- application fit and use-case mapping
- spec interpretation and compatibility
- comparison / tradeoff analysis
- problem/risk avoidance
- scenario-based selection logic

Example directional outputs:
- `100ml Dropper Bottle for Essential Oils: Glass vs PET and Leak-Risk Tradeoffs`
- `How to Choose a 100ml Dropper Bottle for Serum Packaging Without Closure Mismatch`
- `100ml Dropper Bottle Material Selection: UV Protection, Dosing Accuracy, and Filling Fit`

### 3. Propagate lane into planner + writer

#### Planner changes
Update `ContentPlannerService` prompts so article-format planning considers both:
- lane role
- article format

Expected effect:
- `traffic_entry` pages can still be `comparison`, `how_to`, or `general`, but should open from scenario/problem framing.
- `procurement_conversion` pages should produce outlines centered on supplier evaluation, customization, qualification, proofing, and next-step procurement actions.

#### Writer changes
Update `ContentCreatorAgent` prompt building to include explicit lane instructions:
- `traffic_entry`
  - open on scenario / fit / risk / application problem
  - CTA bridges readers to relevant category/tag/product pages without sounding encyclopedic
- `procurement_conversion`
  - open on buying decision stakes
  - enforce evidence blocks such as supplier-fit criteria, quotation variables, sample/QC steps, and negotiation/checklist modules

### 4. Reduce over-normalization in title cleanup
Keep `_finalize_title()` cleanup for readability, but remove or relax logic that collapses many distinct tails into the same phrase bucket.

Guardrails:
- avoid duplicate tokens and dangling connectors,
- keep SEO-safe length,
- preserve lane-specific differentiators,
- avoid converting many variants back into the same 3-tail formula.

### 5. Align selection strategy with lane goals
Update title selection so `select_best_title()` balances:
- keyword match,
- lane fit,
- CTR estimate,
- title-family diversity.

Potential policy:
- `procurement_conversion` prefers commercially specific titles when match/CTR are close.
- `traffic_entry` prefers scenario/problem/comparison titles over generic guide phrasing.

## File-Level Plan

### `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\models\seo_context.py`
- Add content-lane fields.
- Include them in `to_content_creator_task()`.
- Keep backward compatibility defaults.

### `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\services\content\intent_analyzer.py`
- Expand from shallow intent triggers toward routing-signal extraction.
- Support search-stage inference and product-head detection helpers.

### `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\services\content\hook_optimizer.py`
- Add lane-aware title family generation.
- Replace repeated-tail compression with controlled families.
- Update scoring/selection to consider lane fit.

### `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\services\content\content_planner.py`
- Include lane in planning prompt.
- Ensure outline shape changes when lane changes, not just when article format changes.

### `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\agents\content_creator.py`
- Add lane-aware opening/section/CTA guidance.
- Preserve anti-generic and anti-beginner constraints.

### `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\scheduler\jobs.py`
- Insert routing step before title generation.
- Persist lane data into `SEOContext` before planner/writer execution.
- Keep current fallback behavior sane when routing confidence is low.

### Tests to update/add
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\tests\services\content\test_hook_optimizer_integration.py`
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\tests\unit\content\test_hook_optimizer.py`
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\tests\agents\test_content_creator_integration.py`
- add router-focused unit coverage near `tests\services\content\` or `tests\unit\content\`

## Stories / Execution Sequence

### Story 1 - Lane modeling and routing
Deliverables:
- content-lane schema in SEOContext
- routing utility/service
- scheduler integration

Acceptance:
- product-head terms like `dropper bottle 100ml` route to `procurement_conversion`
- scenario/comparison/problem terms can route to `traffic_entry`

### Story 2 - Lane-specific title generation
Deliverables:
- revised title-family generation in `HookOptimizer`
- reduced tail over-normalization
- lane-aware title selection

Acceptance:
- titles from different lanes no longer converge to the same `MOQ, Lead Time, Buyer Checks` form
- titles remain keyword-aligned and length-safe

### Story 3 - Planner and writer propagation
Deliverables:
- planner prompt updated to consume lane
- writer prompt updated to consume lane
- lane-specific opening, section, FAQ, and CTA guidance

Acceptance:
- body structure visibly differs between traffic-entry and procurement-conversion pages
- banned tones/patterns remain absent

### Story 4 - Validation and rollout safety
Deliverables:
- tests covering routing, title families, and writer prompt behavior
- spot-check examples for representative queries

Acceptance:
- existing core tests pass after updates
- new route/title diversity checks prevent regression into single-template headlines

## Architect Review

### Steelman antithesis
A lighter-weight plan would only tune `HookOptimizer` tails and keep the rest of the system unchanged. This minimizes risk and likely removes the ugliest repetitive titles quickly.

### Why not chosen
That approach leaves the core mismatch unresolved: the system still decides too late, after the commercial framing has already dominated the topic. The result would be nicer wording on top of the same monoculture.

### Real tradeoff tension
- More routing logic improves relevance and diversity.
- More routing logic also increases test surface and the chance of misclassification.

### Synthesis
Use deterministic, inspectable routing signals with conservative defaults instead of a freeform LLM classifier. This preserves debuggability while still fixing the root cause.

## Critic Evaluation
- Principle / option consistency: PASS
- Alternatives fairly considered: PASS
- Risks identified: PASS
- Acceptance criteria testable: PASS
- Verification path concrete: PASS
- Verdict: APPROVE

## Risks and Mitigations
- Risk: routing misclassifies borderline queries.
  - Mitigation: store confidence + signals; default product-head queries to procurement lane.
- Risk: titles become more varied but less keyword-matched.
  - Mitigation: keep `TitleQueryMatcher` as a hard signal in selection.
- Risk: writer prompts diverge too much and hurt conversion consistency.
  - Mitigation: preserve shared buyer-value requirements across both lanes.
- Risk: older tests lock in the old commercial-tail style.
  - Mitigation: rewrite assertions around lane fit and diversity instead of exact old phrasing.

## ADR
- Decision: add deterministic content-lane routing before title generation and propagate lane-specific title/planner/writer behavior.
- Drivers: fix title homogenization, preserve equal traffic/conversion goals, keep product-head queries commercially aligned.
- Alternatives considered:
  - tail-only cleanup in `HookOptimizer`
  - AI-only rewriting pass after generation
- Why chosen: only the lane-aware approach solves both search breadth and conversion focus without relying on unstable stylistic rewrites.
- Consequences:
  - more files touched,
  - wider test updates,
  - better long-term control over search coverage and body-role alignment.
- Follow-ups:
  - validate representative query sets after rollout,
  - monitor whether lane defaults need tuning by category/product family.

## Available Agent Types Roster
Recommended if execution is launched later:
- `architect`: confirm routing boundaries and fallback rules
- `executor`: implement router + title/planner/writer changes
- `test-engineer`: add route/title/prompt regression coverage
- `verifier`: validate representative query outputs and pipeline behavior
- `critic`: optional final review before publish-ready signoff

## Staffing Guidance

### If executing via `$ralph`
Use a single-owner sequence:
1. schema + router
2. hook optimizer
3. planner/writer propagation
4. tests
5. verification

Suggested reasoning:
- leader/frontier: high
- verification passes: medium to high

### If executing via `$team`
Suggested lanes:
- Lane A (`executor`): `seo_context.py` + routing insertion in `jobs.py`
- Lane B (`executor`): `hook_optimizer.py` + `intent_analyzer.py`
- Lane C (`executor` or `writer`): `content_planner.py` + `content_creator.py`
- Lane D (`test-engineer`): route/title/prompt tests
- Final lane (`verifier`): representative keyword/output validation

Suggested reasoning by lane:
- routing/title lanes: high
- planner/writer lane: medium-high
- test lane: medium
- verifier lane: high

## Launch Hints
- Sequential execution: `$ralph C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\.omx\plans\prd-seo-title-direction-upgrade.md`
- Parallel execution: `$team C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\.omx\plans\prd-seo-title-direction-upgrade.md`

## Team Verification Path
1. Run routing unit tests for product-head, scenario, comparison, and problem-intent queries.
2. Run title generation tests ensuring lane-specific diversity and length safety.
3. Run content prompt tests ensuring lane-specific instructions appear and banned phrases remain absent.
4. Perform representative fixture validation for at least:
   - `dropper bottle 100ml`
   - one `vs` query
   - one application-fit query
   - one supplier/audit query
5. Confirm quality-gate expectations still pass for both lane types.

## Done Definition
The plan is complete when execution can proceed without reopening requirements discovery, and the implementation team can point to exact files, acceptance criteria, and verification steps.
