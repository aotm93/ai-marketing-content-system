# Coding Conventions

**Analysis Date:** 2026-04-03

## Naming Patterns

**Files:**
- `snake_case.py` for all Python source files (e.g., `keyword_strategy.py`, `base_agent.py`)
- `test_<subject>.py` for test files (e.g., `test_quality_gate_catalog.py`)
- `_old` suffix for deprecated files kept as reference (e.g., `keyword_strategy_old.py`)

**Classes:**
- `PascalCase` for all classes (e.g., `EnhancedQualityGate`, `ContentAwareKeywordGenerator`)
- `PascalCase` for Pydantic models and dataclasses (e.g., `QualityIssue`, `SimilarityMatch`)
- `PascalCase` for enums (e.g., `IssueSeverity`, `ContentStatus`, `AutopilotMode`)
- Enum members are `UPPER_SNAKE_CASE` (e.g., `DRAFT`, `BLOG_POST`, `CRITICAL`)

**Functions / Methods:**
- `snake_case` for all functions and methods (e.g., `get_keyword_suggestions`, `balance_route_coverage`)
- `_snake_case` (leading underscore) for private/internal methods (e.g., `_build_candidate`, `_run_generation_cycle`)
- FastAPI route handlers are named descriptively (e.g., `get_keyword_difficulty`, `trigger_sync`)

**Variables:**
- `snake_case` (e.g., `keyword_list`, `retry_delay`, `difficulty_map`)
- Module-level loggers always named `logger` (e.g., `logger = logging.getLogger(__name__)`)

**Routers:**
- Imported with alias: `from src.api.X import router as X_router`

## Code Style

**Formatter:** `black==24.1.1`
- Standard Black defaults (88-char line length implied)

**Linter:** `ruff==0.1.14`
- No `ruff.toml` or `pyproject.toml` config found; default rules apply
- Type checking via `mypy==1.8.0`

## Import Organization

**Order (observed):**
1. Standard library (e.g., `asyncio`, `logging`, `os`, `re`)
2. Third-party packages (e.g., `fastapi`, `sqlalchemy`, `pydantic`)
3. Internal `src.*` imports

**Path Aliases:**
- All internal imports use `src.` prefix (e.g., `from src.core.database import get_db`)
- Relative imports used only within `models/` package (e.g., `from .base import Base, TimestampMixin`)

## Error Handling

**Patterns:**
- FastAPI endpoints: raise `HTTPException(status_code=..., detail=f"...")`
- Service/startup code: broad `except Exception as e` with `logger.warning/error(f"...: {e}")`
- Retry with exponential backoff in `src/core/database.py:init_db` (max 5 retries, doubling delay)
- Bare `except:` used in `health_check` to silently swallow autopilot probe errors — avoid this pattern
- Validation errors raised as `HTTPException(status_code=400, ...)` before hitting service layer

## Logging

**Framework:** Standard `logging` module

**Setup Pattern:**
```python
# Per-module logger — use this in every module
logger = logging.getLogger(__name__)
```

**Configuration:**
- Configured centrally in `src/api/main.py` via `logging.basicConfig`
- Format: `'%(asctime)s - %(name)s - %(levelname)s - %(message)s'`
- Handlers: `StreamHandler` (console) + `RotatingFileHandler` (`logs/app.log`, 10 MB, 5 backups)
- Level controlled by `settings.log_level` (default `"INFO"`)

**Level Guidelines (observed):**
- `logger.info(...)` — startup events, successful operations, state changes
- `logger.warning(...)` — recoverable failures, missing optional config, timeouts
- `logger.error(...)` — fatal failures that should alert

## DB Access

**Pattern:** SQLAlchemy ORM via FastAPI dependency injection
```python
# In route handler — always inject via Depends
from src.core.database import get_db
db: Session = Depends(get_db)
```

**Session Lifecycle:**
- `get_db()` in `src/core/database.py` yields a `SessionLocal()` and closes it in `finally`
- Never pass a FastAPI-injected `db` session to a background task — create a new `SessionLocal()` instead (noted as an issue in `src/api/gsc.py`)

**Models:**
- All ORM models inherit from `Base` (`src/models/base.py`) and `TimestampMixin`
- `TimestampMixin` provides `created_at` / `updated_at` columns (auto-populated via `default`/`onupdate`)
- Enums stored as SQLAlchemy `Enum` columns

**Settings:**
- `pydantic-settings` `BaseSettings` in `src/config/settings.py`
- Loaded from `.env` file; accessed as `settings.<field>` throughout codebase

## Module Design

**Routers:**
- One `router` per file in `src/api/`, using `APIRouter(prefix="...", tags=[...])`
- Pydantic request/response models defined in same file as router

**Agents:**
- All agents extend `BaseAgent` (`src/agents/base_agent.py`) and implement `async execute(task) -> dict`
- Agents are constructed with optional `ai_provider` and `event_bus` dependencies

**Services:**
- Pure business logic in `src/services/`; no HTTP or DB layer — accept DB session or data as params
- Dataclasses (`@dataclass`) used for internal data transfer objects (e.g., `QualityIssue`, `SimilarityMatch`)

## Comments

**When to Comment:**
- Module-level docstrings on all files with multi-feature services (triple-quoted)
- Class docstrings on all public classes
- Function docstrings on all public API endpoints and service methods
- Inline comments for non-obvious logic, config values, and workarounds

**Style:**
- One-line docstrings for simple functions; multi-line for complex ones
- `# BUG-NNN:` prefix used to reference tracked bugs in comments
