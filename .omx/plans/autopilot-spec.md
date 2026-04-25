# Autopilot Spec

Task: Close the GSC connectivity and opportunity-persistence gaps that can leave the production opportunity pool empty even when Google Search Console has valid data.

Requirements:
- Unify `GSC_ENABLED` behavior across admin, API, scheduler, and sync jobs.
- Use one shared GSC client construction path for `GSC_AUTH_METHOD`, `GSC_CREDENTIALS_JSON`, and `GSC_CREDENTIALS_PATH`.
- Separate live GSC preview from the persisted opportunity pool.
- Add an independent sync/materialization path so `Opportunity` rows can be populated without `content_generation_job`.
- Add readiness/migration diagnostics so missing schema cannot masquerade as an empty pool.
- Preserve the demand-first, conversion-oriented cluster-priority plan already captured in the task PRD.

Constraints:
- No new dependencies.
- Brownfield-safe rollout with explicit rollback controls.
- Keep baseline selector behavior available while the new bridge and sync lane are validated.
- Verification must cover config parity, credential parity, idempotent persistence, and migration-readiness behavior.
