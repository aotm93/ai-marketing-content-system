# External Integrations

**Analysis Date:** 2026-04-03

## APIs & External Services

### AI Providers

| Service | Purpose | Config Location | Auth Method |
|---------|---------|----------------|-------------|
| OpenAI API | Text generation (GPT-4o), image generation (DALL-E 3), embeddings | `src/core/ai_provider.py` | API key via `PRIMARY_AI_API_KEY` env var |
| OpenAI-compatible APIs | Fallback/alternative AI providers (Azure, custom, yunwu) | `src/core/ai_provider.py` | API key + custom `base_url` via `FALLBACK_AI_*` env vars |

**Provider Factory:** `AIProviderFactory` in `src/core/ai_provider.py` supports `openai`, `custom`, `azure`, `yunwu` providers. All use the OpenAI SDK with configurable `base_url`.

**Models configured via settings:**
- Text: `PRIMARY_AI_TEXT_MODEL` (default: `gpt-4o`)
- Image: `PRIMARY_AI_IMAGE_MODEL` (default: `dall-e-3`)
- Embeddings: hardcoded `text-embedding-ada-002` in `src/core/ai_provider.py`

### WordPress

| Service | Purpose | Config Location | Auth Method |
|---------|---------|----------------|-------------|
| WordPress REST API (wp/v2) | Post CRUD, media upload, taxonomy management | `src/integrations/wordpress_client.py` | HTTP Basic Auth (Application Password) |
| Rank Math SEO Plugin | SEO meta read/write via WordPress post meta | `src/integrations/rankmath_adapter.py` | Uses WordPress client auth |

**WordPress Client:** `WordPressClient` class in `src/integrations/wordpress_client.py`
- Base URL: `WORDPRESS_URL` env var
- Auth: `WORDPRESS_USERNAME` + `WORDPRESS_PASSWORD` (Application Password, not login password)
- Operations: create/update/delete posts, upload media, manage categories/tags, get post types
- Timeout: 30 seconds

**Publisher Adapter Pattern:** `src/integrations/publisher_adapter.py` provides `PublisherAdapter` ABC with `WordPressAdapter` (implemented) and `WebhookAdapter` (stub). Factory at `PublisherFactory.create()`.

**SEO Plugin Support:** Configurable via `SEO_PLUGIN` setting (default: `rank_math`). Only Rank Math adapter is implemented. Yoast/AIOSEO are planned but not implemented.

### Google Search Console

| Service | Purpose | Config Location | Auth Method |
|---------|---------|----------------|-------------|
| Google Search Console API | Search analytics, query performance data, URL inspection | `src/integrations/gsc_client.py` | Service Account JSON or OAuth2 |

**GSC Client:** `GSCClient` class in `src/integrations/gsc_client.py`
- Site URL: `GSC_SITE_URL` env var
- Auth method: `GSC_AUTH_METHOD` (`service_account` or `oauth`) - OAuth is NOT fully implemented
- Credentials: `GSC_CREDENTIALS_PATH` (file) or `GSC_CREDENTIALS_JSON` (JSON string in env var)
- Features: Search analytics queries, low-hanging fruit detection, declining page detection, health check
- Data sync: `GSCDataSync` class syncs data to local DB

**GSC Data Sync:** Background job syncs GSC data to `gsc_queries` table. Configurable via:
- `GSC_SYNC_DAYS_BACK` (default: 28 days)
- `GSC_SYNC_INTERVAL_HOURS` (default: 24 hours)
- `GSC_ENABLED` (default: false)

### DataForSEO

| Service | Purpose | Config Location | Auth Method |
|---------|---------|----------------|-------------|
| DataForSEO Labs API | Keyword suggestions, related keywords, bulk difficulty | `src/integrations/keyword_client.py` | HTTP Basic Auth (email:password) |
| DataForSEO Backlinks API | Referring domains, backlink analysis, backlink verification | `src/integrations/dataforseo_backlinks.py` | HTTP Basic Auth (email:password) |

**Keyword Client:** `KeywordClient` in `src/integrations/keyword_client.py`
- Provider: `KEYWORD_API_PROVIDER` (supports `dataforseo` and generic)
- Auth: `KEYWORD_API_USERNAME` (email) + `KEYWORD_API_KEY` (password)
- Base URL: `KEYWORD_API_BASE_URL` (default: `https://api.dataforseo.com`)
- Endpoints used:
  - `/v3/dataforseo_labs/google/keyword_suggestions/live`
  - `/v3/dataforseo_labs/google/related_keywords/live`
  - `/v3/dataforseo_labs/google/bulk_keyword_difficulty/live`
- In-memory cache: 5-minute TTL

**Backlinks Client:** `DataForSEOBacklinksClient` in `src/integrations/dataforseo_backlinks.py`
- Endpoints used:
  - `/v3/backlinks/referring_domains/live`
  - `/v3/backlinks/backlinks/live`

### IndexNow

| Service | Purpose | Config Location | Auth Method |
|---------|---------|----------------|-------------|
| IndexNow API | Instant indexing notification to Bing/Yandex/IndexNow.org | `src/integrations/indexnow.py` | API key in request payload |

**IndexNow Client:** `IndexNowClient` in `src/integrations/indexnow.py`
- Submits URLs to 3 endpoints simultaneously: Bing, IndexNow.org, Yandex
- Supports batch submission (up to 10,000 URLs)
- No persistent config - initialized with `api_key` and `host` parameters

### Resend (Email)

| Service | Purpose | Config Location | Auth Method |
|---------|---------|----------------|-------------|
| Resend Email API | Transactional email sending, batch email, contact management | `src/email/resend_client.py` | Bearer token (`RESEND_API_KEY`) |

**Resend Client:** `ResendClient` in `src/email/resend_client.py`
- Base URL: `https://api.resend.com` (hardcoded)
- Auth: `RESEND_API_KEY` env var
- From email: `RESEND_FROM_EMAIL` env var
- Features: Single email, batch email, contact creation in audiences
- Timeout: 30s (single), 60s (batch)

### Generic Webhook

| Service | Purpose | Config Location | Auth Method |
|---------|---------|----------------|-------------|
| Custom webhooks | Push content events to Zapier, Make, Shopify, etc. | `src/integrations/webhook_adapter.py` | Bearer token (optional) |

**Webhook Adapter:** `WebhookAdapter` in `src/integrations/webhook_adapter.py`
- Sends standardized `content_published` events
- Uses `aiohttp` for async HTTP
- Supports connection verification via ping

## Database Connections

**Primary Database:**
- Engine: PostgreSQL 14 (production), SQLite (local dev fallback)
- Connection config: `src/core/database.py`
- Connection URL: `DATABASE_URL` env var
- Connection pooling: Yes - SQLAlchemy QueuePool
  - `pool_size`: 10 (configurable via `DATABASE_POOL_SIZE`)
  - `max_overflow`: 20 (configurable via `DATABASE_MAX_OVERFLOW`)
  - `pool_pre_ping`: True (connection health checks)
  - `pool_recycle`: 3600 seconds (1 hour)
  - `connect_timeout`: 10 seconds
- Session factory: `SessionLocal` in `src/core/database.py`
- Dependency injection: `get_db()` generator for FastAPI endpoints
- Init retry: 5 attempts with exponential backoff in `init_db()`

**Migration Tool:**
- Alembic 1.13.1
- Config: `alembic.ini`
- Scripts: `migrations/` directory
- Env: `migrations/env.py` (reads URL from settings, falls back to env var)
- Target metadata: `src/models/base.Base.metadata`

**Redis:**
- Connection URL: `REDIS_URL` env var (default: `redis://localhost:6379/0`)
- Max connections: `REDIS_MAX_CONNECTIONS` (default: 50)
- Used by Celery as broker and result backend

## Authentication & Authorization

**Admin Authentication:**
- Method: Password-based with JWT session tokens
- Implementation: `src/core/auth.py`
- Password: `ADMIN_PASSWORD` env var (⚠️ default: `admin123` in dev)
- Session secret: `ADMIN_SESSION_SECRET` env var (⚠️ default: `dev-secret-change-in-production-min-32-chars`)
- Token algorithm: HS256 JWT
- Session expiry: `ADMIN_SESSION_EXPIRE_MINUTES` (default: 1440 = 24 hours)
- Password hashing: bcrypt via passlib (available but admin password comparison is plaintext)
- Rate limiting: 5 login attempts per 5 minutes (`src/core/rate_limiter.py`)

**API Rate Limiting:**
- In-memory rate limiter in `src/core/rate_limiter.py`
- Login: 5 requests / 300 seconds per IP
- API: 30 requests / 60 seconds per IP

**CORS:**
- Configured in `src/api/main.py`: `allow_origins=["*"]` (wide open)

## Third-Party Libraries (with external calls)

| Library | External Service | Purpose |
|---------|-----------------|---------|
| `openai` SDK | OpenAI API / compatible endpoints | Text generation, image generation, embeddings |
| `google-api-python-client` | Google Search Console API | Search analytics data retrieval |
| `google-auth-oauthlib` | Google OAuth2 | GSC authentication |
| `httpx` | WordPress REST API, DataForSEO API, Resend API | HTTP client for all REST integrations |
| `aiohttp` | Custom webhook endpoints | Async webhook publishing |
| `beautifulsoup4` + `lxml` | Target websites | Web scraping for SEO analysis and website profiling |
| `langchain` / `langgraph` | OpenAI API (via langchain-openai) | Agent orchestration and LLM chaining |

## Environment Variables

### Required

| Variable | Purpose | Required |
|----------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `ADMIN_PASSWORD` | Admin panel login password | Yes (has insecure default) |
| `ADMIN_SESSION_SECRET` | JWT signing secret (min 32 chars) | Yes (has insecure default) |

### Recommended

| Variable | Purpose | Required |
|----------|---------|----------|
| `REDIS_URL` | Redis connection for caching/tasks | Recommended (default: `redis://localhost:6379/0`) |
| `ENVIRONMENT` | Runtime environment (`development`/`production`) | No (default: `development`) |
| `PORT` | HTTP server port | No (default: `8080`) |
| `LOG_LEVEL` | Logging verbosity | No (default: `INFO`) |

### AI Provider

| Variable | Purpose | Required |
|----------|---------|----------|
| `PRIMARY_AI_PROVIDER` | AI provider name | No (default: `openai`) |
| `PRIMARY_AI_API_KEY` | API key for primary AI provider | Required for content generation |
| `PRIMARY_AI_BASE_URL` | API base URL | No (default: `https://api.openai.com/v1`) |
| `PRIMARY_AI_TEXT_MODEL` | Text generation model | No (default: `gpt-4o`) |
| `PRIMARY_AI_IMAGE_MODEL` | Image generation model | No (default: `dall-e-3`) |
| `FALLBACK_AI_PROVIDER` | Fallback provider name | No |
| `FALLBACK_AI_API_KEY` | Fallback API key | No |
| `FALLBACK_AI_BASE_URL` | Fallback base URL | No |
| `FALLBACK_AI_TEXT_MODEL` | Fallback text model | No |
| `FALLBACK_AI_IMAGE_MODEL` | Fallback image model | No |

### WordPress

| Variable | Purpose | Required |
|----------|---------|----------|
| `WORDPRESS_URL` | WordPress site URL | Required for publishing |
| `WORDPRESS_USERNAME` | WordPress username | Required for publishing |
| `WORDPRESS_PASSWORD` | WordPress Application Password | Required for publishing |
| `SEO_PLUGIN` | SEO plugin (`rank_math`, `yoast`, `aioseo`) | No (default: `rank_math`) |

### Google Search Console

| Variable | Purpose | Required |
|----------|---------|----------|
| `GSC_SITE_URL` | Site URL in GSC | Required for GSC features |
| `GSC_AUTH_METHOD` | `service_account` or `oauth` | No (default: `service_account`) |
| `GSC_CREDENTIALS_PATH` | Path to service account JSON | One of path/json required |
| `GSC_CREDENTIALS_JSON` | Service account JSON string | One of path/json required |
| `GSC_ENABLED` | Enable GSC integration | No (default: `false`) |
| `GSC_SYNC_DAYS_BACK` | Days to sync | No (default: `28`) |
| `GSC_SYNC_INTERVAL_HOURS` | Sync frequency | No (default: `24`) |

### DataForSEO (Keyword Research & Backlinks)

| Variable | Purpose | Required |
|----------|---------|----------|
| `KEYWORD_API_PROVIDER` | Provider name (`dataforseo`) | No |
| `KEYWORD_API_USERNAME` | DataForSEO login email | Required for keyword features |
| `KEYWORD_API_KEY` | DataForSEO password | Required for keyword features |
| `KEYWORD_API_BASE_URL` | API base URL | No (default: `https://api.dataforseo.com`) |

### Email (Resend)

| Variable | Purpose | Required |
|----------|---------|----------|
| `RESEND_API_KEY` | Resend API key | Required for email features |
| `RESEND_FROM_EMAIL` | Sender email address | No (default: `noreply@example.com`) |

### Autopilot

| Variable | Purpose | Required |
|----------|---------|----------|
| `AUTOPILOT_ENABLED` | Enable autopilot scheduler | No (default: `false`) |
| `AUTOPILOT_MODE` | Mode: `conservative`/`standard`/`aggressive` | No (default: `standard`) |
| `PUBLISH_INTERVAL_MINUTES` | Minutes between publications | No (default: `60`) |
| `MAX_POSTS_PER_DAY` | Daily post limit | No (default: `5`) |
| `MAX_CONCURRENT_JOBS` | Parallel job limit | No (default: `2`) |
| `AUTO_PUBLISH` | Direct publish vs draft | No (default: `false`) |
| `MAX_TOKENS_PER_DAY` | Daily token budget | No (default: `100000`) |
| `ACTIVE_HOURS_START` | Start hour (0-23) | No (default: `8`) |
| `ACTIVE_HOURS_END` | End hour (0-23) | No (default: `22`) |

### Database Tuning

| Variable | Purpose | Required |
|----------|---------|----------|
| `DATABASE_POOL_SIZE` | SQLAlchemy pool size | No (default: `10`) |
| `DATABASE_MAX_OVERFLOW` | Pool overflow limit | No (default: `20`) |
| `REDIS_MAX_CONNECTIONS` | Redis max connections | No (default: `50`) |

## Webhooks & Event Systems

**Internal Event Bus:**
- `EventBus` class in `src/core/event_bus.py`
- In-memory pub/sub with async support
- Tracks event history
- Used for loose coupling between components

**Outgoing Webhooks:**
- Generic webhook adapter in `src/integrations/webhook_adapter.py`
- Pushes `content_published` events to configured endpoints
- Supports Zapier, Make, custom endpoints

**Incoming Webhooks:**
- None detected

**IndexNow Notifications:**
- Outbound URL submission to Bing, Yandex, IndexNow.org after content publishing
- Via `src/integrations/indexnow.py`

## Monitoring & Observability

**Error Tracking:**
- No external error tracking service (Sentry, etc.)
- Application logging to `logs/app.log` with rotation (10MB × 5 backups)

**Logs:**
- Python `logging` module with `RotatingFileHandler`
- Console + file output configured in `src/api/main.py`
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Level configurable via `LOG_LEVEL` env var

**Health Check:**
- `GET /health` endpoint in `src/api/main.py`
- Docker HEALTHCHECK: `curl -f http://localhost:${PORT:-8080}/health`
- Reports: system status, autopilot status, environment

**Metrics:**
- `ENABLE_METRICS` setting exists (default: `true`) with `METRICS_PORT` (default: `9090`)
- No Prometheus/metrics endpoint implementation detected

## CI/CD & Deployment

**Hosting:**
- Docker-based deployment (multi-stage `Dockerfile`)
- Zeabur auto-detection in `scripts/entrypoint.sh`
- Heroku-compatible via `Procfile`

**CI Pipeline:**
- No CI/CD configuration detected (no `.github/workflows/`, `.gitlab-ci.yml`, etc.)

**Docker Setup:**
- Multi-stage build: python-builder → frontend-builder → production
- Production image: `python:3.11-slim`
- Non-root user: `appuser`
- Entrypoint: `scripts/entrypoint.sh` (waits for DB + Redis)
- Exposed port: 8080

---

*Integration audit: 2026-04-03*
