# Codebase Structure

**Analysis Date:** 2026-04-03

## Directory Layout

```
bobopkgproject/
├── src/                          # Application source code
│   ├── api/                      # FastAPI route handlers (14 routers)
│   ├── agents/                   # AI agent classes (13 specialists)
│   ├── backlink/                 # Backlink outreach module
│   ├── config/                   # Settings & config utilities
│   ├── conversion/               # Conversion tracking & CTA optimization
│   ├── core/                     # Cross-cutting infrastructure
│   ├── dashboard/                # Next.js 16 frontend (static export)
│   ├── email/                    # Email marketing (Resend + sequences)
│   ├── integrations/             # External service clients (WordPress, GSC, etc.)
│   ├── models/                   # SQLAlchemy ORM + Pydantic data models
│   ├── pseo/                     # Programmatic SEO page factory
│   ├── scheduler/                # Autopilot scheduler + job runner
│   └── services/                 # Business logic services
│       ├── content/              # Content generation pipeline
│       └── research/             # Competitive & trend research
├── migrations/                   # Alembic DB migrations
│   ├── env.py                    # Migration environment config
│   ├── script.py.mako            # Migration template
│   └── versions/                 # Migration version files
├── tests/                        # Test suite
│   ├── agents/                   # Agent integration tests
│   ├── data/                     # Test fixtures
│   ├── integration/              # Integration tests
│   ├── services/                 # Service-level tests
│   └── unit/                     # Unit tests
│       ├── content/              # Content pipeline unit tests
│       ├── scheduler/            # Scheduler unit tests
│       └── services/             # Service unit tests
├── scripts/                      # Operational scripts
├── static/                       # Static assets (admin panel)
│   ├── admin/                    # HTML/CSS/JS admin panel
│   └── js/                       # Client-side tracking & subscription JS
├── docs/                         # Project documentation
├── wordpress/                    # WordPress mu-plugins for integration
│   ├── mu-plugins/               # Rank Math SEO adapter plugin
│   └── wp-content/               # Additional WP plugins
├── wp-content/                   # WordPress mu-plugins (alternate location)
│   └── mu-plugins/               # SEO autopilot subscribe plugin
├── logs/                         # Application log files (gitignored, runtime)
├── .planning/                    # Planning & analysis documents
├── .sisyphus/                    # Sisyphus agent plans & notes
├── .zenflow/                     # Zenflow task specs & reports
├── .env                          # Environment variables (secrets)
├── .env.example                  # Env var template
├── .gitignore                    # Git ignore rules
├── .python-version               # Python version pinning
├── alembic.ini                   # Alembic migration config
├── docker-compose.yml            # Docker Compose (app + postgres + redis)
├── Dockerfile                    # Multi-stage build (python + node)
├── Procfile                      # Process definition (uvicorn)
├── requirements.txt              # Full Python dependencies
├── requirements-prod.txt         # Production-only Python dependencies
├── README.md                     # Project readme
└── sql_app.db                    # SQLite fallback DB (dev only)
```

## Directory Purposes

**`src/api/`:**
- Purpose: FastAPI route handlers — one file per domain area
- Contains: 14 router modules + `main.py` application entry point
- Key files:
  - `src/api/main.py` — FastAPI app, lifespan, router registration, CORS, static mounts
  - `src/api/autopilot.py` — Autopilot control endpoints (start/stop/config/run-now)
  - `src/api/admin.py` — Admin auth, config CRUD, SEO checks, website analysis
  - `src/api/gsc.py` — Google Search Console data sync & analytics
  - `src/api/content_intelligence.py` — Research triggers, topic generation, outlines
  - `src/api/email.py` — Email subscription, sequences, broadcast
  - `src/api/conversion.py` — CTA tracking, recommendation engine
  - `src/api/pseo.py` — Programmatic SEO page generation
  - `src/api/quality_gate.py` — Content quality validation
  - `src/api/cannibalization.py` — Keyword cannibalization detection
  - `src/api/topic_map.py` — Topic map management
  - `src/api/opportunities.py` — SEO opportunity discovery
  - `src/api/indexing.py` — Index status monitoring
  - `src/api/job_logs.py` — Job execution log viewing
  - `src/api/keywords.py` — Keyword CRUD

**`src/agents/`:**
- Purpose: AI agent classes that use LLMs for marketing tasks
- Contains: 13 specialist agents + base class
- Key files:
  - `src/agents/base_agent.py` — `BaseAgent` ABC with `execute()`, `generate_text()`, `publish_event()`
  - `src/agents/orchestrator.py` — Marketing Director — coordinates strategy
  - `src/agents/content_creator.py` — Content Writer — generates articles using editorial blueprints + `ProfessionalContentWriter`
  - `src/agents/keyword_strategist.py` — Keyword Research specialist
  - `src/agents/quality_gate.py` — Content quality enforcer with RAG fact-checking
  - `src/agents/brief_builder.py` — Creates content briefs
  - `src/agents/content_refresh.py` — Updates existing content
  - `src/agents/internal_link.py` — Internal linking optimization
  - `src/agents/market_researcher.py` — Market research via LLM
  - `src/agents/media_creator.py` — Image generation
  - `src/agents/opportunity_scoring.py` — Opportunity scoring
  - `src/agents/publish_manager.py` — Publishing workflow
  - `src/agents/title_meta_optimizer.py` — Title and meta description optimization

**`src/core/`:**
- Purpose: Cross-cutting infrastructure shared by all layers
- Contains: Database, auth, AI provider, event bus, plugin manager, RAG, rate limiter
- Key files:
  - `src/core/database.py` — SQLAlchemy engine, `SessionLocal`, `get_db()` dependency, `init_db()` with retry
  - `src/core/auth.py` — JWT auth with bcrypt hashing, admin role checking, cookie/header token extraction
  - `src/core/ai_provider.py` — `AIProviderInterface` ABC, `OpenAICompatibleProvider`, `AIProviderFactory`
  - `src/core/event_bus.py` — `EventBus` pub/sub with async support, global `event_bus` singleton
  - `src/core/plugin_manager.py` — `PluginInterface` ABC, `PluginManager` lifecycle manager
  - `src/core/rag.py` — `KnowledgeBase` with document storage, keyword-based search (embedding placeholder)
  - `src/core/rate_limiter.py` — In-memory rate limiter for API endpoints (login + general)

**`src/config/`:**
- Purpose: Application settings via pydantic-settings with DB-backed overrides
- Key files:
  - `src/config/settings.py` — `Settings` class (env vars for AI, DB, Redis, WordPress, SEO, autopilot, GSC), global `settings` instance
  - `src/config/utils.py` — `load_settings_from_db()`, `update_config_value()`, `init_system_config()`
  - `src/config/__init__.py` — Exports `settings` instance

**`src/models/`:**
- Purpose: SQLAlchemy ORM models + Pydantic data models
- Key files:
  - `src/models/base.py` — `Base` declarative base, `TimestampMixin` (created_at, updated_at)
  - `src/models/__init__.py` — Imports all models (required for `init_db()` auto-registration)
  - `src/models/content.py` — `Content` model (title, body, status, wordpress_post_id)
  - `src/models/keyword.py` — `Keyword` model (keyword, volume, difficulty, status)
  - `src/models/config.py` — `SystemConfig` model (key-value dynamic config)
  - `src/models/job_runs.py` — `JobRun`, `ContentAction`, `AutopilotRun` models (audit logging)
  - `src/models/gsc_data.py` — `GSCQuery`, `GSCPageSummary`, `Opportunity`, `TopicCluster`
  - `src/models/seo_context.py` — `SEOContext` Pydantic model (pipeline DTO, not ORM)
  - `src/models/content_intelligence.py` — `ContentTopic`, `ResearchCacheEntry`, `APICallLog`, `ContentOutline`, `OptimizedTitle`
  - `src/models/agent_execution.py` — `AgentExecution` model
  - `src/models/backlink.py` — `BacklinkOpportunityModel`
  - `src/models/email.py` — `EmailSubscriber`
  - `src/models/email_sequence.py` — `EmailSequence`, `EmailSequenceStep`
  - `src/models/email_enrollment.py` — `EmailEnrollment`
  - `src/models/indexing_status.py` — Indexing status tracking
  - `src/models/content_action.py` — Content action tracking
  - `src/models/conversion.py` — Conversion tracking models

**`src/services/`:**
- Purpose: Business logic services, decoupled from API and agents
- Key files:
  - `src/services/keyword_strategy.py` — `ContentAwareKeywordGenerator` (937 lines) — generates keywords from website analysis
  - `src/services/content_intelligence.py` — `ContentIntelligenceService`, `ValueScorer`, `TopicGenerator`
  - `src/services/quality_gate.py` — `QualityGateService` (1254 lines) — multi-algorithm duplicate/quality checking
  - `src/services/cannibalization.py` — `CannibalizationDetector` (879 lines) — semantic similarity, URL pattern analysis
  - `src/services/topic_map.py` — `TopicMapService` (837 lines) — hub-spoke structure, internal link recommendations
  - `src/services/website_analyzer.py` — `WebsiteAnalyzer` — extracts business profile from WordPress content
  - `src/services/product_knowledge.py` — `ProductCatalogMatcher` — maps keywords to categories/tags/products
  - `src/services/index_checker.py` — Index status verification
  - `src/services/gsc_usage_tracker.py` — GSC API usage tracking

**`src/services/content/`:**
- Purpose: Content creation pipeline components
- Key files:
  - `src/services/content/professional_writer.py` — `ProfessionalContentWriter` for LLM-based article generation
  - `src/services/content/hook_optimizer.py` — `HookOptimizer` for title A/B testing and CTR optimization
  - `src/services/content/intent_analyzer.py` — `SearchIntentAnalyzer` for search intent classification
  - `src/services/content/outline_generator.py` — `OutlineGenerator` for content structure planning
  - `src/services/content/research_assistant.py` — Research assistant for content enrichment
  - `src/services/content/title_matcher.py` — Title matching utilities

**`src/services/research/`:**
- Purpose: Competitive and trend research
- Key files:
  - `src/services/research/cache.py` — `ResearchCache` for caching API results
  - `src/services/research/competitive_analyzer.py` — Competitor content analysis
  - `src/services/research/trend_research.py` — Trend detection
  - `src/services/research/pain_point_analyzer.py` — Customer pain point extraction
  - `src/services/research/orchestrator.py` — Research workflow coordination

**`src/scheduler/`:**
- Purpose: Autopilot scheduling and job execution
- Key files:
  - `src/scheduler/autopilot.py` — `AutopilotScheduler` (APScheduler-based), `AutopilotConfig`, `AutopilotMode`
  - `src/scheduler/job_runner.py` — `JobRunner` with rate limiting, concurrency (semaphore), retry, timeout
  - `src/scheduler/jobs.py` — `content_generation_job()` (main pipeline, 1600+ lines), `register_all_jobs()`, rotation/selection logic

**`src/integrations/`:**
- Purpose: External service adapters
- Key files:
  - `src/integrations/wordpress_client.py` — `WordPressClient` (REST API, posts, media, taxonomy)
  - `src/integrations/publisher_adapter.py` — `PublisherAdapter` ABC, `WordPressAdapter`, `WebhookAdapter`, `PublisherFactory`
  - `src/integrations/rankmath_adapter.py` — `RankMathAdapter` for SEO meta via WordPress REST API
  - `src/integrations/gsc_client.py` — `GSCClient`, `GSCDataSync` for Google Search Console
  - `src/integrations/keyword_client.py` — External keyword research API client
  - `src/integrations/dataforseo_backlinks.py` — DataForSEO backlink analysis
  - `src/integrations/indexnow.py` — IndexNow search engine notification
  - `src/integrations/sitemap_manager.py` — XML sitemap management
  - `src/integrations/indexing_monitor.py` — Index status monitoring
  - `src/integrations/webhook_adapter.py` — Webhook-based integration (stub)

**`src/email/`:**
- Purpose: Email marketing capabilities
- Key files:
  - `src/email/resend_client.py` — Resend API client for transactional email
  - `src/email/sequence_engine.py` — Email sequence automation engine

**`src/backlink/`:**
- Purpose: Backlink outreach automation
- Key files:
  - `src/backlink/copilot.py` — Backlink opportunity discovery
  - `src/backlink/outreach_sender.py` — Outreach email automation

**`src/conversion/`:**
- Purpose: Conversion rate optimization
- Key files:
  - `src/conversion/dynamic_cta.py` — `CTATracker`, `CTARecommendationEngine`
  - `src/conversion/attribution.py` — `ConversionTracker`, multi-touch attribution
  - `src/conversion/lead_quality.py` — Lead scoring

**`src/pseo/`:**
- Purpose: Programmatic SEO page generation (template-based)
- Key files:
  - `src/pseo/page_factory.py` — `pSEOFactory`, `BatchJobQueue` for bulk page generation
  - `src/pseo/dimension_model.py` — Dimension model for parametric page variation
  - `src/pseo/components.py` — HTML template components
  - `src/pseo/indexing.py` — pSEO-specific indexing utilities

**`src/dashboard/`:**
- Purpose: Next.js 16 admin dashboard (static export)
- Key files:
  - `src/dashboard/package.json` — Next.js 16, React 19, Tailwind CSS 4, TypeScript
  - `src/dashboard/app/layout.tsx` — Root layout
  - `src/dashboard/app/page.tsx` — Dashboard home page
  - `src/dashboard/lib/api.ts` — API client for backend communication
  - `src/dashboard/types/index.ts` — TypeScript type definitions

## Key File Locations

**Entry Points:**
- `src/api/main.py`: FastAPI application entry point — run via `uvicorn src.api.main:app`
- `scripts/entrypoint.sh`: Docker entrypoint — waits for DB/Redis, then starts uvicorn
- `Procfile`: Process definition for PaaS deployment
- `migrations/env.py`: Alembic migration runner

**Configuration:**
- `src/config/settings.py`: All application settings (Pydantic Settings)
- `src/config/utils.py`: DB config load/save utilities
- `.env`: Environment variables (secrets — DO NOT READ)
- `.env.example`: Env var template
- `alembic.ini`: Alembic migration configuration
- `docker-compose.yml`: Docker services (app, postgres, redis)
- `Dockerfile`: Multi-stage build (Python builder → Node builder → production)

**Core Logic:**
- `src/scheduler/jobs.py`: Main content generation pipeline (largest single file, 1600+ lines)
- `src/agents/content_creator.py`: AI-powered article generation (887 lines)
- `src/services/quality_gate.py`: Content quality validation (1254 lines)
- `src/services/keyword_strategy.py`: Content-aware keyword generation (937 lines)
- `src/services/cannibalization.py`: Cannibalization detection (879 lines)
- `src/services/topic_map.py`: Topic mapping service (837 lines)

**Testing:**
- `tests/unit/`: Unit tests (scheduler, services, content)
- `tests/integration/`: Integration tests (admin, publishing, GSC, content intelligence)
- `tests/agents/`: Agent-level integration tests
- `tests/data/`: Test fixtures and sample data

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `keyword_strategy.py`, `content_creator.py`)
- Test files: `test_*.py` (e.g., `test_value_scorer.py`)
- TypeScript: `camelCase.ts` or `kebab-case.tsx`

**Directories:**
- Package names: `snake_case` (e.g., `content_intelligence/`)
- Test directories mirror source structure (`tests/unit/services/`, `tests/integration/`)

**Classes:**
- `PascalCase` (e.g., `ContentCreatorAgent`, `AutopilotScheduler`, `WordPressClient`)

**Models:**
- SQLAlchemy ORM: `PascalCase` class, `snake_case` table name (e.g., `class JobRun` → `job_runs`)
- Pydantic: `PascalCase` (e.g., `SEOContext`, `PublishableContent`)

## Where to Add New Code

**New API Endpoint:**
- Create router file: `src/api/{domain}.py`
- Define Pydantic request/response models inline or in `src/models/`
- Register router in `src/api/main.py` with `app.include_router()`
- Protect admin endpoints with `Depends(get_current_admin)`

**New AI Agent:**
- Create: `src/agents/{agent_name}.py`
- Extend `BaseAgent` from `src/agents/base_agent.py`
- Implement `execute(self, task: Dict[str, Any]) -> Dict[str, Any]`
- Register in `src/scheduler/jobs.py` if used by autopilot

**New Service:**
- Create: `src/services/{service_name}.py`
- For sub-packages: `src/services/{domain}/{module}.py`
- Keep services stateless; inject dependencies (DB session, clients)

**New Integration/External Client:**
- Create: `src/integrations/{service}_client.py`
- Follow adapter pattern from `src/integrations/publisher_adapter.py`
- Add API key settings to `src/config/settings.py`

**New Database Model:**
- Create: `src/models/{entity}.py`
- Inherit from `Base` and `TimestampMixin`
- Import in `src/models/__init__.py` (required for `init_db()` auto-registration)
- Create migration: `alembic revision --autogenerate -m "description"`

**New Scheduled Job:**
- Define async job function in `src/scheduler/jobs.py`
- Register in `register_all_jobs()` function
- Add to `JOB_REGISTRY` dict for retry support

**New Dashboard Page:**
- Create: `src/dashboard/app/{page}/page.tsx`
- Use API client from `src/dashboard/lib/api.ts`

**Utilities:**
- Shared helpers: `src/core/` (for cross-cutting) or `src/services/` (for domain-specific)
- Config utilities: `src/config/utils.py`

## Special Directories

**`migrations/`:**
- Purpose: Alembic database migration scripts
- Generated: Yes (via `alembic revision --autogenerate`)
- Committed: Yes

**`logs/`:**
- Purpose: Application log files (RotatingFileHandler)
- Generated: Yes (runtime)
- Committed: No (created by `os.makedirs` in `main.py`)

**`src/dashboard/node_modules/`:**
- Purpose: Node.js dependencies for dashboard
- Generated: Yes (`npm ci`)
- Committed: No (gitignored)

**`src/dashboard/out/`:**
- Purpose: Next.js static export build output
- Generated: Yes (`npm run build`)
- Committed: No (built in Docker)

**`static/admin/`:**
- Purpose: Legacy HTML admin panel (index.html, logs.html, opportunities.html)
- Generated: No
- Committed: Yes

**`wordpress/` and `wp-content/`:**
- Purpose: WordPress mu-plugins for Rank Math SEO integration and subscriber tracking
- Generated: No
- Committed: Yes (copied to WordPress installations manually)

**`.ruff_cache/`:**
- Purpose: Ruff linter cache
- Generated: Yes
- Committed: No (should be gitignored)

## Configuration Files

| File | Purpose |
|------|---------|
| `src/config/settings.py` | Application settings (Pydantic Settings from env vars) |
| `.env` | Environment variables with secrets (DO NOT READ) |
| `.env.example` | Template for required environment variables |
| `alembic.ini` | Alembic migration configuration |
| `docker-compose.yml` | Docker service definitions (app + postgres + redis) |
| `Dockerfile` | Multi-stage Docker build (Python + Node → production) |
| `Procfile` | PaaS process definition (`web: uvicorn ...`) |
| `requirements.txt` | Full Python dependencies (dev + prod + test) |
| `requirements-prod.txt` | Production-only Python dependencies |
| `.python-version` | Python version pinning |
| `.dockerignore` | Docker build context exclusions |
| `.gitignore` | Git ignore rules |
| `src/dashboard/package.json` | Dashboard Node.js dependencies |
| `src/dashboard/tsconfig.json` | TypeScript configuration |
| `src/dashboard/next.config.ts` | Next.js configuration |
| `src/dashboard/postcss.config.mjs` | PostCSS configuration (Tailwind) |
| `src/dashboard/eslint.config.mjs` | ESLint configuration |

## Module Dependency Map

**`src/api/` depends on:** `src/core/auth`, `src/core/database`, `src/config/`, `src/scheduler/`, `src/services/`, `src/integrations/`, `src/models/`

**`src/agents/` depends on:** `src/core/ai_provider`, `src/core/event_bus`, `src/services/content/`, `src/services/research/`

**`src/scheduler/` depends on:** `src/config/`, `src/core/database`, `src/models/`, `src/integrations/`, `src/services/`, `src/agents/`

**`src/services/` depends on:** `src/config/`, `src/core/`, `src/models/`, `src/integrations/`

**`src/integrations/` depends on:** `src/config/settings`

**`src/models/` depends on:** `src/models/base` (no upward dependencies)

**`src/core/` depends on:** `src/config/settings`, `src/models/base`

**`src/config/` depends on:** `src/models/config` (for DB config utils only)

**`src/email/` depends on:** `src/config/settings`

**`src/backlink/` depends on:** `src/config/settings`, `src/integrations/`

**`src/conversion/` depends on:** (self-contained, minimal external deps)

**`src/pseo/` depends on:** `src/integrations/`, `src/config/`

---

*Structure analysis: 2026-04-03*
