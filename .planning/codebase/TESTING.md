# Testing Patterns

**Analysis Date:** 2026-04-03

## Test Framework

**Runner:** `pytest==7.4.4`
- Config: no `pytest.ini` / `pyproject.toml` found — runs with default discovery
- Async support: `pytest-asyncio==0.23.3`
- Coverage: `pytest-cov==4.1.0`

**Run Commands:**
```bash
pytest                          # Run all tests
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests only
pytest --cov=src --cov-report=html   # With coverage report
```

## Test File Organization

**Structure:**
```
tests/
├── __init__.py
├── unit/
│   ├── content/                # Content service unit tests
│   ├── scheduler/              # Autopilot/scheduler unit tests
│   └── services/               # Domain service unit tests
├── integration/                # Full-stack integration tests
├── agents/                     # Agent-level integration tests
├── services/                   # Top-level service tests (mixed scope)
└── data/                       # Static test fixtures/data files
```

**Naming:**
- Test files: `test_<subject>.py` (e.g., `test_quality_gate_catalog.py`, `test_value_scorer.py`)
- Test classes: `Test<ClassName>` (e.g., `TestValueScorer`, `TestProductCatalogMatcher`)
- Test methods: `test_<what>_<expected_outcome>` (e.g., `test_prefers_tag_page_for_attribute_led_keyword`)

## Test Structure

**Suite Organization:**
```python
class TestMyService:
    """One class per component under test."""

    @pytest.fixture
    def service(self):
        """Fixture returns the SUT instance."""
        return MyService()

    @pytest.fixture
    def base_data(self):
        """Fixture returns shared input data."""
        return MyModel(field="value", ...)

    def test_synchronous_behavior(self, service, base_data):
        # Arrange / Act / Assert (AAA) pattern
        result = service.method(base_data)
        assert result.field == expected

    @pytest.mark.asyncio
    async def test_async_behavior(self, service, base_data):
        result = await service.async_method(base_data)
        assert result is not None
```

**AAA Pattern:**
- `# Arrange`, `# Act`, `# Assert` comments used consistently in complex tests
- Inline comments on fixture setup explain their intent (e.g., `# Lower is better`)

## Mocking

**Framework:** `unittest.mock` (`Mock`, `patch`)

**Patterns:**
```python
# Mock a DB session
from unittest.mock import Mock

@pytest.fixture
def mock_db(self):
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.return_value = None
    return db

# Mock Redis
@pytest.fixture
def mock_redis(self):
    redis = Mock()
    redis.get = Mock(return_value=None)
    redis.set = Mock(return_value=True)
    return redis

# Monkeypatching scheduler internals
monkeypatch.setattr(scheduler.job_runner, "_persist_job_result", noop_persist)
monkeypatch.setattr(scheduler, "pause", fail_pause)
```

**What to Mock:**
- Database sessions (`Session`) — always mock in unit tests via `Mock()`
- Redis clients — always mock in unit tests
- External scheduler hooks (APScheduler internals)

**What NOT to Mock:**
- The service class under test itself
- Pure Python data structures and dataclasses

## Fixtures and Factories

**Location:** Defined inline within test classes as `@pytest.fixture` methods (no shared `conftest.py` found)

**Pattern:**
- Fixtures named after what they produce: `optimizer`, `scorer`, `mock_db`, `base_topic`
- Data builder fixtures return fully-populated domain objects (e.g., `WebsiteProfile`, `ContentTopic`)
- For async tests, dependencies are injected via fixture params: `def cache(self, mock_db, mock_redis)`

## Test Types

**Unit Tests** (`tests/unit/`):
- Scope: single class or function, no real I/O
- DB and Redis dependencies always mocked
- Both sync and async methods covered
- Example: `test_value_scorer.py`, `test_research_cache.py`

**Integration Tests** (`tests/integration/`):
- Scope: full request pipeline or multi-component flow
- Smoke tests hit real external services (Redis, WordPress) via live `.env` credentials
- Example: `smoke_test.py` — verifies Redis ping, WordPress auth, and a mock pipeline
- Most are not safe to run in CI without live credentials

**Agent Tests** (`tests/agents/`):
- Scope: end-to-end agent invocation (content creator pipeline)
- One file: `test_content_creator_integration.py`

## Coverage

**Requirements:** None enforced (no coverage threshold config found)

**View Coverage:**
```bash
pytest --cov=src --cov-report=term-missing
pytest --cov=src --cov-report=html   # HTML report in htmlcov/
```

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_something(self, service, fixture):
    result = await service.async_method(...)
    assert result.field == expected
```

**Error / Boundary Testing:**
```python
def test_minimum_score_calculation(self, scorer, base_topic):
    base_topic.business_intent = 0.0
    # ... set all fields to worst case
    score = scorer.score(base_topic)
    assert score < 0.05
```

**Assertion Style:**
- Plain `assert` statements throughout (no `assertEqual`-style)
- Numeric precision: `assert abs(value - expected) < 0.001`
- Membership: `assert any("taxonomy link" in t.lower() for t in titles)`
- Boolean flags: `assert diagnostic.can_publish is False`

## Coverage Gaps

- No `conftest.py` — no shared fixtures or app test client setup
- `tests/integration/` tests require live external credentials; not CI-safe
- No database integration tests (all DB usage is mocked)
- `src/api/` router endpoints have no dedicated API-level tests (no `httpx.AsyncClient` test client usage found)
- `src/agents/` largely untested except `test_content_creator_integration.py`
