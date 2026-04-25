# PRD - GSC Demand-Priority Refactor

## Status
- Workflow: `$ralplan` / consensus planning
- Based on: [deep-interview-gsc-priority-upgrade.md](/C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/.omx/specs/deep-interview-gsc-priority-upgrade.md)
- Consensus verdict: APPROVE
- Architect verdict: APPROVE
- Critic verdict: APPROVE
- Execution recommendation: `$ralph` for controlled staged rollout, `$team` for parallel implementation once the migration and safety contracts are accepted

## RALPLAN-DR Summary

### Principles
1. Demand-first: prioritize validated GSC demand before net-new ideation.
2. Conversion-weighted: optimize for inquiry/conversion value, not raw traffic.
3. Cluster decisioning with hard safety contracts: decisions must be explainable, bounded, and reversible.
4. Bounded human steering: admin inputs can guide ranking, but they never bypass core gates.
5. Sidecar-first rollout: prove value in shadow mode before authoritative takeover.

### Decision Drivers
1. Current orchestration uses GSC mainly as a keyword source, not as a cross-action priority engine.
2. Existing brownfield modules already cover refresh, internal-link, content, and backlink execution, but action selection is fragmented.
3. Production rollout safety requires measurable gates, feature flags, fallback behavior, and rollback controls.

### Viable Options

#### Option A - Query-centric enhancement only
- Approach: improve the existing opportunity flow without introducing cluster-level orchestration.
- Pros: smallest diff, fastest ship, lower immediate change surface.
- Cons: does not solve cross-action arbitration, weak fit for conversion-path decisioning, limited long-term explainability.

#### Option B - Cluster-priority orchestrator as sidecar, then progressive promotion (Chosen)
- Approach: build a cluster assembler + governed scorer + action selector above existing executors; run shadow-first, then progressively promote by action family.
- Pros: aligned with business objective, reuses current brownfield components, supports mixed scoring and dynamic action selection, strong rollout safety story.
- Cons: higher governance complexity, more schema/API/admin coordination, requires observability and migration discipline.

#### Option C - New-content-first pipeline with better filters
- Approach: keep content generation as the primary action but improve keyword filtering and commercial weighting.
- Pros: simple mental model, low conceptual overhead.
- Cons: repeats the current bias, overproduces content when existing pages should be optimized first, weak cluster and conversion-path reasoning.

### Chosen Direction
Choose Option B, but not as an immediate authoritative control plane. Build it as a read-only sidecar first, measure it in shadow mode, then progressively promote it by action family: CTR and refresh first, internal links second, supporting content third, backlinks last.

## Requirements Summary

The production SEO system should stop treating Google Search Console as just one keyword source and instead use GSC as a demand-validation layer for a cluster-level priority engine. The engine should rank topic/page clusters by customer-value potential and dynamically choose the best next action for each cluster: page optimization, content refresh, internal links, supporting content, or backlinks.

The user explicitly does **not** want generic informational/tutorial/science traffic as the primary objective. Informational-looking pages can exist only as support assets for conversion-driving clusters.

## Problem Statement

Current orchestration favors source precedence over action prioritization:

- `content_generation_job` first tries GSC, but mainly to select a new keyword for content generation rather than to choose the best action for an existing demand cluster in [src/scheduler/jobs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/scheduler/jobs.py):1157 and [src/scheduler/jobs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/scheduler/jobs.py):1238.
- GSC can already provide raw query/page analytics, low-hanging fruits, and declining pages in [src/integrations/gsc_client.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/integrations/gsc_client.py):160, [src/integrations/gsc_client.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/integrations/gsc_client.py):239, and [src/integrations/gsc_client.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/integrations/gsc_client.py):287.
- Opportunity scoring exists, but it remains query-centric and action-specific in [src/agents/opportunity_scoring.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/agents/opportunity_scoring.py):53, [src/agents/opportunity_scoring.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/agents/opportunity_scoring.py):154, [src/agents/opportunity_scoring.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/agents/opportunity_scoring.py):202, and [src/agents/opportunity_scoring.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/agents/opportunity_scoring.py):254.
- Topic clustering and link intelligence already exist in [src/models/gsc_data.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/gsc_data.py):215 and [src/services/topic_map.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/services/topic_map.py):140, but they are not the main decision unit for production action selection.
- Refresh, internal linking, and backlink jobs run independently in [src/scheduler/jobs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/scheduler/jobs.py):2354, [src/scheduler/jobs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/scheduler/jobs.py):2534, and [src/scheduler/jobs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/scheduler/jobs.py):2914 rather than being chosen by a common action selector.
- GSC readiness is not a single contract today: `/api/v1/gsc/*` respects `gsc_enabled`, but scheduler-side usage can still bypass that gate and depend directly on `gsc_site_url + gsc_credentials_json`.
- The opportunity pool is not the same as live GSC preview. Operators can have valid GSC data and still see an empty `/api/v1/opportunities` result because persistence is coupled to a narrow shadow path instead of an explicit materialization lane.

## Goals

1. Make the priority engine cluster-based instead of single-keyword based.
2. Use a mixed-score model across GSC demand, keyword intent, page type, conversion proximity, and support potential.
3. Dynamically choose the best action for each cluster rather than always generating new content first.
4. Bias the system toward inquiry/conversion-oriented traffic growth.
5. Preserve brownfield reuse of existing GSC, cluster, refresh, internal-link, and backlink modules.
6. Add admin-configurable steering inputs so operators can paste reference keywords and guide generation without bypassing demand validation.
7. Add measurement and rollback-safe shadow mode before the new engine becomes authoritative.
8. Unify GSC runtime behavior across admin, API, scheduler, and sync jobs.
9. Guarantee that raw GSC sync and opportunity materialization can run without content-generation selection.
10. Make operators able to distinguish GSC connectivity, raw-data freshness, persisted-pool freshness, and schema readiness.
11. Keep preview and persisted execution surfaces explicit so empty-pool states are diagnosable.

## Non-goals

- Maximize generic traffic regardless of business value.
- Treat tutorial/informational/science terms as primary targets by default.
- Replace the entire scheduler stack in one migration.
- Add new third-party dependencies.
- Build a perfect attribution system before V1 prioritization ships.
- Turn admin-pasted keywords into a hard publish queue that bypasses GSC, cluster scoring, deduplication, or publishability checks.
- Hide disabled GSC, missing migrations, or disabled persistence behind a silent empty opportunity pool.

## Planning Anchors From Current Google Guidance

These are interpretation anchors for the plan, not copied rules:

- Google prioritizes helpful, reliable, people-first content over content made mainly to capture clicks.
- Search Console Performance should be used to understand which queries and pages already show demand.
- Title links and snippets should be descriptive and useful, not stuffed or templated.
- Important pages should be internally linked with descriptive anchor text.
- Site structure and URL hierarchy should be crawl-friendly and stable.

Official references:
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- https://support.google.com/webmasters/answer/7576553
- https://developers.google.com/search/docs/appearance/title-link
- https://developers.google.com/search/docs/appearance/snippet
- https://developers.google.com/search/docs/crawling-indexing/links-crawlable
- https://developers.google.com/search/docs/specialty/ecommerce/designing-a-url-structure-for-ecommerce-sites

## Proposed Architecture

### Decision Unit

Use a `demand cluster` as the unit of prioritization:

- cluster root intent or commercial theme
- one or more GSC query/page pairs
- one primary target page or hub page
- zero or more support pages
- internal-link candidates
- backlink-support candidates

### Admin Steering Inputs

Use admin-provided keyword guidance as `soft steering inputs`, not as a source of hard overrides.

V1 minimum:

- `reference_keywords`
  - pasted manually in `/admin`
  - one keyword per line
  - boosts related clusters and candidate topics

Recommended extended shape:

- `reference_keywords`
- `negative_keywords`
- `commercial_priority_terms`
- `priority_target_pages`

Core rule:

- admin steering inputs may influence ranking and tie-breaking
- they must not bypass:
  - GSC demand checks
  - cluster assembly
  - semantic deduplication
  - publishability gates
  - conversion-priority scoring

### Sidecar-first Control Plane

1. Cluster assembler
2. Governed mixed scorer
3. Admin steering policy layer
4. Action selector
5. Executor dispatch layer
6. Decision trace and feedback layer

The sidecar first runs read-only. It becomes authoritative only after shadow success gates pass.

## Cluster Contract

### Identity
- `cluster_id`: deterministic hash of `site + canonical_topic + primary_target_page + intent_band + cluster_version`
- `cluster_version`: semantic algorithm version such as `v1`, `v1.1`

### Membership Rules
- include query-page pairs with normalized semantic similarity `>= 0.72` to the cluster topic
- require the same primary intent band:
  - `commercial`
  - `mixed-commercial-support`
  - `support-only`
- limit to max `25` query-page members per cluster in V1
- exclude members that fail publishability or dedup guardrails

### Cadence
- full recompute every `24h`
- incremental recompute after major GSC sync completion
- authoritative decisions require cluster snapshot age `< 36h`

### Versioning Behavior
- keep prior cluster snapshot for one full recompute cycle
- when cluster algorithm version changes, shadow both versions for `7 days` before cutover

## Scoring Governance

### Factor Set
Each factor is normalized to `[0.0, 1.0]`:
- demand
- commercial intent
- conversion proximity
- CTR gap
- content gap
- internal-link gap
- cannibalization penalty
- backlink need
- admin steering modifier

### Steering Cap
- total steering effect absolute value is capped at `0.12` of final score

### Tie-break Order
1. higher conversion proximity
2. higher net demand quality
3. lower cannibalization risk
4. lower operational risk action

### Monotonic Constraints
- increasing demand cannot lower score when other factors are unchanged
- increasing conversion proximity cannot lower score when other factors are unchanged
- increasing negative-keyword conflict cannot raise score

## Admin Steering Policy Layer

### Influence Rules
- reference match: bounded positive modifier
- negative match: bounded suppression; hard-negative exact match blocks primary targeting
- commercial terms: boost intent factor only
- priority target pages: boost only when demand and publishability gates already pass

### Conflict Resolution
- `NEGATIVE_KEYWORDS` overrides `REFERENCE_KEYWORDS` for primary targeting
- `PRIORITY_TARGET_PAGES` cannot override failed publishability or dedup gates

### No-bypass Enforcement
- steering is evaluated after mandatory gates, never before them

## Selector Safety Contract

### Confidence Thresholds
- `>= 0.75`: eligible for authoritative execution
- `0.60 - 0.74`: recommendation-only
- `< 0.60`: fallback to current query-centric path

### Idempotency
- decision key: `cluster_id + action_family + decision_window_24h`
- the same key must not enqueue duplicate execution within the decision window

### Action-specific Fallback Triggers
- `ctr_optimize`: missing valid title/meta candidate or stale page snapshot
- `page_refresh`: missing retrievable source content or patch generation failure
- `internal_link_push`: insufficient eligible target pages
- `supporting_content_create`: fails publishability gate or near-duplicate detected
- `backlink_support`: no valid opportunities or outreach preconditions unmet

## Shadow Success Gates

- minimum shadow duration: `14 days`
- promotion criteria:
  - top-20 recommendation business-value precision improvement `>= +20%` vs baseline
  - no increase in execution failure rate beyond `+2%` absolute
  - no increase in duplicate/cannibalization incidents beyond `+5%`
  - decision trace completeness `>= 99%`
  - steering cap violations `= 0`
- any failed gate extends shadow by `7 days` with remediation

## Observability Spec

### Required Decision Trace Payload
- `cluster_id`
- `cluster_version`
- cluster member summary
- factor values
- capped steering modifiers
- selected action
- confidence
- fallback reason, if any

### Required Metrics
- action-family selection distribution
- confidence distribution
- fallback rate
- execution success/failure by action family
- shadow-vs-baseline ranking deltas

### Required Alarms
- fallback rate spike `> 15%` day-over-day
- confidence collapse with median `< 0.60` for 24h
- steering cap breach count `> 0`
- decision trace missing rate `> 1%`

## Rollout Control Matrix

Feature flags:
- `cluster_engine_shadow_enabled`
- `cluster_engine_authoritative_enabled`
- `action_ctr_authoritative_enabled`
- `action_refresh_authoritative_enabled`
- `action_internal_link_authoritative_enabled`
- `action_new_content_authoritative_enabled`
- `action_backlink_authoritative_enabled`

Kill switch:
- one global switch disables authoritative cluster selection and reverts to the baseline selector

Rollback playbook:
1. disable authoritative flags
2. flush queued non-idempotent cluster jobs not yet started
3. re-enable baseline selector
4. export last 24h decision traces for incident review
5. re-enter shadow mode after the fix

### Core Pipeline

1. `Cluster Assembler`
   - Read GSC query/page performance
   - Group related queries/pages into demand clusters
   - Attach current site assets and topology

2. `Mixed Scorer`
   - Score each cluster using:
     - GSC demand
     - keyword commercial intent
     - page type / conversion proximity
     - page performance gap
     - support-asset potential
     - cluster health / cannibalization / link coverage
     - admin steering boost / suppression

3. `Action Selector`
   - Choose one best next action for the cluster:
     - `ctr_optimize`
     - `page_refresh`
     - `internal_link_push`
     - `supporting_content_create`
     - `backlink_support`

4. `Executor Adapter Layer`
   - Map selected action into existing jobs/agents
   - Reuse current implementations where possible

5. `Feedback Loop`
   - Record before/after metrics and decision rationale
   - Re-score clusters as fresh data arrives

## Viable Options

### Option A - Extend current query/page opportunity rows only
- Pros: smallest schema churn
- Cons: still query-centric; weak fit for cluster-level action choice; likely to produce fragmented actions

### Option B - Add a cluster-priority engine above existing GSC/opportunity/actions layers (Chosen)
- Pros: matches user intent, reuses existing modules, enables dynamic action selection, fits current `TopicCluster` direction
- Cons: requires orchestration refactor and score-breakdown visibility

### Option C - Keep current logic and just improve GSC keyword weighting
- Pros: smallest implementation effort
- Cons: does not solve action selection or conversion-priority orchestration

## Chosen Direction

Choose Option B. Introduce a dedicated cluster-priority service and action selector while reusing current jobs as executors.

## Brownfield Reuse Strategy

- Reuse existing GSC ingest and helper methods in [src/integrations/gsc_client.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/integrations/gsc_client.py):160, 239, 287.
- Reuse `TopicCluster` and topic-map logic as the starting point for cluster modeling in [src/models/gsc_data.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/gsc_data.py):215 and [src/services/topic_map.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/services/topic_map.py):176, 347.
- Reuse `Opportunity` as the outward-facing admin/API unit, but evolve it to represent cluster decisions in [src/models/gsc_data.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/gsc_data.py):144.
- Reuse action executors:
  - refresh in [src/agents/content_refresh.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/agents/content_refresh.py):69
  - internal links in [src/agents/internal_link.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/agents/internal_link.py):71
  - backlinks in [src/backlink/copilot.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/backlink/copilot.py):85
- Reuse existing `SEOContext` lane metadata instead of inventing another content-role DTO in [src/models/seo_context.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/seo_context.py):105 and [src/models/seo_context.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/seo_context.py):352.

## Data Model Direction

### V1 principle

Prefer extending existing models over introducing a brand-new parallel subsystem.

### Recommended changes

1. Extend `Opportunity` with cluster-aware metadata in [src/models/gsc_data.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/gsc_data.py):144
   - `cluster_id`
   - `cluster_name`
   - `decision_unit_type`
   - `recommended_action_family`
   - `score_breakdown_json`
   - `support_role`
   - `target_asset_type`

2. Reuse or extend `TopicCluster` in [src/models/gsc_data.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/gsc_data.py):215
   - add GSC-demand aggregation freshness
   - add business-intent summary
   - add conversion proximity summary
   - add support-asset coverage / orphan counts

3. Canonicalize action logging on one model
   - There are two `ContentAction` definitions for `content_actions` in [src/models/job_runs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/job_runs.py):121 and [src/models/content_action.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/content_action.py):10.
   - V1 should choose one canonical model before adding more action-feedback fields.
   - Migration phases:
     - Phase A: dual-write for `14 days`
     - Phase B: read cutover after parity mismatch rate `< 1%` for `7` consecutive days
     - Phase C: backfill historical legacy records into canonical schema
     - Phase D: decommission legacy writes and add regression guards

4. Add system-config-backed admin steering keys
   - persist via `SystemConfig` in [src/models/config.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/config.py):5
   - expose via admin API in [src/api/admin.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/api/admin.py):105 and [src/api/admin.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/api/admin.py):171
   - edit in admin UI in [static/admin/index.html](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/static/admin/index.html) and [static/admin/script.js](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/static/admin/script.js)

### Suggested config keys

- `REFERENCE_KEYWORDS`
- `NEGATIVE_KEYWORDS`
- `COMMERCIAL_PRIORITY_TERMS`
- `PRIORITY_TARGET_PAGES`
- `GSC_ENABLED`
- `GSC_AUTH_METHOD`
- `GSC_CREDENTIALS_JSON`
- `GSC_CREDENTIALS_PATH`
- `GSC_OPPORTUNITY_SYNC_ENABLED`

V1 minimum required:

- `REFERENCE_KEYWORDS`

Recommended semantics:

- `REFERENCE_KEYWORDS`: soft positive boost
- `NEGATIVE_KEYWORDS`: soft suppression or explicit exclude list
- `COMMERCIAL_PRIORITY_TERMS`: raises commercial-intent weighting
- `PRIORITY_TARGET_PAGES`: boosts clusters attached to strategically important landing pages
- `GSC_ENABLED`: single gate for all GSC read paths (API + scheduler + sync jobs)
- `GSC_AUTH_METHOD`: canonical credential mode selector for all GSC clients
- `GSC_OPPORTUNITY_SYNC_ENABLED`: controls DB persistence bridge from GSC demand into `Opportunity`

## Operational Remediation: GSC Connection And Opportunity Persistence

Before deeper selector promotion, close the production gaps that can keep the opportunity pool empty even when GSC has data.

### Gap A - Gate mismatch
- Symptom: `/api/v1/gsc/*` requires `gsc_enabled`, but admin currently cannot manage `GSC_ENABLED`.
- Correction:
  - expose `GSC_ENABLED` in admin API and `/admin` UI
  - include `GSC_ENABLED` in allowed keys and bool coercion list
  - show effective runtime value in admin config response

### Gap B - Credential resolution mismatch
- Symptom: scheduler uses `gsc_site_url + gsc_credentials_json` and ignores `gsc_auth_method` and `gsc_credentials_path`.
- Correction:
  - introduce one shared GSC client factory used by API and scheduler
  - enforce consistent credential precedence by auth method
  - fail with explicit diagnostics when required credential source is missing

### Gap C - Live GSC opportunities not persisted to opportunity pool
- Symptom: `/api/v1/gsc/opportunities` can return rows while `/api/v1/opportunities` remains empty.
- Correction:
  - add a dedicated persistence bridge that materializes selected GSC opportunities into `Opportunity`
  - make persistence idempotent on `site + query + page + decision_window`
  - keep clear source metadata (`engine_mode`, `decision_window_key`, `opportunity_type`)

### Gap D - Shadow persistence tied only to `content_generation_job`
- Symptom: if content generation does not run, cluster-priority opportunities are never materialized.
- Correction:
  - add a dedicated periodic/manual shadow-sync job not coupled to content generation
  - allow admin-triggered sync endpoint for immediate recovery
  - keep fallback behavior when shadow engine returns no confident decisions

### Gap E - Migration and runtime readiness drift
- Symptom: production DB can miss required columns/migrations, causing silent empty pool or runtime failures.
- Correction:
  - add startup/readiness checks for required tables and columns (`opportunities`, `topic_clusters`, migration version)
  - expose readiness status in admin health view
  - block authoritative mode when schema readiness fails

## Functional Requirements

### R1. Cluster assembly
- Build clusters from GSC query/page pairs, current page inventory, and topic-map signals.
- Similar queries that map to the same commercial intent or landing destination should join the same cluster.

### R2. Mixed scoring
- Score must combine at least:
  - GSC demand
  - business intent
  - page conversion proximity
  - page opportunity gap
  - support-content need
  - internal-link gap
  - cannibalization or duplication risk
- Admin steering inputs may adjust score, but only as bounded weighting factors.
- No single hard gate decides eligibility.

### R3. Dynamic action selection
- Each cluster receives exactly one primary next action and optional secondary actions.
- Existing-page optimization should outrank new content when the current page already has strong demand and weak CTR/content fit.

### R4. Informational support rule
- Informational/tutorial-looking content may only be prioritized when attached to a conversion-driving cluster as support.

### R5. Admin guidance rule
- `/admin` must allow operators to paste reference keywords.
- Admin-provided reference keywords must improve directionality without directly forcing content generation.
- If a pasted keyword conflicts with negative filters, deduplication, or publishability rules, the system must not auto-promote it.

### R6. Shadow mode
- The new engine must support shadow scoring without changing live production behavior initially.
- Shadow outputs should be reviewable alongside old selections.

### R7. Measurement
- Record decision rationale and before/after metrics for executed actions.

### R8. GSC readiness contract
- The system must expose one authoritative GSC readiness status that covers:
  - `GSC_ENABLED`
  - site URL presence
  - credential-source validity based on `GSC_AUTH_METHOD`
  - API connectivity health

### R9. Opportunity materialization contract
- If GSC live opportunities exist and persistence bridge is enabled, `/api/v1/opportunities` must receive materialized records within one sync window.
- Materialization must be idempotent across repeated sync runs in the same decision window.

### R10. Scheduler/API parity contract
- API and scheduler must use the same GSC client construction path and credential resolution.
- `GSC_CREDENTIALS_PATH` and `GSC_CREDENTIALS_JSON` must both be supported according to auth-mode policy.

### R11. Decoupled shadow persistence contract
- Cluster-priority persistence must not depend solely on `content_generation_job`.
- A dedicated sync lane must keep opportunity pool freshness under autopilot-off or low-content-frequency periods.

### R12. Migration safety contract
- Authoritative cluster mode must not activate unless required schema columns and indexes are present.
- Missing migration state must produce actionable alerts, not silent degradation.

## Implementation Steps

### 0. Close GSC operational gaps before selector rollout
Implement these items before further promotion of cluster-authoritative control:
- Add `GSC_ENABLED` to admin API + UI config flows.
- Add shared GSC client factory for API and scheduler parity.
- Add dedicated GSC opportunity persistence bridge and idempotency rules.
- Add dedicated shadow-sync trigger lane (scheduled + admin manual trigger).
- Add migration/readiness checks and authoritative-mode guard.

### 1. Introduce a cluster-priority domain service
Create a new service layer, for example:
- `src/services/gsc_priority_engine.py`
- `src/services/demand_cluster_service.py`

Responsibilities:
- cluster assembly
- mixed scoring
- action selection
- score breakdown generation

Inputs:
- GSC query/page data from [src/integrations/gsc_client.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/integrations/gsc_client.py):160
- page summaries/opportunities/clusters from [src/models/gsc_data.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/gsc_data.py):89, 144, 215
- topic-map intelligence from [src/services/topic_map.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/services/topic_map.py):140
- admin steering config from [src/models/config.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/config.py):5 and [src/config/utils.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/config/utils.py):59

The scorer should treat admin input as:

- boost for related commercial clusters
- suppression for unwanted directions
- tie-break help when multiple clusters have similar demand

It should not treat admin input as:

- a guaranteed generation queue
- a replacement for GSC demand
- a bypass around cluster/action selection

### 2. Refactor scheduler entrypoints around action selection
Refactor [src/scheduler/jobs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/scheduler/jobs.py):1157 so the autopilot flow becomes:
- collect candidate demand clusters
- score clusters
- choose winning cluster
- choose winning action
- dispatch to executor

Do not immediately delete the existing keyword-source fallback chain. Wrap it behind:
- shadow mode
- fallback if cluster engine yields no confident decisions
- unified GSC client-factory behavior and readiness diagnostics
- persisted-pool freshness checks before expensive live fetch fallback

### 3. Add admin configuration and readiness surface
Extend the admin stack so operators can manage guidance inputs and GSC operational controls from `/admin`:

- add UI fields in [static/admin/index.html](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/static/admin/index.html)
- add field mapping/save behavior in [static/admin/script.js](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/static/admin/script.js)
- allow keys in [src/api/admin.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/api/admin.py):171
- include values in [src/api/admin.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/api/admin.py):105
- expose effective GSC readiness, credential source mode, last raw sync, last materialization, and schema readiness state

V1 UI shape:

- one textarea for `REFERENCE_KEYWORDS`

Preferred V1.1 UI shape:

- one textarea each for:
  - `REFERENCE_KEYWORDS`
  - `NEGATIVE_KEYWORDS`
  - `COMMERCIAL_PRIORITY_TERMS`
  - `PRIORITY_TARGET_PAGES`

Suggested UX rules:

- one line per entry
- ignore blank lines
- trim and normalize duplicates
- keep field descriptions explicit that these inputs guide ranking but do not force publishing

### 4. Refit opportunity scoring from query-centric to cluster-centric
Evolve [src/agents/opportunity_scoring.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/agents/opportunity_scoring.py):53 into reusable scoring helpers or fold its logic into the new priority engine.

Target behavior:
- low-hanging fruit becomes one factor, not the whole system
- CTR gap becomes one factor, not a separate world
- cannibalization becomes a negative factor or a consolidation action trigger
- admin steering boosts become bounded modifiers, not top-level overrides

### 5. Unify action dispatch to existing executors
Add a dispatch layer that maps action families to current jobs:
- `page_refresh` -> [src/scheduler/jobs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/scheduler/jobs.py):2354
- `internal_link_push` -> [src/scheduler/jobs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/scheduler/jobs.py):2534
- `backlink_support` -> [src/scheduler/jobs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/scheduler/jobs.py):2914
- `supporting_content_create` -> existing content generation branch in [src/scheduler/jobs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/scheduler/jobs.py):1157

### 6. Extend admin/API visibility
Update [src/api/opportunities.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/api/opportunities.py):115 so admins can inspect:
- cluster-level opportunities
- selected action family
- score breakdown
- support-vs-primary role
- whether admin steering inputs influenced the score
- which steering inputs matched
- data freshness and whether records are materialized or preview-only

### 7. Canonicalize action feedback logging
Before deepening measurement, reconcile the duplicate `ContentAction` model definitions in:
- [src/models/job_runs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/job_runs.py):121
- [src/models/content_action.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/content_action.py):10

Then log:
- decision snapshot
- metrics before
- metrics after
- cluster/action linkage

### 8. Roll out in three phases

#### Phase 1 - Shadow scoring only
- compute clusters and mixed scores
- do not alter live action choice
- expose comparison logs/admin output
- validate that admin steering inputs only produce bounded boost/suppression effects

#### Phase 2 - Assisted action recommendation
- new engine chooses recommended action
- human/admin confirms execution or review

#### Phase 3 - Controlled autopilot takeover
- autopilot uses new selector for a bounded subset of clusters
- retain fallback to old logic on engine failure or low confidence

## Consensus Hardening Additions

Implementation order after Architect/Critic review:

1. define cluster contract and versioned identity
2. implement assembler with conservative membership rules
3. implement governed scorer with bounded steering and monotonic tests
4. implement admin steering conflict and no-bypass policy
5. implement selector safety contract: confidence thresholds, idempotency, fallback rules
6. integrate sidecar shadow path into scheduler orchestration
7. add observability traces, metrics, and alarms
8. add rollout control flags, kill switch, and rollback playbook
9. canonicalize `ContentAction` through dual-write, read cutover, backfill, and decommission
10. progressively promote the selector by action family

## Acceptance Criteria

1. The system can produce cluster-level candidates instead of only single-keyword candidates.
2. Each selected cluster includes a transparent mixed-score breakdown.
3. Each selected cluster produces one primary next action.
4. High-impression but low-value informational demand does not dominate top recommendations.
5. Informational/tutorial assets can appear only as support roles for conversion-driving clusters.
6. Existing page optimization can outrank net-new content when current demand already exists.
7. Shadow mode can compare old-vs-new selections before live takeover.
8. Admin/API surfaces can show cluster, action family, and score breakdown.
9. `/admin` supports at least one pasted reference-keywords field backed by `SystemConfig`.
10. Admin reference keywords influence ranking only as bounded guidance and never bypass publishability, deduplication, or cluster scoring.
11. Before/after action logging supports measurement of decision quality.
12. Cluster identity and versioning are deterministic and test-covered.
13. Steering cap, tie-break order, and monotonic scoring constraints are enforced by tests.
14. Selector idempotency prevents duplicate action enqueue inside a 24h window.
15. Shadow success gates are numeric and automatically evaluable.
16. Feature flags support per-action-family promotion and instant rollback.
17. Observability emits complete per-cluster traces with factor contributions.
18. Admin can read/write `GSC_ENABLED` from `/admin`, and runtime value is visible.
19. API and scheduler both support `GSC_CREDENTIALS_JSON` and `GSC_CREDENTIALS_PATH` via the same client-factory logic.
20. When GSC live opportunities exist, persistence bridge can materialize them into `Opportunity` without requiring `content_generation_job`.
21. Opportunity materialization is idempotent across repeated sync runs in the same window.
22. Dedicated shadow-sync lane can populate/refresh cluster opportunities while autopilot content generation is idle.
23. Schema readiness check blocks authoritative mode when required migration columns are missing.
24. Rollback can disable bridge/sync/authoritative flags without breaking baseline GSC status and baseline selector.

## Risks And Mitigations

### Risk 1 - Bad clustering merges unrelated demand
- Mitigation: start with conservative clustering rules and expose score breakdown + cluster members for review.

### Risk 2 - Overweighting impressions revives vanity traffic
- Mitigation: explicit business-intent and conversion-proximity factors; reject pure-impression ranking.

### Risk 3 - Old and new engines diverge unpredictably in production
- Mitigation: mandatory shadow mode and bounded rollout.

### Risk 4 - Duplicate `ContentAction` models cause incorrect writes
- Mitigation: canonicalize action log model before extending measurement.

### Risk 5 - Existing action executors are too generic
- Mitigation: keep executor reuse for V1, but pass richer cluster context into refresh/link/content jobs.

### Risk 6 - Admin-pasted keywords overpower real demand
- Mitigation: cap steering weights, expose score breakdown, and validate behavior in shadow mode before live rollout.

### Risk 7 - Free-text admin inputs become noisy or duplicated
- Mitigation: normalize, deduplicate, trim, and optionally cap entry counts per field.

### Risk 8 - API and scheduler disagree on GSC enablement/credentials
- Mitigation: shared client factory + single readiness contract + parity tests across entrypoints.

### Risk 9 - Opportunity pool remains empty due to persistence coupling
- Mitigation: dedicated sync lane + idempotent persistence bridge + manual trigger endpoint for recovery.

### Risk 10 - Production schema drift causes partial feature activation
- Mitigation: startup/readiness checks, authoritative guardrails, and explicit operator-visible health state.

### Risk 11 - Cross-database misconfiguration hides true production state
- Mitigation: expose effective database target and readiness diagnostics in admin health payload.

## Verification Steps

1. Unit-test cluster assembly on representative GSC query/page fixtures.
2. Unit-test mixed scoring to ensure conversion-value clusters outrank generic high-impression clusters.
3. Unit-test action selection for refresh vs internal links vs new content vs backlinks.
4. Integration-test scheduler dispatch from cluster decision to executor.
5. Integration-test opportunity API rendering of cluster-aware fields.
6. Integration-test admin config save/load for steering inputs.
7. Property-test monotonic scoring constraints and steering-cap enforcement.
8. Contract-test cluster identity and version stability.
9. Integration-test selector idempotency and fallback behavior per action family.
10. Run shadow mode and compare top-N recommendations with current production logic.
11. Verify action logging writes consistent before/after metrics on the canonical `ContentAction` model.
12. Run a staging rollback drill that validates kill switch behavior and baseline restoration.
13. Validate decision trace completeness stays at or above `99%`.
14. Verify `/api/v1/gsc/status` and scheduler GSC path both reflect `GSC_ENABLED` consistently.
15. Verify scheduler/API both succeed under `GSC_CREDENTIALS_PATH` and under `GSC_CREDENTIALS_JSON`.
16. Verify live GSC opportunities can be persisted into `Opportunity` through dedicated bridge when content generation is not running.
17. Verify repeated sync runs do not duplicate opportunity rows inside the same decision window.
18. Verify schema-readiness guard prevents authoritative execution when required columns are missing.
19. Verify rollback by disabling bridge/sync/authoritative flags restores baseline behavior without data corruption.

## Recommended Files To Change

- [src/api/gsc.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/api/gsc.py)
- [src/scheduler/jobs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/scheduler/jobs.py)
- [src/integrations/gsc_client.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/integrations/gsc_client.py)
- [src/services/gsc_priority_engine.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/services/gsc_priority_engine.py)
- [src/config/settings.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/config/settings.py)
- [src/config/utils.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/config/utils.py)
- [src/models/gsc_data.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/gsc_data.py)
- [src/services/topic_map.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/services/topic_map.py)
- [src/agents/opportunity_scoring.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/agents/opportunity_scoring.py)
- [src/api/opportunities.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/api/opportunities.py)
- [src/api/admin.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/api/admin.py)
- [static/admin/index.html](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/static/admin/index.html)
- [static/admin/script.js](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/static/admin/script.js)
- [src/models/job_runs.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/job_runs.py)
- [src/models/content_action.py](C:/Users/DJS%20Tech/ZenflowProjects/bobopkgproject/src/models/content_action.py)

## Remaining Open Decisions

- Whether cluster persistence should be materialized in DB immediately or derived in V1 shadow mode first
- Whether `TopicCluster` is sufficient as the persistence model or needs a dedicated demand-cluster supplement
- Whether backlinks should remain weekly-batch in V1 or become on-demand cluster actions later
- Whether `/api/v1/opportunities` should expose a guarded read-through fallback from live GSC when persisted pool is empty
- Whether dedicated sync lane should run under autopilot scheduler only or also under an independent periodic runner

## ADR

### Decision
Adopt a cluster-priority orchestration layer with governed mixed scoring and dynamic action selection, integrating admin steering as bounded ranking guidance.

### Drivers
- maximize inquiry/conversion-value traffic
- reuse existing brownfield modules instead of replacing them
- preserve production safety through measurable rollout controls

### Alternatives considered
- query-centric enhancement only
- new-content-first with better filters
- full greenfield rewrite

### Why chosen
This option best balances business alignment, brownfield reuse, explainability, and rollout safety.

### Consequences
- moderate refactor scope across scheduler, model, API, admin, and logging layers
- higher implementation governance requirements
- better action prioritization and decision traceability if shadow gates pass

### Follow-ups
1. finalize steering weight constants and negative-keyword policy details
2. choose the canonical `ContentAction` model and migration owner
3. define go-live thresholds from shadow performance dashboards

## Available-Agent-Types Roster

- `explore`
- `planner`
- `architect`
- `debugger`
- `executor`
- `verifier`
- `test-engineer`
- `quality-reviewer`
- `api-reviewer`
- `performance-reviewer`
- `security-reviewer`
- `build-fixer`
- `writer`

## Follow-up Staffing Guidance

### `$ralph`
- Lane 1: core implementation and orchestrator build using `executor` with `high` reasoning
- Lane 2: tests and verification using `test-engineer` and `verifier` with `medium/high` reasoning
- Lane 3: architecture checkpoint reviews using `architect` with `medium/high` reasoning
- Lane 4: API/admin compatibility review using `api-reviewer` with `medium` reasoning
- Best for: milestone-based sequential rollout where every stage must clear evidence gates before the next

### `$team`
- Worker 1: core scoring/orchestration using `executor` with `high` reasoning
- Worker 2: scheduler integration and fallback path using `executor` or `debugger` with `high` reasoning
- Worker 3: admin config and UI/API integration using `executor` with `medium` reasoning
- Worker 4: API/model evolution using `executor` plus `api-reviewer` with `medium/high` reasoning
- Worker 5: regression suite and rollout tests using `test-engineer` with `high` reasoning
- Worker 6: final validation and audit lane using `verifier` with `high` reasoning
- Best for: parallel lane execution once the migration contract is accepted

## Launch Hints

### Ralph
- `$ralph .omx/plans/prd-gsc-priority-upgrade.md`

### Team
- `omx team 5:executor "Implement GSC cluster-priority engine with bounded admin steering, shadow-first rollout, and regression evidence"`
- `omx team 6:executor "Parallel lanes: scorer+selector, scheduler integration, admin config UI/API, model canonicalization, tests, verification"`

Suggested staged team launches:
1. `omx team 3:executor "Domain contracts + cluster assembler + governed scorer"`
2. `omx team 3:executor "Scheduler dispatch + admin steering config + API exposure"`
3. `omx team 2:executor "Migration parity + regression suite + rollout safety verification"`

## Team Verification Path

1. All worker tasks reach terminal state with no unacknowledged failures.
2. Required evidence bundle includes:
   - unit tests for scorer, selector, and cluster assembler
   - integration tests for scheduler, admin, API, and migration parity
   - fallback-path validation
   - shadow comparison report
3. Cross-lane consistency checks confirm:
   - steering inputs are bounded in scoring
   - no bypass of deduplication or publishability gates
   - action logs are written through the canonical `ContentAction` model
4. Final verifier issues explicit pass/fail evidence.
5. Only then perform team shutdown.

## Applied Improvements

- Added deterministic cluster contract with versioning, cadence, and staleness rules.
- Added scoring governance: factor bounds, steering cap, tie-break order, and monotonic constraints.
- Added admin steering conflict and no-bypass policy.
- Added selector safety contract with thresholds, idempotency, and action-specific fallback rules.
- Added explicit `ContentAction` dual-write, read-cutover, and backfill migration path.
- Added numeric shadow success gates.
- Added observability requirements, alarms, feature flags, kill switch, and rollback playbook.
- Switched rollout from generic shadow/live to sidecar-first plus progressive action-family promotion.
