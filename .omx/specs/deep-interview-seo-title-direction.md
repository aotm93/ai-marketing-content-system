# Deep Interview Spec - SEO Title Direction Upgrade

## Metadata
- Profile: standard
- Rounds: 6
- Final ambiguity: 0.14
- Threshold: 0.20
- Context type: brownfield
- Context snapshot: `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\.omx\context\seo-title-direction-20260416T000000Z.md`
- Transcript summary: `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\.omx\interviews\seo-title-direction-20260416T000500Z.md`

## Clarity breakdown
| Dimension | Score | Notes |
| --- | --- | --- |
| Intent clarity | 0.97 | Upgrade title/content direction to be search-demand-aligned and commercially useful, not template-like. |
| Outcome clarity | 0.94 | Achieve equal weight across broader Google traffic acquisition and procurement conversion. |
| Scope clarity | 0.90 | Changes likely touch title generation, routing logic, content planning, and writer prompts. |
| Constraint clarity | 0.90 | Explicit bans and editorial constraints are now clear. |
| Success criteria clarity | 0.82 | Direction is clear; measurable KPIs still need planning-stage operationalization. |
| Context clarity | 0.88 | Brownfield touchpoints identified across title optimizer, intent analysis, planner, and content creator. |

## Intent (why)
The current system still generates repetitive titles with nearly identical structures, especially around `MOQ / Lead Time / Buyer Checks`. This weakens search coverage, reduces title professionalism, and fails to match diverse user search needs. The user wants a higher-value SEO system that can win more Google traffic while still converting commercial buyers.

## Desired outcome
Build an upgraded title and content-direction system that:
- expands beyond one-note procurement FAQ phrasing,
- captures broader search demand from multiple intent stages,
- preserves strong procurement-conversion performance for product/commercial keywords,
- writes titles and article direction in a way that feels professional, search-aligned, and commercially credible.

## In scope
- Rework title strategy so the system no longer collapses distinct topics into the same headline format.
- Introduce automatic content-role routing before title generation.
- Support at least two content lanes:
  - search-traffic entry pages
  - procurement-conversion pages
- Use combined signals from:
  - keyword wording
  - product type
  - search stage
- Upgrade title-writing direction to reflect page role and actual search demand.
- Upgrade content planning/writing direction so the resulting article matches the title role.

## Out of scope / Non-goals
The upgraded system must avoid:
- encyclopedia-style explanatory writing,
- beginner-tutorial tone,
- clickbait headlines,
- uniform `MOQ / Lead Time` template tails across topics,
- generic `Complete Guide` style headlines,
- content without application scenarios,
- content without buyer decision perspective.

## Decision boundaries
OMX may decide without further confirmation:
- how to model the two content lanes internally,
- how to score and combine routing signals,
- how to redesign title families per lane,
- how to update planner/writer prompts so the title role propagates into article structure.

OMX should preserve these fixed business rules:
- `拓宽流量面` and `强化采购转化` remain equally important.
- Product-head queries should default to procurement-conversion unless strong evidence suggests another lane.
- Informational traffic expansion should come from dedicated entry-page logic, not by turning every product query into a generic educational article.

## Constraints
- No new dependencies unless explicitly requested.
- Preserve query relevance; do not trade search match for stylistic variety.
- Keep titles professional and commercially credible.
- The current system is brownfield; changes must fit existing SEO/content pipeline.
- Title/H1 synchronization remains important, so weak title strategy cannot be treated as isolated from body-content planning.

## Testable acceptance criteria
1. Title generation no longer compresses different product/support topics into the same repeated tail patterns by default.
2. The system can classify a topic into at least two distinct page roles before selecting a title strategy.
3. Product-head queries like `dropper bottle 100ml` route to procurement-conversion by default.
4. Search-expansion topics can route to non-commercial entry-page structures without sounding encyclopedic or beginner-focused.
5. Generated titles vary by page role and search stage, not just by swapping product nouns.
6. Content planning and writing prompts reflect the selected page role so the article body matches the search intent behind the title.
7. The resulting title families avoid banned patterns such as repetitive `MOQ, Lead Time, Buyer Checks` tails and generic `Complete Guide` phrasing.

## Assumptions exposed + resolutions
- Assumption: broader traffic and stronger conversion compete with each other.
  - Resolution: they are equal-priority objectives and should be handled through routing, not compromise headlines.
- Assumption: broader traffic means product terms should become informational pages.
  - Resolution: false. Product-core queries still default to procurement-conversion.
- Assumption: routing can be handled with surface keyword triggers only.
  - Resolution: false. Routing must combine keyword wording, product type, and search stage.

## Pressure-pass findings
- Revisited answer: the equal weighting between traffic expansion and procurement conversion.
- Stress test: `dropper bottle 100ml`
- What changed: clarified that business strategy is not “mixed everything into every page”; it is “automatic split into two lane types, with product-head terms defaulting to commercial conversion.”

## Brownfield evidence vs inference
### Direct evidence from code
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\services\content\hook_optimizer.py`
  - `_catalog_tail_for_hook()` defines repeated commercial tails for multiple hook/page types.
  - `_shorten_tail()` further normalizes many variants back into the same short formulas.
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\services\content\intent_analyzer.py`
  - current intent detection is keyword-trigger based and may over-bias toward buying-guide phrasing.
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\agents\content_creator.py`
  - `title_must_use` is enforced as the H1, so title strategy directly shapes the article role.

### Inference
- The current architecture likely needs page-role classification before title generation, not just better tail text.
- Tests that assert existing wholesale-style titles may need to be updated to avoid reinforcing the old pattern.

## Technical context findings
Likely implementation touchpoints:
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\services\content\hook_optimizer.py`
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\services\content\intent_analyzer.py`
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\services\content\content_planner.py`
- `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\src\agents\content_creator.py`
- tests under:
  - `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\tests\services\content\`
  - `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\tests\agents\`
  - `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\tests\unit\content\`

## Recommended planning targets for the next stage
- Define a page-role classifier with explicit lane outputs and fallback behavior.
- Redesign title families per lane:
  - traffic-entry families: scenario, comparison, failure/risk, selection logic, application fit, specification interpretation
  - procurement-conversion families: supplier evaluation, MOQ/cost drivers, customization, qualification, audit, quotation comparison
- Update planner prompts so role-specific outlines differ meaningfully.
- Update writer prompts so article openings, sectioning, and CTA logic follow lane type.
- Add tests for routing behavior and title diversity by page role.
