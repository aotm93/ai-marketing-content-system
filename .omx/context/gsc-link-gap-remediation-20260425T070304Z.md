# Context Snapshot: gsc-link-gap-remediation

- Timestamp: 2026-04-25T07:03:04Z
- Task statement: Plan the missing remediation work for Google Search Console connectivity, data ingestion, and opportunity-pool population so production can reliably surface GSC-backed opportunities.
- Desired outcome: An execution-ready plan that closes the observed operational gaps between valid GSC credentials, live GSC reads, scheduler-side usage, and the database-backed opportunity pool.
- Scope boundary: Focus on planning and hardening the brownfield implementation path before rollout; do not assume the current refactor is operationally complete.

## Known Facts / Evidence

- `src/api/gsc.py` gates all GSC API endpoints behind `settings.gsc_enabled`, but admin config does not expose `GSC_ENABLED`.
- `src/api/gsc.py` builds a `GSCClient` using `gsc_credentials_json` or `gsc_credentials_path`.
- `src/scheduler/jobs.py` uses GSC for shadow priority and keyword selection when `gsc_site_url` and `gsc_credentials_json` exist, but it ignores `gsc_enabled`, `gsc_auth_method`, and `gsc_credentials_path`.
- `src/api/gsc.py:/opportunities` returns live GSC low-hanging-fruit results without persisting them to `Opportunity`.
- `src/api/opportunities.py` and `static/admin/opportunities.html` read only from the `Opportunity` table.
- `src/services/gsc_priority_engine.py` can persist cluster-priority decisions into `Opportunity`, but current persistence is triggered from `content_generation_job`.
- The workspace database `sql_app.db` has `gsc_queries=0`, `opportunities=0`, `topic_clusters=0`, lacks new cluster-priority columns such as `engine_mode`, and has no `alembic_version` table.
- Local full-app startup currently hits a DB compatibility issue in `src/core/database.py` because SQLite does not accept the configured `connect_timeout` arg.

## Constraints

- Production safety matters more than feature breadth.
- No new dependencies.
- The fix should preserve the brownfield GSC priority refactor rather than replace it.
- The opportunity pool must optimize for customer-value and conversion-adjacent demand, not generic informational traffic.

## Unknowns / Open Questions

- Whether production currently authenticates GSC via JSON blob, credentials path, or both.
- Whether production opportunity visibility should support a temporary live-GSC fallback when persisted rows are empty.
- Whether the first rollout should materialize only cluster-priority opportunities or also baseline GSC low-hanging-fruit rows.
- Whether production currently runs autopilot/content-generation frequently enough for shadow persistence to populate the pool.

## Likely Touchpoints

- `src/api/gsc.py`
- `src/api/admin.py`
- `src/config/settings.py`
- `src/config/utils.py`
- `src/integrations/gsc_client.py`
- `src/scheduler/jobs.py`
- `src/services/gsc_priority_engine.py`
- `src/models/gsc_data.py`
- `src/core/database.py`
- `static/admin/index.html`
- `static/admin/script.js`
- `static/admin/opportunities.html`
