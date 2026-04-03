# Codebase Concerns

**Analysis Date:** 2026-04-03

---

## Critical Security Concerns

**Hardcoded Admin Credentials in Settings (HIGH):**
- Issue: `admin_password` defaults to `"admin123"` and `admin_session_secret` defaults to `"dev-secret-change-in-production-min-32-chars"` in source code
- Files: `src/config/settings.py` (lines 69–70)
- Impact: Any deployment that doesn't override these env vars ships with trivially brute-forceable admin access and a known JWT signing secret
- Fix: Remove defaults entirely; fail at startup if not set in production

**Plain-text Password Comparison for Admin Auth (HIGH):**
- Issue: `authenticate_admin()` compares password as plain string: `return password == settings.admin_password`
- Files: `src/core/auth.py` (line 61)
- Impact: Passwords are not hashed even with bcrypt already available in the stack
- Fix: Store a bcrypt hash in settings; use `pwd_context.verify()` already defined in `auth.py`

**Wildcard CORS with Credentials (HIGH):**
- Issue: `allow_origins=["*"]` combined with `allow_credentials=True` — browsers reject this combination, and it exposes API to CSRF
- Files: `src/api/main.py` (lines 203–206)
- Impact: Either credentials are silently dropped or a misconfigured client exposes authenticated endpoints
- Fix: Replace `"*"` with explicit list of allowed origins from environment config

**`cookies.txt` Committed to Git (MEDIUM):**
- Issue: `cookies.txt` is tracked by git (`git ls-files` confirms)
- Files: `cookies.txt` (repo root)
- Impact: May contain session cookies or auth tokens that persist in git history
- Fix: Add to `.gitignore`; rotate any credentials stored there; run `git rm --cached cookies.txt`

**Hardcoded Fallback API Key (LOW-MEDIUM):**
- Issue: `api_key = "test-key-change-me"` used as default fallback when no env var set
- Files: `src/api/indexing.py` (line 36)
- Impact: Silent degraded behavior; may submit to IndexNow with an invalid key without alerting
- Fix: Raise a config error or skip submission instead of silently using a fake key

---

## Tech Debt

**`src/scheduler/jobs.py` is 2,646 lines (HIGH):**
- Single file contains multiple full job implementations, utility functions, and orchestration logic
- Refactoring: split into domain modules under `src/scheduler/jobs/` (e.g., `content_job.py`, `seo_job.py`, `backlink_job.py`)

**Bare `except:` Clauses Silently Suppress Errors (HIGH):**
- Files: `src/scheduler/jobs.py` (lines 1574, 1861, 2075, 2438)
- Impact: Swallows all exceptions including `KeyboardInterrupt`, `SystemExit`; masks real failures
- Fix: Replace with `except (json.JSONDecodeError, ValueError):` or the specific expected exception

**RAG Embeddings Are Stubbed with Zeros (HIGH):**
- Issue: `embedding = [0.0] * 1536` is used as placeholder; actual OpenAI embedding call is commented out
- Files: `src/core/rag.py` (lines 104, 111)
- Impact: RAG/semantic search is non-functional — vector similarity will always return meaningless results
- Fix: Implement `AIProvider.get_embedding()` and call it here; add a feature flag to disable RAG if API key absent

**GSC URL Inspection API is a Stub (MEDIUM):**
- Issue: `_check_via_gsc()` always returns `"not_implemented"` status; feature appears functional but does nothing
- Files: `src/services/index_checker.py` (lines 100–110)
- Impact: Indexing status checks silently fail without surfacing errors to users

**PSEO Rollback State is In-Memory Only (MEDIUM):**
- Issue: `rollback_batch()` relies on `self.published_entries` dict; acknowledged as non-durable with a TODO
- Files: `src/pseo/page_factory.py` (lines 595–600)
- Impact: Published post IDs are lost on process restart; rollback impossible after crash
- Fix: Persist batch publish IDs to Redis or DB on each publication

**`src/services/keyword_strategy_old.py` is Dead Code (LOW):**
- Files: `src/services/keyword_strategy_old.py` (8,414 bytes)
- Fix: Delete the file; it creates confusion alongside `keyword_strategy.py`

**`print(f"DEBUG ERROR: {e}")` Left in Production Code (LOW):**
- Files: `src/integrations/gsc_client.py` (line 487)
- Fix: Replace with `logger.error()`

**Duplicate entry in `requirements.txt` (LOW):**
- `ruff==0.1.14` listed twice (lines 65–66)

---

## Performance Concerns

**`src/services/quality_gate.py` is 1,220 lines (MEDIUM):**
- Monolithic quality gate service with all validation in one class
- Likely reloads and re-validates redundantly within a job cycle

**Broad `except Exception` Throughout Async Jobs (MEDIUM):**
- 238 matches across the codebase; most catch-all handlers log and return degraded results
- Masking transient vs. permanent failures prevents proper retry strategy

**No Connection Pooling Verification for Redis (LOW):**
- `redis_max_connections: int = 50` configured but no evidence of connection pool health checks in workers

---

## Missing Infrastructure / Architecture Risks

**No Input Validation on Admin Config Update Endpoint (MEDIUM):**
- `ConfigUpdateRequest` only requires `config_key: str` and `config_value: str` with no allowlist
- Files: `src/api/admin.py` (lines 28–32)
- Risk: Any authenticated admin can overwrite arbitrary config keys including sensitive credentials

**Outdated Dependencies (MEDIUM):**
- `langchain==0.1.4`, `langgraph==0.0.20`, `langchain-openai==0.0.5` — all from Jan 2024; LangChain 0.1.x reached EOL
- `openai==1.10.0` — current is 1.x but misses significant API improvements since then
- `fastapi==0.109.0` — current is 0.115+

**Test Coverage Gaps (MEDIUM):**
- No tests for: `src/api/admin.py`, `src/core/auth.py`, `src/scheduler/autopilot.py`
- Most tests use heavy mocking; no integration test suite that hits a real DB transaction
- 25 test files for 114 source files (~22% coverage by file count)

**RAG Persistence via Pickle (LOW):**
- Files: `src/core/rag.py` (lines 58, 68)
- `pickle.load()` on untrusted files is a remote code execution risk if the pickle file path is writable by external actors
- Fix: Use JSON serialization or a proper vector store

---

## Risk Assessment

| Concern | Severity | Effort to Fix |
|---|---|---|
| Hardcoded admin password default | Critical | Low |
| Plain-text password comparison | Critical | Low |
| Wildcard CORS + credentials | High | Low |
| RAG embeddings are zero stubs | High | Medium |
| `jobs.py` 2,646-line god file | High | High |
| Bare `except:` clauses | High | Low |
| `cookies.txt` tracked in git | Medium | Low |
| PSEO rollback in-memory state | Medium | Medium |
| GSC index check is a stub | Medium | Medium |
| Outdated LangChain/OpenAI deps | Medium | Medium |
| Missing admin config allowlist | Medium | Low |
| Dead code `keyword_strategy_old.py` | Low | Low |

---

*Concerns audit: 2026-04-03*
