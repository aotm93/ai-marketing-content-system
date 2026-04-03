# BoboPkg SEO Automation Platform

## What This Is

An AI-powered SEO content automation platform that autonomously generates, optimizes, and publishes articles to WordPress. It uses a multi-agent pipeline (keyword discovery → content planning → AI writing → quality gate → publishing) driven by an APScheduler autopilot, integrating with Google Search Console, DataForSEO, Rank Math SEO, and OpenAI-compatible LLMs.

## Core Value

The autopilot reliably publishes SEO-optimized articles that are structurally matched to their keyword intent — so every article earns its ranking by actually serving what the searcher needs.

## Requirements

### Validated

- ✓ FastAPI backend with JWT admin auth and REST API — existing
- ✓ Multi-agent AI pipeline (orchestrator + specialist agents) — existing
- ✓ APScheduler autopilot for autonomous content generation cycles — existing
- ✓ WordPress REST API publishing with Rank Math SEO meta — existing
- ✓ Google Search Console data sync and keyword opportunity scoring — existing
- ✓ Multi-source keyword fallback (GSC → KeywordAPI → ContentIntelligence → Emergency) — existing
- ✓ Quality gate service with duplicate detection and SEO validation — existing
- ✓ Admin dashboard (Next.js static export) for config and monitoring — existing
- ✓ DataForSEO integration for keyword and backlink data — existing
- ✓ Dual configuration (env + DB-backed runtime overrides) — existing
- ✓ Alembic migrations, PostgreSQL + Redis infrastructure — existing
- ✓ Email marketing module (Resend client, sequence engine) — existing
- ✓ Programmatic SEO page factory — existing
- ✓ Backlink outreach module — existing

### Active

- [ ] AI-driven content type classification: analyze title intent (how-to, listicle, comparison, review, pricing) via LLM before outline generation
- [ ] Content type-specific section structures: each content type gets its own tailored H2/H3 outline instead of a generic skeleton
- [ ] Intent-aware prose quality: writing instructions per section vary by content type (e.g. numbered steps for how-to, side-by-side tables for comparison, verdict sections for reviews)
- [ ] New ContentPlannerAgent (or planning step in ContentCreatorAgent): classifies intent → selects structure → generates tailored outline → passes enriched SEOContext to writer

### Out of Scope

- Full research enrichment before writing — deferred; Phase 1 focuses on structure and prose quality, not adding web research
- Replacing LangChain/LangGraph with a different orchestration framework — too disruptive; dependencies will be updated in a separate tech-debt phase
- Multi-platform publishing (beyond WordPress) — WebhookAdapter already stubbed; not the current focus
- Fixing the 3 critical security issues (hardcoded password, plain-text auth, wildcard CORS) — important but separate from content generation; tracked in CONCERNS.md for a dedicated security phase

## Context

**Existing pipeline to modify:**
`AutopilotScheduler` → `content_generation_job()` in `src/scheduler/jobs.py` (2,646 lines) → `SEOContext` DTO → `ContentCreatorAgent.execute()` → `ProfessionalContentWriter` → `QualityGateService` → `WordPressAdapter.publish()`

**The problem:**
`ProfessionalContentWriter` (in `src/services/content/`) uses the same section template for every article regardless of what the title signals. A "Best 10 X" article and a "How to do Y" article get the same generic H2 skeleton with no structural differentiation. This produces articles that don't match user intent and are less likely to rank.

**Target content types:**
How-to/Tutorial, Listicle/Best-of, Comparison/Versus, Review, Pricing/Cost guide.

**Classification approach:**
LLM-based intent classification (not rule-based) — the title is sent to the LLM for classification before outline generation. This handles ambiguous titles where keyword matching would fail.

**Integration pattern:**
New planning step inserted between SEOContext creation and ContentCreatorAgent execution. The SEOContext should be enriched with `content_type` and `section_outline` fields before the writer receives it.

**Key files likely involved:**
- `src/agents/content_creator.py` — ContentCreatorAgent
- `src/services/content/` — ProfessionalContentWriter and writing pipeline
- `src/models/seo_context.py` — SEOContext DTO (needs new fields)
- `src/scheduler/jobs.py` — content_generation_job() orchestration

## Constraints

- **Tech Stack**: Python 3.11, FastAPI, LangChain 0.1.x, OpenAI SDK 1.10.0 — must work within current dependency versions; no major upgrades in scope
- **Integration**: Must plug into existing `SEOContext` DTO and `ContentCreatorAgent` without breaking the current autopilot pipeline
- **Architecture**: Single-container deployment; no new background workers or services; changes stay within the existing modular monolith
- **Backward Compatibility**: Existing WordPress publishing, quality gate, and scheduler flows must continue to work after changes

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LLM classification (not keyword rules) for content type | Handles ambiguous titles, uses existing AI provider abstraction, consistent with multi-agent design | — Pending |
| New planning step (not a new agent class) | Inserting into the existing pipeline is lower risk than adding a new agent; ContentPlannerAgent can be added if complexity warrants it | — Pending |
| Structure + prose quality in scope for Phase 1 | User wants both section structure AND writing quality improvements, not just structural templates | — Pending |
| Security fixes deferred | Critical concerns identified in CONCERNS.md but separate from content generation milestone | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-03 after initialization*
