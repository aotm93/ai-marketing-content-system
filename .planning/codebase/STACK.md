# Technology Stack

**Analysis Date:** 2026-04-03

## Languages

**Primary:**
- Python 3.11 - Backend API, agents, services, integrations (from `.python-version`, `Dockerfile`)
- TypeScript ~5.x - Frontend dashboard (from `src/dashboard/tsconfig.json`, `src/dashboard/package.json`)

**Secondary:**
- Bash - Entrypoint and utility scripts (`scripts/entrypoint.sh`)
- SQL - Database migrations (`migrations/versions/`)
- HTML/CSS - Static admin interface (`static/admin/`), dashboard styling via Tailwind CSS

## Runtime

**Environment:**
- Python 3.11-slim (Docker production image)
- Node.js 20 (Docker build stage for dashboard)

**Package Manager:**
- pip (Python) - `requirements.txt`, `requirements-prod.txt`
- npm (Node.js) - `src/dashboard/package.json`, `src/dashboard/package-lock.json`
- Lockfile: `package-lock.json` present for Node.js; no `pip.lock` / `Pipfile.lock`

## Frameworks

**Core:**
- FastAPI 0.109.0 - HTTP API framework (`src/api/main.py`)
- Uvicorn 0.27.0 - ASGI server (`Procfile`, `scripts/entrypoint.sh`)
- Pydantic 2.5.3 - Data validation and serialization
- Pydantic-Settings 2.1.0 - Environment-based configuration (`src/config/settings.py`)
- Next.js 16.1.5 - Frontend dashboard, static export mode (`src/dashboard/next.config.ts`)
- React 19.2.3 - UI rendering (`src/dashboard/package.json`)

**AI/LLM:**
- OpenAI SDK 1.10.0 - AI text/image generation (`src/core/ai_provider.py`)
- LangChain 0.1.4 - LLM orchestration framework
- LangChain-OpenAI 0.0.5 - OpenAI integration for LangChain
- LangGraph 0.0.20 - Agent graph execution

**Database:**
- SQLAlchemy 2.0.25 - ORM and database abstraction (`src/core/database.py`)
- Alembic 1.13.1 - Database migrations (`alembic.ini`, `migrations/`)
- psycopg2-binary 2.9.9 - PostgreSQL driver

**Cache & Queue:**
- Redis 5.0.1 - Caching and message broker
- Celery 5.3.6 - Distributed task queue

**Scheduler:**
- APScheduler 3.10.4 - Async job scheduling (`src/scheduler/autopilot.py`)

**HTTP Clients:**
- httpx 0.26.0 - Async HTTP client (primary, used throughout integrations)
- requests 2.31.0 - Synchronous HTTP client
- aiohttp 3.9.1 - Async HTTP for webhook adapter

**Testing:**
- pytest 7.4.4 - Test runner
- pytest-asyncio 0.23.3 - Async test support
- pytest-cov 4.1.0 - Coverage reporting

**Build/Dev:**
- black 24.1.1 - Code formatter
- ruff 0.1.14 - Linter
- mypy 1.8.0 - Static type checking
- ESLint 9.x - TypeScript/Next.js linting (`src/dashboard/eslint.config.mjs`)
- Tailwind CSS 4.x - Utility-first CSS (`src/dashboard/postcss.config.mjs`)

## Key Dependencies

**Critical:**
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

**Infrastructure:**
| Package | Version | Purpose |
|---------|---------|---------|
| `redis` | 5.0.1 | Caching, task queue backend |
| `celery` | 5.3.6 | Async task execution |
| `psycopg2-binary` | 2.9.9 | PostgreSQL connectivity |
| `alembic` | 1.13.1 | Schema migrations |
| `uvicorn` | 0.27.0 | Production ASGI server |
| `python-jose` | 3.3.0 | JWT token handling for auth |
| `passlib` | 1.7.4 | Password hashing (bcrypt) |

**Integration-Specific:**
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

**Environment:**
- Settings loaded via `pydantic-settings` from `.env` file and environment variables (`src/config/settings.py`)
- Dynamic configuration overlay from database `system_config` table (`src/config/utils.py`)
- Admin panel allows runtime configuration changes stored in DB
- `.env.example` documents all available environment variables

**Key Config Files:**
- `src/config/settings.py` - Central settings class (Pydantic `BaseSettings`)
- `src/config/utils.py` - DB-based config loading/updating
- `alembic.ini` - Migration configuration
- `src/dashboard/next.config.ts` - Next.js static export config (`output: 'export'`, `basePath: '/dashboard'`)
- `src/dashboard/tsconfig.json` - TypeScript compilation settings
- `src/dashboard/postcss.config.mjs` - PostCSS with Tailwind CSS
- `src/dashboard/eslint.config.mjs` - ESLint with Next.js rules

**Build:**
- `Dockerfile` - Multi-stage build (python-builder → frontend-builder → production)
- `docker-compose.yml` - Full stack: app + PostgreSQL 14 + Redis 7
- `Procfile` - Heroku/PaaS deployment entry point
- `requirements.txt` - Full dependencies (dev + prod)
- `requirements-prod.txt` - Production-only dependencies (no test/dev tools)

## Database & Storage

**Primary DB:**
- PostgreSQL 14 (via `docker-compose.yml`: `postgres:14-alpine`)
- Fallback: SQLite for local development (`alembic.ini`: `sqlite:///sql_app.db`)
- Connection pooling: QueuePool with `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, 1-hour recycle (`src/core/database.py`)

**Migrations:**
- Alembic with autogenerate support
- Migration scripts in `migrations/versions/`
- `migrations/env.py` reads URL from `src.config.settings`

**Cache:**
- Redis 7 (via `docker-compose.yml`: `redis:7-alpine`)
- Used for task queue backend (Celery) and application caching

**File Storage:**
- Local filesystem only (`generated_content/` volume mount in Docker)
- RAG knowledge base stored as pickle files in `data/rag_store/` (`src/core/rag.py`)
- No cloud storage integration (S3, GCS, etc.)

## Platform Requirements

**Development:**
- Python 3.11
- Node.js 20 (for dashboard development)
- PostgreSQL 14 or SQLite
- Redis 7 (optional for dev)

**Production:**
- Docker with multi-stage build
- PostgreSQL 14
- Redis 7
- Port 8080 (configurable via `PORT` env var)
- Supports Zeabur deployment (auto-detected in `scripts/entrypoint.sh`)
- Procfile for Heroku-compatible PaaS

**Resource Limits (from `docker-compose.yml`):**
- Memory limit: 2GB
- Memory reservation: 512MB

---

*Stack analysis: 2026-04-03*
