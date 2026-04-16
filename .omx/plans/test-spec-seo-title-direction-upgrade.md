# Test Spec - SEO Title Direction Upgrade

## Scope
Validate the lane-aware title/content-direction upgrade planned in `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\.omx\plans\prd-seo-title-direction-upgrade.md`.

## Test Objectives
1. Verify routing chooses the correct lane using keyword wording, product type, and search stage.
2. Verify title generation differs by lane and no longer collapses into one repeated commercial template.
3. Verify content planning and writer prompts reflect lane role.
4. Verify query match, SEO length safety, and commercial relevance remain intact.

## Test Levels

### Unit Tests

#### A. Routing / signal extraction
Target files:
- `src/services/content/intent_analyzer.py` or the new router module
- `src/scheduler/jobs.py` integration helper if routing is inserted there

Cases:
1. product-head keyword defaults to `procurement_conversion`
   - input: `dropper bottle 100ml`
   - expect: procurement lane, medium/high confidence
2. supplier/commercial term routes to `procurement_conversion`
   - input: `dropper bottle supplier`
3. comparison query can route to `traffic_entry`
   - input: `glass vs pet dropper bottle for serum`
4. application-fit query can route to `traffic_entry`
   - input: `best dropper bottle material for essential oils`
5. mixed query with strong product + commercial clues still routes commercial
   - input: `100ml dropper bottle wholesale customization`
6. low-confidence ambiguous query still returns a sane default and exposes signals

Assertions:
- lane value
- confidence range
- signal payload / reasons present

#### B. Hook optimizer title-family behavior
Target file:
- `src/services/content/hook_optimizer.py`

Cases:
1. procurement lane titles use commercial decision framing without repeating the same suffix across hooks
2. traffic lane titles use scenario/comparison/spec/problem framing without encyclopedic tone
3. `_finalize_title()` keeps titles under SEO-safe length while preserving distinguishing tails
4. old collapse pattern regression test
   - multiple hook variants should not all normalize to the same `MOQ, Lead Time, Buyer Checks` family
5. keyword match remains acceptable via `TitleQueryMatcher`

Assertions:
- set diversity across generated titles
- forbidden patterns absent
- title length <= configured max
- keyword match score >= acceptable threshold for selected title

#### C. SEOContext propagation
Target file:
- `src/models/seo_context.py`

Cases:
1. lane fields serialize into `to_content_creator_task()`
2. default backward compatibility works when lane fields are missing

### Integration Tests

#### D. Scheduler -> SEOContext -> planner/writer flow
Target files:
- `src/scheduler/jobs.py`
- `src/services/content/content_planner.py`
- `src/agents/content_creator.py`

Cases:
1. procurement query populates SEOContext with procurement lane before title generation
2. traffic-entry query populates SEOContext with traffic lane and produces different planner/writer instructions
3. selected title, lane, article type, and prompt body stay synchronized through content generation task creation

Assertions:
- lane present in SEOContext
- planner prompt includes lane-aware framing
- writer prompt includes lane-specific opening / section / CTA expectations

#### E. ContentCreator prompt behavior
Target file:
- `tests/agents/test_content_creator_integration.py`

Add assertions for:
- procurement lane prompt includes supplier-fit / quote / QC / sampling guidance
- traffic-entry lane prompt includes scenario / comparison / application / risk guidance
- banned phrases remain absent in both lanes

## Representative Fixtures
Use at minimum these keywords in tests or fixture-based verification:
- `dropper bottle 100ml`
- `dropper bottle supplier`
- `glass vs pet dropper bottle for serum`
- `best dropper bottle material for essential oils`
- `100ml dropper bottle wholesale customization`

## Regression Constraints
Must continue to protect:
- H1 equals `title_must_use`
- title query matching stays enforced
- quality-gate catalog expectations still pass for procurement pages
- SEO title length remains within configured bounds

## Manual / Snapshot Verification
After automated tests, run example generation or prompt snapshots for both lanes and review:
1. procurement example should read like a buyer-decision page, not a beginner guide
2. traffic-entry example should read like a search-value entry page, not an encyclopedia article
3. both examples should preserve professional tone and application/buyer value

## Failure Conditions
The implementation fails this spec if any of the following happen:
- product-head terms stop defaulting to procurement lane
- traffic-entry titles still collapse into procurement FAQ phrasing
- planner/writer prompts ignore lane role
- titles become more varied but lose keyword match or SEO length safety
- banned patterns such as `Complete Guide` or repeated `Buyer Checks` templates reappear broadly

## Recommended Command Sequence for Execution Stage
When implementation begins, verify in roughly this order:
1. focused router tests
2. hook optimizer tests
3. content creator prompt tests
4. broader integration tests touching scheduler/content flow

## Exit Criteria
This test plan is complete when execution can verify lane routing, title diversity, prompt propagation, and SEO safety without reopening planning.
