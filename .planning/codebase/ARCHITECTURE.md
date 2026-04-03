# Architecture

**Analysis Date:** 2026-04-03 (refreshed)

## Pattern Overview

**Overall:** Modular monolith — a single FastAPI application organized into domain-specific packages with internal event-driven communication.

**Key Characteristics:**
- Multi-agent AI system with an orchestrator coordinating specialist agents
- Scheduler-based autopilot for autonomous content generation and publishing
- Adapter pattern for external integrations (WordPress, SEO plugins, keyword APIs)
- Event bus for loose coupling between components
- Factory patterns for AI providers and publisher adapters
- Pydantic Settings for configuration with database-backed overrides at runtime

## Layers

**API Layer (`src/api/`):**
- Purpose: HTTP request handling via FastAPI routers. Validates input, delegates to services/scheduler, returns JSON.
- Location: `src/api/`
- Contains: 14 router modules, each with Pydantic request/response models
- Depends on: `src/core/auth`, `src/core/database`, `src/scheduler/`, `src/services/`, `src/integrations/`
- Used by: External clients (dashboard, admin panel, WordPress plugins)

**Core Infrastructure (`src/core/`):**
- Purpose: Cross-cutting concerns — database, authentication, AI providers, event bus, plugin system, rate limiting, RAG.
- Location: `src/core/`
- Contains: Database engine/session factory, JWT auth, AI provider abstraction, event bus singleton, plugin manager, rate limiter, RAG knowledge base
- Depends on: `src/config/`, `src/models/base.py`
- Used by: All other layers

**Agent Layer (`src/agents/`):**
- Purpose: AI-powered specialist agents that perform marketing tasks (content creation, SEO optimization, keyword research, etc.) via LLM calls.
- Location: `src/agents/`
- Contains: 13 agent classes inheriting from `BaseAgent`, each with an `execute()` method
- Depends on: `src/core/ai_provider`, `src/core/event_bus`, `src/services/content/`
- Used by: `src/scheduler/jobs.py` (content generation pipeline)

**Services Layer (`src/services/`):**
- Purpose: Business logic — keyword strategy, content intelligence, quality gates, cannibalization detection, topic mapping, website analysis.
- Location: `src/services/`
- Contains: Domain services, sub-packages for `content/` (writing pipeline) and `research/` (competitive analysis, trend research)
- Depends on: `src/models/`, `src/core/`, `src/integrations/`
- Used by: `src/agents/`, `src/api/`, `src/scheduler/`

**Scheduler Layer (`src/scheduler/`):**
- Purpose: Autonomous content generation loop — APScheduler-based autopilot with rate limiting, concurrency control, retry logic, and job auditing.
- Location: `src/scheduler/`
- Contains: `AutopilotScheduler`, `JobRunner`, job definitions
- Depends on: `src/services/`, `src/integrations/`, `src/agents/`, `src/models/`, `src/core/database`
- Used by: `src/api/autopilot.py` (control endpoints), startup lifespan in `src/api/main.py`

**Integrations Layer (`src/integrations/`):**
- Purpose: External service clients — WordPress REST API, Google Search Console, Rank Math SEO, DataForSEO, IndexNow, sitemap management.
- Location: `src/integrations/`
- Contains: 10 integration modules with adapter patterns
- Depends on: `src/config/settings`
- Used by: `src/services/`, `src/scheduler/jobs.py`, `src/api/`

**Models Layer (`src/models/`):**
- Purpose: SQLAlchemy ORM models and Pydantic data models for all domain entities.
- Location: `src/models/`
- Contains: 15+ model files covering content, keywords, GSC data, job runs, email, backlinks, SEO context, content intelligence
- Depends on: `src/models/base.py` (declarative base + timestamp mixin)
- Used by: All layers that interact with the database

**Configuration (`src/config/`):**
- Purpose: Application settings via pydantic-settings (env vars + .env) with database-backed dynamic overrides.
- Location: `src/config/`
- Contains: `settings.py` (Settings class), `utils.py` (DB config load/save)
- Depends on: `src/models/config.py` (SystemConfig table)
- Used by: All layers via `from src.config import settings`

**Domain Packages:**
- `src/email/`: Email marketing — Resend client, sequence engine
- `src/backlink/`: Backlink outreach — copilot, outreach sender
- `src/conversion/`: Conversion optimization — attribution, dynamic CTAs, lead quality
- `src/pseo/`: Programmatic SEO — page factory, dimension models, component templates
- `src/dashboard/`: Next.js 16 frontend (static export, served by FastAPI)

## Data Flow

**Content Generation Autopilot (Primary Flow):**

1. `AutopilotScheduler._run_generation_cycle()` fires on interval trigger
2. `JobRunner.run_job()` enforces rate limits, concurrency, and retries
3. `content_generation_job()` in `src/scheduler/jobs.py` executes:
   - **Layer 1 — Opportunity Discovery:** GSC → Keyword API → Content Intelligence → Emergency fallback
   - **Layer 2 — Catalog Matching:** `ProductCatalogMatcher` maps keyword to category/tag/product
   - **Layer 3 — SEO Context:** `SEOContext` object created with title, keyword, internal links, outline
   - **Layer 4 — Content Creation:** `ContentCreatorAgent.execute()` → `ProfessionalContentWriter` → LLM generation
   - **Layer 5 — Quality Gate:** `QualityGateService.full_quality_check()` validates content
   - **Layer 6 — Publishing:** `WordPressAdapter.publish()` → WordPress REST API + Rank Math SEO meta
4. `JobRunner` records result to `job_runs` table and updates rate limiter counters

**Admin Configuration Flow:**

1. Admin authenticates via `POST /api/v1/admin/login` → JWT token
2. Config updates via `PUT /api/v1/admin/config` → `update_config_value()` writes to `system_config` table
3. `load_settings_from_db()` refreshes runtime settings from DB
4. Autopilot picks up new config on next cycle or via explicit `/api/v1/autopilot/config` update

**GSC Data Sync Flow:**

1. Admin triggers sync via `POST /api/v1/gsc/sync` or scheduled job
2. `GSCClient` authenticates with service account credentials
3. Query performance data fetched for configured date range
4. Data stored in `gsc_queries` table with deduplication
5. `Opportunity` model scores low-hanging-fruit keywords for autopilot

**State Management:**
- **Application state:** PostgreSQL database (via SQLAlchemy ORM)
- **Session state:** JWT tokens (stateless, cookie or header)
- **Scheduler state:** In-memory (`AutopilotScheduler` counters, `JobRunner` history), with `job_runs` DB persistence for audit
- **Cache strategy:** In-memory website profile cache with configurable TTL (default 7 days), in-memory research cache via `ResearchCacheEntry` model
- **Configuration state:** Dual-source — `.env` file for defaults, `system_config` DB table for runtime overrides

## Key Abstractions

**BaseAgent (`src/agents/base_agent.py`):**
- Purpose: Abstract base class for all AI agents
- Examples: `src/agents/content_creator.py`, `src/agents/orchestrator.py`, `src/agents/keyword_strategist.py`, `src/agents/quality_gate.py`
- Pattern: Template Method — subclasses implement `execute()`, base class provides `generate_text()` and `publish_event()`

**AIProviderInterface (`src/core/ai_provider.py`):**
- Purpose: Abstract interface for LLM providers (text generation, image generation, embeddings)
- Examples: `OpenAICompatibleProvider` (supports OpenAI, Azure, custom endpoints)
- Pattern: Strategy + Factory — `AIProviderFactory.create_provider()` instantiates correct provider

**PublisherAdapter (`src/integrations/publisher_adapter.py`):**
- Purpose: Abstract interface for multi-platform publishing
- Examples: `WordPressAdapter` (full implementation), `WebhookAdapter` (stub)
- Pattern: Adapter + Factory — `PublisherFactory.create()` creates platform-specific adapter

**SEOContext (`src/models/seo_context.py`):**
- Purpose: Central data object passed through the entire content pipeline, ensuring all SEO elements (title, meta, keywords, internal links, outline) are synchronized
- Examples: Created in `src/scheduler/jobs.py`, consumed by agents and publishers
- Pattern: Data Transfer Object (DTO) spanning the full pipeline

**EventBus (`src/core/event_bus.py`):**
- Purpose: Pub/sub mechanism for loose coupling between agents and services
- Examples: Agents publish events like `catalog_analyzed`, `campaign_planned`
- Pattern: Observer — global singleton `event_bus` with async `publish()` and `subscribe()`

**JobRunner (`src/scheduler/job_runner.py`):**
- Purpose: Unified job execution with rate limiting, concurrency control, retry with exponential backoff, timeout handling
- Pattern: Command — wraps async job functions with cross-cutting execution concerns

## Entry Points

**Web Application:**
- Location: `src/api/main.py`
- Triggers: `uvicorn src.api.main:app` (Procfile, entrypoint.sh)
- Responsibilities: FastAPI app creation, router registration, CORS setup, lifespan (startup: DB init, config load, autopilot start, website analysis; shutdown: autopilot stop), static file serving (admin panel, dashboard)

**Scheduler (Embedded):**
- Location: `src/scheduler/autopilot.py` → started within `src/api/main.py` lifespan
- Triggers: APScheduler interval and cron triggers
- Responsibilities: Content generation cycles, daily summaries, weekly cannibalization scans

**Database Migrations:**
- Location: `migrations/env.py` via `alembic`
- Triggers: `alembic upgrade head`
- Responsibilities: Schema evolution for all SQLAlchemy models

**Dashboard (Static Export):**
- Location: `src/dashboard/` (Next.js 16)
- Triggers: `npm run build` → static export to `out/`, served at `/dashboard`
- Responsibilities: Admin UI for monitoring and configuration

## Error Handling

**Strategy:** Multi-layered — retry with exponential backoff at job level, try/except with logging at service level, HTTP exceptions at API level.

**Patterns:**
- `JobRunner._execute_with_retry()`: Configurable retries with exponential backoff (base delay × 2^attempt, capped at max delay)
- `AutopilotScheduler`: Consecutive error tracking → auto-pause after threshold (resets daily)
- API layer: FastAPI `HTTPException` with appropriate status codes
- Database: Retry logic in `init_db()` with exponential backoff (5 attempts)
- Integration clients: Custom exceptions (`WordPressAPIError`, `WordPressConnectionError`)
- Graceful degradation: Content generation falls through 4 keyword sources (GSC → KeywordAPI → ContentIntelligence → Emergency)

## Cross-Cutting Concerns

**Logging:** Python `logging` module with `RotatingFileHandler` (10MB/file, 5 backups) + console. Configured in `src/api/main.py`. Log level dynamically adjustable via admin API.

**Validation:** Pydantic models for API request/response validation. SQLAlchemy models for database schema. `QualityGateService` for content validation (duplicate detection, thin content, SEO checks).

**Authentication:** JWT-based admin auth via `src/core/auth.py`. Single admin role. Supports both Bearer header and session cookie. Rate-limited login (5 attempts/5 min).

**Rate Limiting:** Two levels:
1. API-level: In-memory `RateLimiter` in `src/core/rate_limiter.py` (login: 5/5min, API: 30/min)
2. Job-level: `RateLimiter` in `src/scheduler/job_runner.py` (posts/day, interval between posts)

## API Surface

### Internal APIs (FastAPI Routers)

| Router | Prefix | Purpose |
|--------|--------|---------|
| `src/api/admin.py` | `/api/v1/admin` | Login, config management, SEO checks, website analysis |
| `src/api/autopilot.py` | `/api/v1/autopilot` | Scheduler control, job history, manual triggers |
| `src/api/content.py` | `/api/v1/content` | Content CRUD (stub) |
| `src/api/conversion.py` | `/conversion` | CTA tracking, recommendations, attribution |
| `src/api/pseo.py` | `/api/v1/pseo` | Programmatic SEO page generation |
| `src/api/gsc.py` | `/api/v1/gsc` | GSC data sync, opportunities, analytics |
| `src/api/indexing.py` | `/api/v1/indexing` | Index status monitoring |
| `src/api/opportunities.py` | `/api/v1/opportunities` | SEO opportunity discovery |
| `src/api/topic_map.py` | `/api/v1/topics` | Topic map management |
| `src/api/quality_gate.py` | `/api/v1/quality` | Content quality validation |
| `src/api/cannibalization.py` | `/api/v1/cannibalization` | Keyword cannibalization detection |
| `src/api/job_logs.py` | `/api/v1/jobs` | Job execution logs |
| `src/api/keywords.py` | `/api/v1/keywords` | Keyword management |
| `src/api/email.py` | `/api/v1/email` | Email subscriptions, sequences |
| `src/api/content_intelligence.py` | `/api/v1/content-intelligence` | Research, topic generation, outlines |

### External APIs (Consumed)

| Service | Client | Purpose |
|---------|--------|---------|
| WordPress REST API | `src/integrations/wordpress_client.py` | Post CRUD, media upload, taxonomy |
| Rank Math SEO | `src/integrations/rankmath_adapter.py` | SEO meta management |
| Google Search Console | `src/integrations/gsc_client.py` | Query performance data |
| OpenAI / Compatible LLM | `src/core/ai_provider.py` | Text generation, image generation, embeddings |
| DataForSEO | `src/integrations/dataforseo_backlinks.py`, `src/integrations/keyword_client.py` | Keyword data, backlink analysis |
| IndexNow | `src/integrations/indexnow.py` | Search engine indexing notification |
| Resend | `src/email/resend_client.py` | Transactional email delivery |

## Key Design Decisions

- **Embedded scheduler (not Celery workers):** APScheduler runs within the FastAPI process. Simpler deployment (single container) but limits horizontal scaling. Celery is in requirements but not actively used for job orchestration.
- **Dual configuration (env + DB):** `.env` provides defaults; `system_config` DB table allows runtime changes via admin UI without redeployment.
- **SEOContext as pipeline DTO:** A single Pydantic model carries all SEO decisions through the entire content generation pipeline, preventing misalignment between title, meta, keywords, and content.
- **Multi-source keyword fallback:** Four-tier keyword selection (GSC → Keyword API → Content Intelligence → Emergency) ensures the autopilot never stalls even without external API access.
- **Static dashboard export:** Next.js dashboard is built as a static export and served by FastAPI, avoiding the need for a separate Node.js server in production.
- **WordPress as primary publishing target:** The architecture is built around WordPress via REST API + Rank Math, with adapter pattern ready for additional platforms.

---

*Architecture analysis: 2026-04-03*
