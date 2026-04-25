# Test Spec - GSC Demand-Priority Refactor

## Scope

Validate the cluster-priority SEO upgrade defined in `C:\Users\DJS Tech\ZenflowProjects\bobopkgproject\.omx\plans\prd-gsc-priority-upgrade.md`.

## Test Objectives

1. Verify cluster assembly groups related GSC query/page demand correctly.
2. Verify mixed scoring ranks customer-value clusters above generic informational traffic.
3. Verify action selection can choose different next actions for different clusters.
4. Verify scheduler dispatch reuses the correct executor without breaking fallback behavior.
5. Verify admin-pasted steering inputs guide ranking without overriding core demand validation.
6. Verify selector safety, shadow success gates, and rollback controls are testable.
7. Verify action logging and API exposure are consistent.
8. Verify GSC readiness, credential resolution parity, and opportunity materialization keep the pool non-empty when demand exists.

## Unit Tests

### A. Cluster Assembly
Target area:
- new cluster service
- existing topic-map helpers in [src/services/topic_map.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/services/topic_map.py):176 and :347

Cases:
1. similar commercial queries mapping to the same product/category page form one cluster
2. tutorial-like support queries attach to a conversion cluster as support, not as a separate primary cluster
3. unrelated informational demand does not merge into a commercial cluster
4. multiple pages for the same query trigger cluster health warnings or cannibalization penalties

Assertions:
- cluster id stability for equivalent input
- correct primary page / hub selection
- support-role labeling is explicit

### B. Mixed Scoring
Target area:
- new mixed scorer
- reusable logic from [src/agents/opportunity_scoring.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/agents/opportunity_scoring.py):154, :202, :254

Cases:
1. high-impression but weak-commercial informational cluster loses to a lower-impression commercial cluster
2. cluster with strong existing page + poor CTR is ranked for optimization instead of new content
3. cluster with weak internal link coverage receives a stronger internal-link action score
4. cluster with no credible business value cannot win only on impressions
5. cluster with support-page gap can recommend supporting content without becoming a primary informational play
6. a cluster matching `REFERENCE_KEYWORDS` receives only bounded uplift and cannot leapfrog clearly higher-value clusters on keyword boost alone
7. a cluster matching `NEGATIVE_KEYWORDS` is suppressed or excluded according to policy
8. a cluster matching `COMMERCIAL_PRIORITY_TERMS` gets a commercial weighting boost without bypassing other factors

Assertions:
- score breakdown contains all required factors
- no single factor overrides all others by accident
- ranking order matches business intent
- steering boost/suppression is visible in the breakdown
- steering total effect is capped at `0.12`
- monotonic constraints hold for demand, conversion proximity, and negative-keyword conflict

### C. Action Selection
Target area:
- new action selector

Cases:
1. choose `ctr_optimize` when page already ranks and demand exists but CTR underperforms
2. choose `page_refresh` when page demand exists and content/coverage is weak
3. choose `internal_link_push` when cluster assets exist but internal support is poor
4. choose `supporting_content_create` when demand exists but the cluster lacks support assets
5. choose `backlink_support` only when other on-site opportunities are weaker and authority need is explicit
6. confidence `>= 0.75` is authoritative eligible
7. confidence `0.60 - 0.74` remains recommendation-only
8. confidence `< 0.60` triggers fallback
9. duplicate decision key inside the 24h window does not enqueue duplicate execution

Assertions:
- exactly one primary action
- optional secondary actions are lower-ranked and explainable
- fallback reason is explicit when selector does not promote an action
- decision key idempotency holds under repeated runs

## Integration Tests

### D. Scheduler Integration
Target files:
- [src/scheduler/jobs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/scheduler/jobs.py):1157, :2354, :2534, :2914

Cases:
1. shadow mode computes cluster decisions without changing current execution
2. live mode dispatches chosen cluster action to the right existing executor
3. low-confidence engine result falls back to old logic safely
4. action-family feature flags can enable or disable authority independently
5. global kill switch restores baseline selector

Assertions:
- no executor mismatch
- fallback path still works
- logs contain cluster id, selected action, and score breakdown
- authoritative path can be disabled without breaking baseline behavior

### E. Opportunity API
Target file:
- [src/api/opportunities.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/api/opportunities.py):115

Cases:
1. list endpoint returns cluster-aware fields
2. sorting and filtering still work with new action-family metadata
3. cluster opportunities can be inspected without losing current score/position/impression fields
4. response can show whether admin steering inputs influenced ranking

### F. Admin Config Integration
Target files:
- [src/api/admin.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/api/admin.py):105 and :171
- [static/admin/index.html](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/static/admin/index.html)
- [static/admin/script.js](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/static/admin/script.js)

Cases:
1. `/admin` can save and reload `REFERENCE_KEYWORDS`
2. blank lines and duplicate lines are normalized safely
3. masked/secret handling does not interfere with non-secret steering fields
4. field help text makes clear these values guide ranking and do not force generation

### G. Action Logging
Target files:
- [src/models/job_runs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/job_runs.py):121
- [src/models/content_action.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/content_action.py):10

Cases:
1. canonical model writes before/after metrics consistently
2. executed action logs cluster linkage and decision snapshot
3. duplicate-model ambiguity is removed or guarded by tests
4. dual-write parity mismatch rate can be measured
5. read cutover criteria `< 1%` mismatch for `7` consecutive days can be evaluated

### H. GSC Connection And Persistence Integrity
Target files:
- [src/api/gsc.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/api/gsc.py)
- [src/api/admin.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/api/admin.py)
- [src/scheduler/jobs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/scheduler/jobs.py)
- [src/integrations/gsc_client.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/integrations/gsc_client.py)
- [src/models/gsc_data.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/gsc_data.py)

Cases:
1. admin can save/load `GSC_ENABLED` and the effective runtime gate updates immediately
2. `/api/v1/gsc/status` returns `503` when `GSC_ENABLED=False` and valid health payload when `GSC_ENABLED=True`
3. scheduler and API both construct GSC client through the same credential policy
4. `GSC_CREDENTIALS_PATH` mode works for both scheduler and API, not only `GSC_CREDENTIALS_JSON`
5. live GSC opportunities can be materialized into `Opportunity` via dedicated sync path even when `content_generation_job` is not triggered
6. repeated sync in the same decision window does not create duplicate opportunity rows
7. when live GSC has demand rows, persisted opportunity pool receives rows within one sync window under enabled bridge flag
8. when persistence bridge is disabled, system degrades gracefully and reports explicit status rather than silently empty data

Assertions:
- GSC readiness contract is consistent across admin status, API, and scheduler logs
- credential resolution mismatch cannot happen between API and scheduler
- opportunity materialization path is independent from content generation cadence
- idempotency key behavior prevents duplicate pool rows
- disabled states are explicit and auditable

## Additional Safety Tests

### I. Shadow Gate Evaluation
Cases:
1. pass scenario where business-value precision improvement is `>= +20%`
2. fail scenario where execution failure rate increases more than `+2%` absolute
3. fail scenario where duplicate/cannibalization incidents increase more than `+5%`
4. fail scenario where steering cap violations are non-zero

Assertions:
- gate evaluator emits pass/fail by criterion
- failing any criterion extends shadow by `7 days`

### J. Rollback Drill
Cases:
1. disable action-family authority flags and confirm baseline selector resumes
2. trigger global kill switch and confirm authoritative selector stops
3. flush queued non-idempotent cluster jobs not yet started
4. export last 24h decision traces for review
5. disable GSC persistence bridge and dedicated shadow-sync lane; confirm baseline paths remain healthy
6. re-enable bridge/sync flags and confirm pool resumes materialization without historical duplication

Assertions:
- rollback completes without breaking baseline scheduler behavior
- incident review bundle is generated

### K. Observability Completeness
Cases:
1. each selected cluster emits `cluster_id`, `cluster_version`, member summary, factor values, steering modifiers, selected action, confidence, fallback reason
2. missing trace rate alert fires when completeness drops below `99%`
3. readiness payload includes schema state, GSC gate state, and persistence-bridge state
4. alerting fires when live GSC opportunities remain non-zero while persisted pool remains zero beyond one sync window

## Representative Fixtures

Use clusters that cover:
- direct commercial queries
- mixed-intent support queries
- high-impression generic informational demand
- one cluster with clear CTR problem
- one cluster with internal-link gap
- one cluster needing supporting content
- one cluster matching pasted reference keywords
- one cluster matching negative keywords

## Manual Verification

1. Run shadow mode and inspect top 20 cluster recommendations.
2. Confirm top recommendations are dominated by customer-value demand, not generic tutorial traffic.
3. Inspect at least one example for each selected action family.
4. Compare old selection vs new selection for the same GSC window and review whether the new engine makes more commercially coherent choices.
5. Paste a small curated keyword list in `/admin` and confirm it nudges ranking without force-generating low-value topics.
6. Run a staging rollback drill and confirm baseline selector restoration.
7. Flip `GSC_ENABLED` off/on and verify API + scheduler behavior remains consistent.
8. Validate opportunity pool can be backfilled from live GSC without triggering content generation.

## Observability Checks

Required debug output per selected cluster:
- cluster id and members
- score breakdown by factor
- matched admin steering inputs
- primary action and reason
- fallback status
- executor result
- effective GSC readiness state and credential source mode
- live-opportunity count vs persisted-opportunity count in the same window

## Failure Conditions

The upgrade fails this spec if:

- generic informational clusters dominate top-ranked recommendations
- the engine always chooses new content regardless of context
- support content is promoted as a primary goal without conversion-cluster linkage
- admin-pasted reference keywords can force low-value topics into top rank by themselves
- selector authority cannot be disabled cleanly
- shadow mode cannot explain why it selected a cluster/action
- action logging remains ambiguous across duplicate `ContentAction` models
- fallback behavior breaks the current autopilot flow
- API and scheduler use different GSC credential resolution behavior
- live GSC opportunities are non-zero while persisted opportunity pool remains zero beyond one sync window with bridge enabled
- required migration columns are missing but authoritative mode still executes

## Recommended Verification Sequence

1. cluster assembly unit tests
2. mixed scoring unit tests
3. action selection unit tests
4. scheduler integration tests
5. admin config integration tests
6. opportunity API tests
7. ContentAction migration parity tests
8. GSC connection/persistence integrity tests
9. shadow-gate evaluator tests
10. rollback drill
11. shadow-mode manual review

## Exit Criteria

This plan is validated when:

- cluster-based decisions are explainable
- steering inputs remain bounded and no-bypass
- selected actions vary appropriately by cluster state
- production rollout can begin in shadow mode without replacing the old engine immediately
- authoritative promotion is gated by measurable evidence
- action results can be measured consistently after execution
- GSC read path and opportunity-persistence path are operationally coupled by explicit, test-covered contracts
