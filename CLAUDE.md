<!-- GSD:project-start source:PROJECT.md -->
## Project

**BoboPkg SEO Automation Platform**

An AI-powered SEO content automation platform that autonomously generates, optimizes, and publishes articles to WordPress. It uses a multi-agent pipeline (keyword discovery → content planning → AI writing → quality gate → publishing) driven by an APScheduler autopilot, integrating with Google Search Console, DataForSEO, Rank Math SEO, and OpenAI-compatible LLMs.

**Core Value:** The autopilot reliably publishes SEO-optimized articles that are structurally matched to their keyword intent — so every article earns its ranking by actually serving what the searcher needs.

### Constraints

- **Tech Stack**: Python 3.11, FastAPI, LangChain 0.1.x, OpenAI SDK 1.10.0 — must work within current dependency versions; no major upgrades in scope
- **Integration**: Must plug into existing `SEOContext` DTO and `ContentCreatorAgent` without breaking the current autopilot pipeline
- **Architecture**: Single-container deployment; no new background workers or services; changes stay within the existing modular monolith
- **Backward Compatibility**: Existing WordPress publishing, quality gate, and scheduler flows must continue to work after changes
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.11 - Backend API, agents, services, integrations (from `.python-version`, `Dockerfile`)
- TypeScript ~5.x - Frontend dashboard (from `src/dashboard/tsconfig.json`, `src/dashboard/package.json`)
- Bash - Entrypoint and utility scripts (`scripts/entrypoint.sh`)
- SQL - Database migrations (`migrations/versions/`)
- HTML/CSS - Static admin interface (`static/admin/`), dashboard styling via Tailwind CSS
## Runtime
- Python 3.11-slim (Docker production image)
- Node.js 20 (Docker build stage for dashboard)
- pip (Python) - `requirements.txt`, `requirements-prod.txt`
- npm (Node.js) - `src/dashboard/package.json`, `src/dashboard/package-lock.json`
- Lockfile: `package-lock.json` present for Node.js; no `pip.lock` / `Pipfile.lock`
## Frameworks
- FastAPI 0.109.0 - HTTP API framework (`src/api/main.py`)
- Uvicorn 0.27.0 - ASGI server (`Procfile`, `scripts/entrypoint.sh`)
- Pydantic 2.5.3 - Data validation and serialization
- Pydantic-Settings 2.1.0 - Environment-based configuration (`src/config/settings.py`)
- Next.js 16.1.5 - Frontend dashboard, static export mode (`src/dashboard/next.config.ts`)
- React 19.2.3 - UI rendering (`src/dashboard/package.json`)
- OpenAI SDK 1.10.0 - AI text/image generation (`src/core/ai_provider.py`)
- LangChain 0.1.4 - LLM orchestration framework
- LangChain-OpenAI 0.0.5 - OpenAI integration for LangChain
- LangGraph 0.0.20 - Agent graph execution
- SQLAlchemy 2.0.25 - ORM and database abstraction (`src/core/database.py`)
- Alembic 1.13.1 - Database migrations (`alembic.ini`, `migrations/`)
- psycopg2-binary 2.9.9 - PostgreSQL driver
- Redis 5.0.1 - Caching and message broker
- Celery 5.3.6 - Distributed task queue
- APScheduler 3.10.4 - Async job scheduling (`src/scheduler/autopilot.py`)
- httpx 0.26.0 - Async HTTP client (primary, used throughout integrations)
- requests 2.31.0 - Synchronous HTTP client
- aiohttp 3.9.1 - Async HTTP for webhook adapter
- pytest 7.4.4 - Test runner
- pytest-asyncio 0.23.3 - Async test support
- pytest-cov 4.1.0 - Coverage reporting
- black 24.1.1 - Code formatter
- ruff 0.1.14 - Linter
- mypy 1.8.0 - Static type checking
- ESLint 9.x - TypeScript/Next.js linting (`src/dashboard/eslint.config.mjs`)
- Tailwind CSS 4.x - Utility-first CSS (`src/dashboard/postcss.config.mjs`)
## Key Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.109.0 | Core API framework - all endpoints built on this |
| `openai` | 1.10.0 | AI text/image generation via OpenAI-compatible API |
| `sqlalchemy` | 2.0.25 | Database ORM - all models and queries |
| `langchain` | 0.1.4 | LLM chain orchestration for agents |
| `langgraph` | 0.0.20 | Agent workflow graph execution |
| `apscheduler` | 3.10.4 | Autopilot scheduling engine |
| `next` | 16.1.5 | Dashboard frontend framework |
| `react` | 19.2.3 | Dashboard UI rendering |
| Package | Version | Purpose |
|---------|---------|---------|
| `redis` | 5.0.1 | Caching, task queue backend |
| `celery` | 5.3.6 | Async task execution |
| `psycopg2-binary` | 2.9.9 | PostgreSQL connectivity |
| `alembic` | 1.13.1 | Schema migrations |
| `uvicorn` | 0.27.0 | Production ASGI server |
| `python-jose` | 3.3.0 | JWT token handling for auth |
| `passlib` | 1.7.4 | Password hashing (bcrypt) |
| Package | Version | Purpose |
|---------|---------|---------|
| `python-wordpress-xmlrpc` | 2.3 | WordPress XML-RPC (legacy, REST API used instead via httpx) |
| `google-api-python-client` | 2.111.0 | Google Search Console integration |
| `google-auth-oauthlib` | 1.2.0 | Google OAuth2 for GSC |
| `beautifulsoup4` | 4.12.3 | HTML parsing for SEO analysis |
| `lxml` | 5.1.0 | XML/HTML parser backend |
| `Pillow` | 10.2.0 | Image processing for media uploads |
| `jinja2` | 3.1.3 | Template rendering for pSEO pages |
## Configuration
- Settings loaded via `pydantic-settings` from `.env` file and environment variables (`src/config/settings.py`)
- Dynamic configuration overlay from database `system_config` table (`src/config/utils.py`)
- Admin panel allows runtime configuration changes stored in DB
- `.env.example` documents all available environment variables
- `src/config/settings.py` - Central settings class (Pydantic `BaseSettings`)
- `src/config/utils.py` - DB-based config loading/updating
- `alembic.ini` - Migration configuration
- `src/dashboard/next.config.ts` - Next.js static export config (`output: 'export'`, `basePath: '/dashboard'`)
- `src/dashboard/tsconfig.json` - TypeScript compilation settings
- `src/dashboard/postcss.config.mjs` - PostCSS with Tailwind CSS
- `src/dashboard/eslint.config.mjs` - ESLint with Next.js rules
- `Dockerfile` - Multi-stage build (python-builder → frontend-builder → production)
- `docker-compose.yml` - Full stack: app + PostgreSQL 14 + Redis 7
- `Procfile` - Heroku/PaaS deployment entry point
- `requirements.txt` - Full dependencies (dev + prod)
- `requirements-prod.txt` - Production-only dependencies (no test/dev tools)
## Database & Storage
- PostgreSQL 14 (via `docker-compose.yml`: `postgres:14-alpine`)
- Fallback: SQLite for local development (`alembic.ini`: `sqlite:///sql_app.db`)
- Connection pooling: QueuePool with `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, 1-hour recycle (`src/core/database.py`)
- Alembic with autogenerate support
- Migration scripts in `migrations/versions/`
- `migrations/env.py` reads URL from `src.config.settings`
- Redis 7 (via `docker-compose.yml`: `redis:7-alpine`)
- Used for task queue backend (Celery) and application caching
- Local filesystem only (`generated_content/` volume mount in Docker)
- RAG knowledge base stored as pickle files in `data/rag_store/` (`src/core/rag.py`)
- No cloud storage integration (S3, GCS, etc.)
## Platform Requirements
- Python 3.11
- Node.js 20 (for dashboard development)
- PostgreSQL 14 or SQLite
- Redis 7 (optional for dev)
- Docker with multi-stage build
- PostgreSQL 14
- Redis 7
- Port 8080 (configurable via `PORT` env var)
- Supports Zeabur deployment (auto-detected in `scripts/entrypoint.sh`)
- Procfile for Heroku-compatible PaaS
- Memory limit: 2GB
- Memory reservation: 512MB
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- `snake_case.py` for all Python source files (e.g., `keyword_strategy.py`, `base_agent.py`)
- `test_<subject>.py` for test files (e.g., `test_quality_gate_catalog.py`)
- `_old` suffix for deprecated files kept as reference (e.g., `keyword_strategy_old.py`)
- `PascalCase` for all classes (e.g., `EnhancedQualityGate`, `ContentAwareKeywordGenerator`)
- `PascalCase` for Pydantic models and dataclasses (e.g., `QualityIssue`, `SimilarityMatch`)
- `PascalCase` for enums (e.g., `IssueSeverity`, `ContentStatus`, `AutopilotMode`)
- Enum members are `UPPER_SNAKE_CASE` (e.g., `DRAFT`, `BLOG_POST`, `CRITICAL`)
- `snake_case` for all functions and methods (e.g., `get_keyword_suggestions`, `balance_route_coverage`)
- `_snake_case` (leading underscore) for private/internal methods (e.g., `_build_candidate`, `_run_generation_cycle`)
- FastAPI route handlers are named descriptively (e.g., `get_keyword_difficulty`, `trigger_sync`)
- `snake_case` (e.g., `keyword_list`, `retry_delay`, `difficulty_map`)
- Module-level loggers always named `logger` (e.g., `logger = logging.getLogger(__name__)`)
- Imported with alias: `from src.api.X import router as X_router`
## Code Style
- Standard Black defaults (88-char line length implied)
- No `ruff.toml` or `pyproject.toml` config found; default rules apply
- Type checking via `mypy==1.8.0`
## Import Organization
- All internal imports use `src.` prefix (e.g., `from src.core.database import get_db`)
- Relative imports used only within `models/` package (e.g., `from .base import Base, TimestampMixin`)
## Error Handling
- FastAPI endpoints: raise `HTTPException(status_code=..., detail=f"...")`
- Service/startup code: broad `except Exception as e` with `logger.warning/error(f"...: {e}")`
- Retry with exponential backoff in `src/core/database.py:init_db` (max 5 retries, doubling delay)
- Bare `except:` used in `health_check` to silently swallow autopilot probe errors — avoid this pattern
- Validation errors raised as `HTTPException(status_code=400, ...)` before hitting service layer
## Logging
- Configured centrally in `src/api/main.py` via `logging.basicConfig`
- Format: `'%(asctime)s - %(name)s - %(levelname)s - %(message)s'`
- Handlers: `StreamHandler` (console) + `RotatingFileHandler` (`logs/app.log`, 10 MB, 5 backups)
- Level controlled by `settings.log_level` (default `"INFO"`)
- `logger.info(...)` — startup events, successful operations, state changes
- `logger.warning(...)` — recoverable failures, missing optional config, timeouts
- `logger.error(...)` — fatal failures that should alert
## DB Access
- `get_db()` in `src/core/database.py` yields a `SessionLocal()` and closes it in `finally`
- Never pass a FastAPI-injected `db` session to a background task — create a new `SessionLocal()` instead (noted as an issue in `src/api/gsc.py`)
- All ORM models inherit from `Base` (`src/models/base.py`) and `TimestampMixin`
- `TimestampMixin` provides `created_at` / `updated_at` columns (auto-populated via `default`/`onupdate`)
- Enums stored as SQLAlchemy `Enum` columns
- `pydantic-settings` `BaseSettings` in `src/config/settings.py`
- Loaded from `.env` file; accessed as `settings.<field>` throughout codebase
## Module Design
- One `router` per file in `src/api/`, using `APIRouter(prefix="...", tags=[...])`
- Pydantic request/response models defined in same file as router
- All agents extend `BaseAgent` (`src/agents/base_agent.py`) and implement `async execute(task) -> dict`
- Agents are constructed with optional `ai_provider` and `event_bus` dependencies
- Pure business logic in `src/services/`; no HTTP or DB layer — accept DB session or data as params
- Dataclasses (`@dataclass`) used for internal data transfer objects (e.g., `QualityIssue`, `SimilarityMatch`)
## Comments
- Module-level docstrings on all files with multi-feature services (triple-quoted)
- Class docstrings on all public classes
- Function docstrings on all public API endpoints and service methods
- Inline comments for non-obvious logic, config values, and workarounds
- One-line docstrings for simple functions; multi-line for complex ones
- `# BUG-NNN:` prefix used to reference tracked bugs in comments
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Multi-agent AI system with an orchestrator coordinating specialist agents
- Scheduler-based autopilot for autonomous content generation and publishing
- Adapter pattern for external integrations (WordPress, SEO plugins, keyword APIs)
- Event bus for loose coupling between components
- Factory patterns for AI providers and publisher adapters
- Pydantic Settings for configuration with database-backed overrides at runtime
## Layers
- Purpose: HTTP request handling via FastAPI routers. Validates input, delegates to services/scheduler, returns JSON.
- Location: `src/api/`
- Contains: 14 router modules, each with Pydantic request/response models
- Depends on: `src/core/auth`, `src/core/database`, `src/scheduler/`, `src/services/`, `src/integrations/`
- Used by: External clients (dashboard, admin panel, WordPress plugins)
- Purpose: Cross-cutting concerns — database, authentication, AI providers, event bus, plugin system, rate limiting, RAG.
- Location: `src/core/`
- Contains: Database engine/session factory, JWT auth, AI provider abstraction, event bus singleton, plugin manager, rate limiter, RAG knowledge base
- Depends on: `src/config/`, `src/models/base.py`
- Used by: All other layers
- Purpose: AI-powered specialist agents that perform marketing tasks (content creation, SEO optimization, keyword research, etc.) via LLM calls.
- Location: `src/agents/`
- Contains: 13 agent classes inheriting from `BaseAgent`, each with an `execute()` method
- Depends on: `src/core/ai_provider`, `src/core/event_bus`, `src/services/content/`
- Used by: `src/scheduler/jobs.py` (content generation pipeline)
- Purpose: Business logic — keyword strategy, content intelligence, quality gates, cannibalization detection, topic mapping, website analysis.
- Location: `src/services/`
- Contains: Domain services, sub-packages for `content/` (writing pipeline) and `research/` (competitive analysis, trend research)
- Depends on: `src/models/`, `src/core/`, `src/integrations/`
- Used by: `src/agents/`, `src/api/`, `src/scheduler/`
- Purpose: Autonomous content generation loop — APScheduler-based autopilot with rate limiting, concurrency control, retry logic, and job auditing.
- Location: `src/scheduler/`
- Contains: `AutopilotScheduler`, `JobRunner`, job definitions
- Depends on: `src/services/`, `src/integrations/`, `src/agents/`, `src/models/`, `src/core/database`
- Used by: `src/api/autopilot.py` (control endpoints), startup lifespan in `src/api/main.py`
- Purpose: External service clients — WordPress REST API, Google Search Console, Rank Math SEO, DataForSEO, IndexNow, sitemap management.
- Location: `src/integrations/`
- Contains: 10 integration modules with adapter patterns
- Depends on: `src/config/settings`
- Used by: `src/services/`, `src/scheduler/jobs.py`, `src/api/`
- Purpose: SQLAlchemy ORM models and Pydantic data models for all domain entities.
- Location: `src/models/`
- Contains: 15+ model files covering content, keywords, GSC data, job runs, email, backlinks, SEO context, content intelligence
- Depends on: `src/models/base.py` (declarative base + timestamp mixin)
- Used by: All layers that interact with the database
- Purpose: Application settings via pydantic-settings (env vars + .env) with database-backed dynamic overrides.
- Location: `src/config/`
- Contains: `settings.py` (Settings class), `utils.py` (DB config load/save)
- Depends on: `src/models/config.py` (SystemConfig table)
- Used by: All layers via `from src.config import settings`
- `src/email/`: Email marketing — Resend client, sequence engine
- `src/backlink/`: Backlink outreach — copilot, outreach sender
- `src/conversion/`: Conversion optimization — attribution, dynamic CTAs, lead quality
- `src/pseo/`: Programmatic SEO — page factory, dimension models, component templates
- `src/dashboard/`: Next.js 16 frontend (static export, served by FastAPI)
## Data Flow
- **Application state:** PostgreSQL database (via SQLAlchemy ORM)
- **Session state:** JWT tokens (stateless, cookie or header)
- **Scheduler state:** In-memory (`AutopilotScheduler` counters, `JobRunner` history), with `job_runs` DB persistence for audit
- **Cache strategy:** In-memory website profile cache with configurable TTL (default 7 days), in-memory research cache via `ResearchCacheEntry` model
- **Configuration state:** Dual-source — `.env` file for defaults, `system_config` DB table for runtime overrides
## Key Abstractions
- Purpose: Abstract base class for all AI agents
- Examples: `src/agents/content_creator.py`, `src/agents/orchestrator.py`, `src/agents/keyword_strategist.py`, `src/agents/quality_gate.py`
- Pattern: Template Method — subclasses implement `execute()`, base class provides `generate_text()` and `publish_event()`
- Purpose: Abstract interface for LLM providers (text generation, image generation, embeddings)
- Examples: `OpenAICompatibleProvider` (supports OpenAI, Azure, custom endpoints)
- Pattern: Strategy + Factory — `AIProviderFactory.create_provider()` instantiates correct provider
- Purpose: Abstract interface for multi-platform publishing
- Examples: `WordPressAdapter` (full implementation), `WebhookAdapter` (stub)
- Pattern: Adapter + Factory — `PublisherFactory.create()` creates platform-specific adapter
- Purpose: Central data object passed through the entire content pipeline, ensuring all SEO elements (title, meta, keywords, internal links, outline) are synchronized
- Examples: Created in `src/scheduler/jobs.py`, consumed by agents and publishers
- Pattern: Data Transfer Object (DTO) spanning the full pipeline
- Purpose: Pub/sub mechanism for loose coupling between agents and services
- Examples: Agents publish events like `catalog_analyzed`, `campaign_planned`
- Pattern: Observer — global singleton `event_bus` with async `publish()` and `subscribe()`
- Purpose: Unified job execution with rate limiting, concurrency control, retry with exponential backoff, timeout handling
- Pattern: Command — wraps async job functions with cross-cutting execution concerns
## Entry Points
- Location: `src/api/main.py`
- Triggers: `uvicorn src.api.main:app` (Procfile, entrypoint.sh)
- Responsibilities: FastAPI app creation, router registration, CORS setup, lifespan (startup: DB init, config load, autopilot start, website analysis; shutdown: autopilot stop), static file serving (admin panel, dashboard)
- Location: `src/scheduler/autopilot.py` → started within `src/api/main.py` lifespan
- Triggers: APScheduler interval and cron triggers
- Responsibilities: Content generation cycles, daily summaries, weekly cannibalization scans
- Location: `migrations/env.py` via `alembic`
- Triggers: `alembic upgrade head`
- Responsibilities: Schema evolution for all SQLAlchemy models
- Location: `src/dashboard/` (Next.js 16)
- Triggers: `npm run build` → static export to `out/`, served at `/dashboard`
- Responsibilities: Admin UI for monitoring and configuration
## Error Handling
- `JobRunner._execute_with_retry()`: Configurable retries with exponential backoff (base delay × 2^attempt, capped at max delay)
- `AutopilotScheduler`: Consecutive error tracking → auto-pause after threshold (resets daily)
- API layer: FastAPI `HTTPException` with appropriate status codes
- Database: Retry logic in `init_db()` with exponential backoff (5 attempts)
- Integration clients: Custom exceptions (`WordPressAPIError`, `WordPressConnectionError`)
- Graceful degradation: Content generation falls through 4 keyword sources (GSC → KeywordAPI → ContentIntelligence → Emergency)
## Cross-Cutting Concerns
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
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
