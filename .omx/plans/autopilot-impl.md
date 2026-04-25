# Autopilot Implementation Plan

1. Add a unified GSC runtime resolver and client factory shared by API and scheduler.
2. Expose `GSC_ENABLED` and readiness diagnostics in the admin config surface.
3. Add an independent raw GSC sync + opportunity materialization lane with idempotent upsert behavior.
4. Decouple shadow persistence from `content_generation_job` while keeping baseline fallback.
5. Add schema-readiness guards before authoritative mode can run.
6. Extend API/admin visibility for persisted-pool freshness and degraded states.
7. Verify config parity, credential parity, materialization, rollback, and migration-readiness behavior with targeted tests.
