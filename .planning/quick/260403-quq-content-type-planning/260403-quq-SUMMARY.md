---
phase: 260403-quq-content-type-planning
plan: "01"
type: quick
completed: 2026-04-03
duration: ~45 minutes
tasks_completed: 3
files_changed: 6
commits:
  - d92579f
  - 879f1cf
  - 842e8b7
requirements:
  - ROBUST-01
  - CLASS-01
  - CLASS-02
  - TMPL-01
  - TMPL-02
  - TMPL-03
  - PIPE-01
  - PIPE-02
  - PIPE-03
key_decisions:
  - "JSON-mode LLM (response_format json_object) via existing ai_provider kwargs — no LangChain parsers"
  - "confidence < 0.75 threshold overrides classification to GENERAL silently"
  - "planned_outline takes precedence over ContentOutline in ContentCreatorAgent; empty falls back to existing outline"
  - "GENERAL content type guidance block suppressed in prompt to avoid noise (only injects for non-general types)"
dependency_graph:
  provides:
    - ArticleContentType enum (seo_context.py)
    - ContentTypeTemplate/SectionTemplate dataclasses (content_type_templates.py)
    - ContentPlannerService.plan() (content_planner.py)
    - _run_content_planner() helper (jobs.py)
    - article_content_type + planned_outline keys in SEOContext.to_content_creator_task()
    - content type guidance injection in ContentCreatorAgent._build_synchronized_prompt()
  requires:
    - OpenAICompatibleProvider.generate_text(**kwargs) pass-through (unchanged)
    - SEOContext Pydantic DTO (unchanged except new fields)
  affects:
    - content_generation_job() pipeline flow (jobs.py)
    - ContentCreatorAgent prompt structure (new blocks injected)
tech_stack:
  added: []
  patterns:
    - "Pydantic field_validator with mode='before' for enum coercion"
    - "Non-raising async service: try/except Exception logs warning and returns"
    - "Dataclass catalog pattern for per-content-type writing instructions"
key_files:
  created:
    - src/services/content/content_type_templates.py
    - src/services/content/content_planner.py
    - tests/unit/content/test_content_planner.py
  modified:
    - src/models/seo_context.py
    - src/agents/content_creator.py
    - src/scheduler/jobs.py
---

# Quick Task 260403-quq: Content Type Planning — Summary

**One-liner**: End-to-end content type classification pipeline — JSON-mode LLM classifies title intent into 6 ArticleContentTypes, generates a type-specific H2 outline, and injects structural guidance into every ContentCreatorAgent prompt.

---

## What Was Implemented

### Task 1: Infrastructure (commit d92579f)
- **`ArticleContentType` enum** added to `src/models/seo_context.py` (before `InternalLinkOpportunity`). 6 values: `how_to`, `listicle`, `comparison`, `review`, `pricing`, `general`. Uses `str` mixin for clean JSON serialization.
- **3 new Optional fields** added to `SEOContext`:
  - `article_content_type: Optional[ArticleContentType] = None`
  - `article_content_type_confidence: Optional[float] = None`
  - `planned_outline: List[Dict[str, Any]] = Field(default_factory=list)`
- **`to_content_creator_task()`** updated to include `"article_content_type"` (str value, defaults to `"general"`) and `"planned_outline"` (list, defaults to `[]`).
- **`src/services/content/content_type_templates.py`** (new file): `SectionTemplate` and `ContentTypeTemplate` dataclasses, plus `CONTENT_TYPE_TEMPLATES` dict with all 6 types, each having ≥5 sections (GENERAL has 3) with non-empty `writing_mode` and `section_type`.

### Task 2: ContentPlannerService + bare except fixes + jobs.py wiring (commit 879f1cf)
- **`src/services/content/content_planner.py`** (new file): `ContentPlannerService` with:
  - `PlannerLLMOutput` Pydantic model using `field_validator` to coerce unknown `content_type` values → `GENERAL`
  - `CONFIDENCE_THRESHOLD = 0.75` class constant
  - `async def plan(seo_context)` — single `generate_text(response_format={"type": "json_object"})` call; on success sets 3 SEOContext fields; confidence < 0.75 overrides to GENERAL; all exceptions caught silently
  - `_build_prompt()` injects type-hint signals and article context
- **4 bare `except:` clauses** in `jobs.py` replaced with specific types:
  - Line 1574: `except Exception: pass` (keyword suggestions)
  - Line 1861: `except (json.JSONDecodeError, KeyError, ValueError):` (meta JSON parse)
  - Line 2075: `except (json.JSONDecodeError, KeyError):` (SEO optimization JSON parse)
  - Line 2438: `except (json.JSONDecodeError, KeyError, TypeError):` (internal linking JSON parse)
- **`_run_content_planner()`** helper added after `_ensure_catalog_outline()` in `jobs.py`; wired into `content_generation_job()` after `_ensure_catalog_outline(seo_context)` call.

### Task 3: ContentCreatorAgent prompt injection (commit 842e8b7)
- **New params** on `_build_synchronized_prompt()`: `article_content_type: Optional[str] = None`, `planned_outline: Optional[list] = None`
- **`_get_content_type_guidance()`** helper: looks up template in `CONTENT_TYPE_TEMPLATES`, injects `## CONTENT TYPE: X` block with opening/closing instructions; returns `""` for `general` or invalid types (no noise for unclassified articles).
- **Article structure block** replaced: `planned_outline` non-empty → type-specific sections with `writing_notes`; `planned_outline` empty → existing `ContentOutline` fallback (backward compatible).
- **`_create_article()`** extracts `article_content_type` and `planned_outline` from task dict, passes to prompt builder.

---

## Files Changed

| File | Change |
|------|--------|
| `src/models/seo_context.py` | +ArticleContentType enum, +3 Optional fields, updated to_content_creator_task() |
| `src/services/content/content_type_templates.py` | New — 6 ContentTypeTemplate definitions |
| `src/services/content/content_planner.py` | New — ContentPlannerService |
| `src/scheduler/jobs.py` | +_run_content_planner() helper, wire call, fix 4 bare except: clauses |
| `src/agents/content_creator.py` | +_get_content_type_guidance(), updated _build_synchronized_prompt() |
| `tests/unit/content/test_content_planner.py` | New — 12 unit tests (3 test classes) |

---

## Verification Results

```
# All 12 unit tests pass
pytest tests/unit/content/test_content_planner.py -v
→ 12 passed

# No bare except: remaining
python -c "...check content..." → OK: no bare except: found

# All 6 templates present
python -c "...check templates..." → OK: all 6 content type templates present

# Pipeline wiring confirmed
python -c "...check jobs.py..." → OK: _run_content_planner wired into jobs.py

# No regressions in existing tests
pytest tests/unit/ tests/services/content/ -v --tb=short
→ 77 passed (4 failed + 9 errors are PRE-EXISTING in test_research_cache + test_value_scorer, confirmed by git stash verification)
```

---

## Deviations from Plan

### Auto-applied: Explicit encoding on jobs.py open

The verification script from the plan used `open('src/scheduler/jobs.py')` which failed with `UnicodeDecodeError: 'gbk'` on Windows. Added `encoding='utf-8'` to the verification call. No code changes needed — the jobs.py file itself is correctly UTF-8; this was only a verification script issue.

No other deviations — plan executed exactly as written.

---

## Known Stubs

None. All implemented functionality is fully wired:
- `ArticleContentType` → real enum, not a string constant
- `CONTENT_TYPE_TEMPLATES` → fully populated for all 6 types
- `ContentPlannerService.plan()` → real LLM call (mocked in tests)
- `_run_content_planner()` → live call in jobs.py
- `_get_content_type_guidance()` → real template lookup

---

## Self-Check

### Files Created/Modified

- [x] `src/models/seo_context.py` — FOUND (ArticleContentType enum visible)
- [x] `src/services/content/content_type_templates.py` — FOUND (new file)
- [x] `src/services/content/content_planner.py` — FOUND (new file)
- [x] `src/scheduler/jobs.py` — FOUND (_run_content_planner present)
- [x] `src/agents/content_creator.py` — FOUND (new params + method)
- [x] `tests/unit/content/test_content_planner.py` — FOUND (12 tests)

### Commits

- [x] d92579f — feat(260403-quq-01): add ArticleContentType enum, SEOContext fields, and content type templates
- [x] 879f1cf — feat(260403-quq-01): add ContentPlannerService and wire into jobs.py pipeline
- [x] 842e8b7 — feat(260403-quq-01): extend ContentCreatorAgent to inject content type guidance and planned outline

## Self-Check: PASSED
