# Autopilot Implementation Plan

1. Clean upstream keyword generation templates and entity extraction.
2. Add keyword publishability/quality scoring and selection gating.
3. Add SERP role to routing and SEO context.
4. Make title generation role-aware and add strict fallback when title-query match fails.
5. Pass SERP role into planner/writer prompts.
6. Add publish-time synchronization blocking for non-publishable keywords / title mismatch.
7. Run targeted regression suite and reviewer validation.
