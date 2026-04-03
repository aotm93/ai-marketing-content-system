---
phase: 260403-quq-content-type-planning
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/models/seo_context.py
  - src/services/content/content_type_templates.py
  - src/services/content/content_planner.py
  - src/scheduler/jobs.py
  - src/agents/content_creator.py
  - tests/unit/content/test_content_planner.py
autonomous: true
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

must_haves:
  truths:
    - "ContentPlannerService.plan() classifies any title into ArticleContentType + confidence without raising"
    - "All 5 content types + general fallback have ContentTypeTemplate dataclasses with ordered SectionTemplate lists"
    - "confidence < 0.75 or LLM failure produces ArticleContentType.GENERAL silently"
    - "SEOContext accepts article_content_type, article_content_type_confidence, planned_outline as Optional fields — existing callers raise no ValidationError"
    - "ContentCreatorAgent._build_synchronized_prompt() injects content type opening/closing instructions and planned_outline sections when present"
    - "content_generation_job() calls _run_content_planner() after _ensure_catalog_outline(), wrapped in non-fatal try/except"
    - "Bare except: clauses in jobs.py are replaced with specific exception types"
    - "Unit tests pass: correct type returned, fallback triggered on low-confidence, LLM error handled, all 6 templates non-empty"
  artifacts:
    - path: "src/models/seo_context.py"
      provides: "ArticleContentType enum + 3 new Optional SEOContext fields"
      contains: "class ArticleContentType"
    - path: "src/services/content/content_type_templates.py"
      provides: "CONTENT_TYPE_TEMPLATES dict mapping all 6 ArticleContentType values to ContentTypeTemplate"
      exports: ["CONTENT_TYPE_TEMPLATES", "ContentTypeTemplate", "SectionTemplate"]
    - path: "src/services/content/content_planner.py"
      provides: "ContentPlannerService with async plan() method"
      exports: ["ContentPlannerService", "PlannerLLMOutput"]
    - path: "tests/unit/content/test_content_planner.py"
      provides: "Unit tests for classifier and templates"
  key_links:
    - from: "src/scheduler/jobs.py (_run_content_planner)"
      to: "src/services/content/content_planner.py (ContentPlannerService.plan)"
      via: "await planner.plan(seo_context)"
      pattern: "_run_content_planner"
    - from: "src/models/seo_context.py (to_content_creator_task)"
      to: "src/agents/content_creator.py (_build_synchronized_prompt)"
      via: "task dict keys article_content_type, planned_outline"
      pattern: "article_content_type"
---

<objective>
Implement content type classification and intent-matched article structure end-to-end across Phase 1 (infrastructure) and Phase 2 (pipeline integration).

Purpose: Every article produced by the autopilot currently receives a generic H2 skeleton regardless of title intent. This plan builds the ContentPlannerService, ArticleContentType enum, 5-type template library, and wires everything into the live pipeline — so each article gets type-specific section structure and prose instructions from title to published post.

Output:
- `ArticleContentType` enum + 3 backward-compatible Optional fields on SEOContext
- `content_type_templates.py` — 6 ContentTypeTemplate dataclasses (how-to, listicle, comparison, review, pricing, general)
- `ContentPlannerService` — single JSON-mode LLM call, classifies + outlines, non-raising
- `_run_content_planner()` wired into `jobs.py` between `_ensure_catalog_outline()` and `ContentCreatorAgent.execute()`
- `ContentCreatorAgent._build_synchronized_prompt()` extended to inject type guidance and planned sections
- Bare `except:` in `jobs.py` replaced with specific exception types (ROBUST-01 prerequisite)
- Unit tests covering classifier fallback, template completeness, SEOContext backward compatibility
</objective>

<execution_context>
@$HOME/.config/opencode/get-shit-done/workflows/execute-plan.md
@$HOME/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260403-quq-content-type-planning/260403-quq-PLAN.md
@.planning/REQUIREMENTS.md
@.planning/research/ARCHITECTURE.md

<!-- Key interfaces the executor needs — extracted from codebase -->
<interfaces>
<!-- From src/models/seo_context.py — current SEOContext structure (relevant excerpt) -->
```python
# Existing SEOContext fields (do NOT modify or remove any of these)
class SEOContext(BaseModel):
    source: str
    target_keyword: str
    topic_title: str
    selected_title: Optional[str] = None
    page_type: str = "category_support"
    primary_taxonomy_name: Optional[str] = None
    primary_taxonomy_type: Optional[str] = None
    outline: Optional[ContentOutline] = None  # ← DO NOT overwrite this
    # ... all other existing fields unchanged

    def to_content_creator_task(self) -> Dict[str, Any]:
        # Returns a dict with: type, keyword, seo_context, title_must_use,
        # outline, research_context, page_type, category_context, tag_context,
        # primary_catalog_context, decision_questions, commercial_facts,
        # semantic_keywords, internal_links, products, supporting_tags
        # ADD: article_content_type, planned_outline (new keys)
```

<!-- From src/agents/content_creator.py — prompt building signature -->
```python
def _build_synchronized_prompt(
    self,
    keyword: str,
    title_must_use: str,
    hook_type: Optional[str],
    products: list,
    research_context: dict,
    outline: dict,       # ← existing ContentOutline fallback
    page_type: str,
    category_context: dict,
    tag_context: dict,
    primary_catalog_context: dict,
    decision_questions: List[str],
    commercial_facts: List[str],
    supporting_tags: List[str],
    semantic_keywords: List[str],
    internal_links: List[dict]
) -> str:
# ADD two new parameters: article_content_type: Optional[str] = None, planned_outline: Optional[list] = None
# Inject content type guidance AFTER the EDITORIAL BLUEPRINT block (before ## RESEARCH DATA)
# Inject planned_outline sections in ## ARTICLE STRUCTURE block INSTEAD OF outline when planned_outline is non-empty
```

<!-- From src/scheduler/jobs.py — exact insertion point (lines ~1652–1663) -->
```python
# CURRENT FLOW:
if seo_context:
    logger.info(...)
    logger.info(...)
    _ensure_catalog_outline(seo_context)       # ← INSERT AFTER THIS LINE
    creator_task = seo_context.to_content_creator_task()
    content_result = await content_agent.execute(creator_task)

# TARGET FLOW:
if seo_context:
    logger.info(...)
    logger.info(...)
    _ensure_catalog_outline(seo_context)
    await _run_content_planner(seo_context, ai_provider)   # NEW — non-fatal
    creator_task = seo_context.to_content_creator_task()
    content_result = await content_agent.execute(creator_task)
```

<!-- From src/core/ai_provider.py — generate_text signature -->
```python
async def generate_text(self, prompt: str, max_tokens: int = 2000, **kwargs) -> str:
    # kwargs are forwarded to chat.completions.create()
    # response_format={"type": "json_object"} passes through via **kwargs — no provider changes needed
```

<!-- Bare except: locations to fix (ROBUST-01) — from jobs.py grep -->
# Line 1574: except: pass  → except Exception: pass
# Line 1861: except: meta_data = {...}  → except (json.JSONDecodeError, KeyError, ValueError): meta_data = {...}
# Line 2075: except: logger.warning(...)  → except (json.JSONDecodeError, KeyError): logger.warning(...)
# Line 2438: except: logger.warning(...)  → except (json.JSONDecodeError, KeyError, TypeError): logger.warning(...)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Infrastructure — ArticleContentType enum, SEOContext fields, and content_type_templates.py</name>
  <files>
    src/models/seo_context.py
    src/services/content/content_type_templates.py
    tests/unit/content/test_content_planner.py
  </files>
  <behavior>
    - Test 1: SEOContext constructed with only pre-existing required fields (source, target_keyword, topic_title) raises no ValidationError — backward compatibility guaranteed
    - Test 2: SEOContext accepts article_content_type=ArticleContentType.HOW_TO, article_content_type_confidence=0.9, planned_outline=[{"title":"Step 1"}] without error
    - Test 3: CONTENT_TYPE_TEMPLATES[ArticleContentType.HOW_TO].sections is non-empty and each section has name, section_type, writing_mode set
    - Test 4: All 6 ArticleContentType values (HOW_TO, LISTICLE, COMPARISON, REVIEW, PRICING, GENERAL) exist as keys in CONTENT_TYPE_TEMPLATES
    - Test 5: Each ContentTypeTemplate has non-empty opening_instruction, closing_instruction, and at least 3 sections
  </behavior>
  <action>
**Step 1 — Write the failing tests first** in `tests/unit/content/test_content_planner.py`:

```python
"""Unit tests for ContentPlannerService and content type templates."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.models.seo_context import ArticleContentType, SEOContext
from src.services.content.content_type_templates import CONTENT_TYPE_TEMPLATES, ContentTypeTemplate, SectionTemplate


class TestSEOContextBackwardCompat:
    def test_existing_fields_only_no_validation_error(self):
        ctx = SEOContext(source="GSC", target_keyword="packaging solutions", topic_title="Packaging Guide")
        assert ctx.article_content_type is None
        assert ctx.article_content_type_confidence is None
        assert ctx.planned_outline == []

    def test_new_fields_accepted(self):
        ctx = SEOContext(
            source="GSC", target_keyword="kw", topic_title="T",
            article_content_type=ArticleContentType.HOW_TO,
            article_content_type_confidence=0.9,
            planned_outline=[{"title": "Step 1", "section_type": "step"}]
        )
        assert ctx.article_content_type == ArticleContentType.HOW_TO
        assert ctx.article_content_type_confidence == 0.9
        assert len(ctx.planned_outline) == 1


class TestContentTypeTemplates:
    def test_all_types_present(self):
        for ct in ArticleContentType:
            assert ct in CONTENT_TYPE_TEMPLATES, f"Missing template for {ct}"

    def test_each_template_non_empty(self):
        for ct, tmpl in CONTENT_TYPE_TEMPLATES.items():
            assert tmpl.opening_instruction, f"{ct} opening_instruction is empty"
            assert tmpl.closing_instruction, f"{ct} closing_instruction is empty"
            assert len(tmpl.sections) >= 3, f"{ct} has fewer than 3 sections"

    def test_each_section_has_writing_mode(self):
        for ct, tmpl in CONTENT_TYPE_TEMPLATES.items():
            for section in tmpl.sections:
                assert section.writing_mode, f"{ct} section '{section.name}' missing writing_mode"
                assert section.section_type, f"{ct} section '{section.name}' missing section_type"
```

**Step 2 — Run tests (expect RED):**
```
pytest tests/unit/content/test_content_planner.py -x -q 2>&1
```

**Step 3 — Implement to make tests GREEN:**

**`src/models/seo_context.py`** — Add `ArticleContentType` enum and 3 new Optional fields:

Add this enum class BEFORE the `InternalLinkOpportunity` class (it must be defined before SEOContext imports it):

```python
class ArticleContentType(str, Enum):
    """
    SEO article content type — classifies title intent for structure selection.
    Named ArticleContentType to avoid collision with existing ContentType in content_intelligence.py.
    Use str mixin to ensure .value serializes cleanly in JSON and task dicts.
    """
    HOW_TO = "how_to"
    LISTICLE = "listicle"
    COMPARISON = "comparison"
    REVIEW = "review"
    PRICING = "pricing"
    GENERAL = "general"  # fallback for unclassified / low-confidence titles
```

Add to `SEOContext` model at the end of the field declarations (before `class Config`), after the `# ========== Performance Tracking ==========` block:

```python
    # ========== Content Planning (NEW — all Optional, backward-compatible) ==========
    article_content_type: Optional[ArticleContentType] = Field(
        None,
        description="LLM-classified article format. Set by ContentPlannerService before ContentCreatorAgent."
    )
    article_content_type_confidence: Optional[float] = Field(
        None,
        description="0–1 confidence score from the classifier LLM call."
    )
    planned_outline: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Ordered list of section dicts: {title, section_type, key_points, writing_notes}. "
            "Generated by ContentPlannerService and consumed by ContentCreatorAgent via to_content_creator_task()."
        )
    )
```

Also add `article_content_type` and `planned_outline` to `to_content_creator_task()` return dict:

```python
            "article_content_type": self.article_content_type.value if self.article_content_type else "general",
            "planned_outline": self.planned_outline or [],
```

**`src/services/content/content_type_templates.py`** — New file. Copy the exact full `CONTENT_TYPE_TEMPLATES` dict from `.planning/research/ARCHITECTURE.md` section 4 (lines 200–328). This is the authoritative template definition — do not simplify or abbreviate the section templates. The dataclasses are:

```python
from dataclasses import dataclass, field
from typing import List
from src.models.seo_context import ArticleContentType


@dataclass
class SectionTemplate:
    name: str          # H2 title template (may include {keyword} placeholder)
    section_type: str  # "step" | "comparison" | "list_item" | "verdict" | "faq" | "cta" | "prerequisites" | etc.
    writing_mode: str  # Instruction injected into ContentCreatorAgent writing prompt
    estimated_words: int = 350


@dataclass
class ContentTypeTemplate:
    content_type: ArticleContentType
    opening_instruction: str   # How to open the article
    sections: List[SectionTemplate]  # Ordered H2 skeleton
    closing_instruction: str   # How to close / what CTA type


CONTENT_TYPE_TEMPLATES: dict[ArticleContentType, ContentTypeTemplate] = { ... }  # full dict from ARCHITECTURE.md
```

**Step 4 — Run tests (expect GREEN):**
```
pytest tests/unit/content/test_content_planner.py::TestSEOContextBackwardCompat tests/unit/content/test_content_planner.py::TestContentTypeTemplates -v 2>&1
```
  </action>
  <verify>
    <automated>pytest tests/unit/content/test_content_planner.py::TestSEOContextBackwardCompat tests/unit/content/test_content_planner.py::TestContentTypeTemplates -v 2>&1</automated>
  </verify>
  <done>
    - ArticleContentType enum with 6 values exists in src/models/seo_context.py
    - SEOContext has 3 new Optional fields (article_content_type, article_content_type_confidence, planned_outline=[])
    - to_content_creator_task() includes "article_content_type" and "planned_outline" keys
    - CONTENT_TYPE_TEMPLATES dict covers all 6 ArticleContentType values with ≥3 sections each
    - All tests in TestSEOContextBackwardCompat and TestContentTypeTemplates pass
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: ContentPlannerService + jobs.py wiring (ROBUST-01 + PIPE-02)</name>
  <files>
    src/services/content/content_planner.py
    src/scheduler/jobs.py
    tests/unit/content/test_content_planner.py
  </files>
  <behavior>
    - Test 6: ContentPlannerService.plan() with mocked LLM returning valid JSON → seo_context.article_content_type = HOW_TO, confidence = 0.9, planned_outline has entries
    - Test 7: ContentPlannerService.plan() with LLM returning confidence=0.6 (below 0.75 threshold) → seo_context.article_content_type = ArticleContentType.GENERAL
    - Test 8: ContentPlannerService.plan() with LLM raising an exception → no exception re-raised, seo_context.article_content_type remains None (graceful degradation)
    - Test 9: ContentPlannerService.plan() with LLM returning malformed JSON → no exception re-raised, seo_context unchanged
  </behavior>
  <action>
**Step 1 — Append failing tests** to `tests/unit/content/test_content_planner.py`:

```python
class TestContentPlannerService:
    def _make_seo_context(self):
        return SEOContext(source="GSC", target_keyword="hdpe bottle packaging", topic_title="HDPE Bottle Guide")

    @pytest.mark.asyncio
    async def test_successful_classification(self):
        from src.services.content.content_planner import ContentPlannerService
        mock_provider = AsyncMock()
        mock_provider.generate_text = AsyncMock(return_value='{"content_type": "how_to", "confidence": 0.9, "outline": [{"title": "Step 1", "section_type": "step", "key_points": ["point"], "writing_notes": "note"}]}')
        svc = ContentPlannerService(mock_provider)
        ctx = self._make_seo_context()
        await svc.plan(ctx)
        from src.models.seo_context import ArticleContentType
        assert ctx.article_content_type == ArticleContentType.HOW_TO
        assert ctx.article_content_type_confidence == 0.9
        assert len(ctx.planned_outline) == 1

    @pytest.mark.asyncio
    async def test_low_confidence_falls_back_to_general(self):
        from src.services.content.content_planner import ContentPlannerService
        from src.models.seo_context import ArticleContentType
        mock_provider = AsyncMock()
        mock_provider.generate_text = AsyncMock(return_value='{"content_type": "review", "confidence": 0.6, "outline": []}')
        svc = ContentPlannerService(mock_provider)
        ctx = self._make_seo_context()
        await svc.plan(ctx)
        assert ctx.article_content_type == ArticleContentType.GENERAL

    @pytest.mark.asyncio
    async def test_llm_exception_does_not_raise(self):
        from src.services.content.content_planner import ContentPlannerService
        mock_provider = AsyncMock()
        mock_provider.generate_text = AsyncMock(side_effect=RuntimeError("API timeout"))
        svc = ContentPlannerService(mock_provider)
        ctx = self._make_seo_context()
        await svc.plan(ctx)  # must not raise
        assert ctx.article_content_type is None

    @pytest.mark.asyncio
    async def test_malformed_json_does_not_raise(self):
        from src.services.content.content_planner import ContentPlannerService
        mock_provider = AsyncMock()
        mock_provider.generate_text = AsyncMock(return_value="not valid json {{{{")
        svc = ContentPlannerService(mock_provider)
        ctx = self._make_seo_context()
        await svc.plan(ctx)  # must not raise
        assert ctx.article_content_type is None
```

**Step 2 — Run tests (expect RED):**
```
pytest tests/unit/content/test_content_planner.py::TestContentPlannerService -x -q 2>&1
```

**Step 3 — Create `src/services/content/content_planner.py`:**

Use the full implementation from `.planning/research/ARCHITECTURE.md` section 5 (lines 357–459). Key implementation points:

- `PlannerLLMOutput(BaseModel)` with `content_type: ArticleContentType`, `confidence: float`, `outline: list`
- `@field_validator("content_type", mode="before")` coerces invalid strings → `ArticleContentType.GENERAL`
- `CONFIDENCE_THRESHOLD = 0.75` — class-level constant; confidence below this → override `content_type` to `GENERAL` after Pydantic parsing
- `async def plan(self, seo_context: SEOContext) -> None` — enriches seo_context in-place:
  - Reads `selected_title or topic_title` and `target_keyword`
  - Calls `self.ai_provider.generate_text(prompt, temperature=0.2, max_tokens=900, response_format={"type": "json_object"})`
  - On `json.JSONDecodeError` or `ValidationError` or any other `Exception`: `logger.warning(...)` and return (do NOT re-raise)
  - On success: set `seo_context.article_content_type`, `.article_content_type_confidence`, `.planned_outline`
  - If `parsed.confidence < CONFIDENCE_THRESHOLD`: set `seo_context.article_content_type = ArticleContentType.GENERAL` and log fallback
- `_build_prompt()` using the pattern from ARCHITECTURE.md section 5 lines 438–458 — include SYSTEM_PROMPT + type_hints + title/keyword/page_type/catalog context

**Step 4 — Patch bare `except:` in `jobs.py` (ROBUST-01):**

Four locations identified via grep. Replace each bare `except:` with a specific exception type:

- **Line 1574** (keyword suggestion failure, context: `kw_client.get_keyword_suggestions`):
  ```python
  # OLD:
  except:
      pass
  # NEW:
  except Exception:
      pass
  ```

- **Line 1861** (meta JSON parse failure, context: `json.loads(clean_json)` for meta_data):
  ```python
  # OLD:
  except:
      meta_data = {"title": f"{target_keyword} Guide", "meta_description": "Read more...", "excerpt": ""}
  # NEW:
  except (json.JSONDecodeError, KeyError, ValueError):
      meta_data = {"title": f"{target_keyword} Guide", "meta_description": "Read more...", "excerpt": ""}
  ```

- **Line 2075** (SEO optimization JSON parse, context: `json.loads(seo_json_str)` for `optimized_seo`):
  ```python
  # OLD:
  except:
      logger.warning("Failed to parse AI SEO response, using fallback")
  # NEW:
  except (json.JSONDecodeError, KeyError):
      logger.warning("Failed to parse AI SEO response, using fallback")
  ```

- **Line 2438** (internal linking JSON parse, context: `json.loads(link_json_str)` for `links_to_add`):
  ```python
  # OLD:
  except:
      logger.warning("Failed to parse AI linking response")
      links_to_add = []
  # NEW:
  except (json.JSONDecodeError, KeyError, TypeError):
      logger.warning("Failed to parse AI linking response")
      links_to_add = []
  ```

**Step 5 — Wire `_run_content_planner()` into `jobs.py`:**

Add the helper function NEAR the existing `_ensure_catalog_outline()` function (around line 408) — place it immediately after `_ensure_catalog_outline`:

```python
async def _run_content_planner(seo_context, ai_provider) -> None:
    """Classify content type and generate tailored section outline. Non-fatal on failure."""
    try:
        from src.services.content.content_planner import ContentPlannerService
        planner = ContentPlannerService(ai_provider)
        await planner.plan(seo_context)
    except Exception as exc:
        logger.warning(f"ContentPlanner failed, using fallback outline: {exc}")
```

Then in `content_generation_job()`, at the `if seo_context:` block (line ~1657), insert the call after `_ensure_catalog_outline(seo_context)`:

```python
            _ensure_catalog_outline(seo_context)
            await _run_content_planner(seo_context, ai_provider)   # NEW: classify + outline (non-fatal)
            
            # Create task from SEOContext
            creator_task = seo_context.to_content_creator_task()
```

**Step 6 — Run all ContentPlanner tests (expect GREEN):**
```
pytest tests/unit/content/test_content_planner.py -v 2>&1
```
  </action>
  <verify>
    <automated>pytest tests/unit/content/test_content_planner.py -v 2>&1</automated>
  </verify>
  <done>
    - src/services/content/content_planner.py exists with ContentPlannerService and PlannerLLMOutput
    - confidence < 0.75 overrides type to GENERAL
    - LLM exceptions and JSON errors are caught silently, seo_context left at None defaults
    - All 4 bare except: in jobs.py replaced with specific exception types
    - _run_content_planner() helper defined and called after _ensure_catalog_outline() in jobs.py
    - All 9 unit tests (Tasks 1+2) pass
  </done>
</task>

<task type="auto">
  <name>Task 3: ContentCreatorAgent prompt injection (PIPE-03) + regression guard</name>
  <files>
    src/agents/content_creator.py
    tests/unit/content/test_content_planner.py
  </files>
  <action>
**Purpose:** ContentCreatorAgent._build_synchronized_prompt() must inject content type guidance when `article_content_type` is present in the task dict, and use `planned_outline` sections instead of the `outline` (ContentOutline) block when non-empty.

**Step 1 — Update `_create_article()` to extract new task keys:**

After the existing `page_type = task.get(...)` line (line ~86 in content_creator.py), add:

```python
        article_content_type = task.get("article_content_type", "general")
        planned_outline = task.get("planned_outline", [])
```

**Step 2 — Pass new params to `_build_synchronized_prompt()`:**

In the `_build_synchronized_prompt()` call (lines ~98–114), add at the end:

```python
            article_content_type=article_content_type,
            planned_outline=planned_outline,
```

**Step 3 — Add new parameters to `_build_synchronized_prompt()` signature:**

```python
    def _build_synchronized_prompt(
        self,
        keyword: str,
        title_must_use: str,
        hook_type: Optional[str],
        products: list,
        research_context: dict,
        outline: dict,
        page_type: str,
        category_context: dict,
        tag_context: dict,
        primary_catalog_context: dict,
        decision_questions: List[str],
        commercial_facts: List[str],
        supporting_tags: List[str],
        semantic_keywords: List[str],
        internal_links: List[dict],
        article_content_type: Optional[str] = None,    # NEW
        planned_outline: Optional[list] = None,         # NEW
    ) -> str:
```

**Step 4 — Inject content type guidance block in prompt:**

Add a `_get_content_type_guidance()` helper method to the class:

```python
    def _get_content_type_guidance(self, article_content_type: Optional[str]) -> str:
        """Build content-type-specific opening/closing guidance block for the prompt."""
        if not article_content_type or article_content_type == "general":
            return ""
        from src.services.content.content_type_templates import CONTENT_TYPE_TEMPLATES
        from src.models.seo_context import ArticleContentType
        try:
            ct = ArticleContentType(article_content_type)
        except ValueError:
            return ""
        template = CONTENT_TYPE_TEMPLATES.get(ct)
        if not template:
            return ""
        return (
            f"\n## CONTENT TYPE: {ct.value.upper()}\n"
            f"**Opening approach**: {template.opening_instruction}\n"
            f"**Closing approach**: {template.closing_instruction}\n"
            f"Follow the structural pattern for {ct.value} content — do not default to a generic blog post skeleton.\n"
        )
```

In `_build_synchronized_prompt()`, insert the content type guidance block immediately after the EDITORIAL BLUEPRINT section (after the line `- Do NOT fall back to one-size-fits-all article sequencing.\n`):

```python
        # Inject content type guidance (when planner ran successfully)
        content_type_guidance = self._get_content_type_guidance(article_content_type)
        if content_type_guidance:
            prompt += content_type_guidance
```

**Step 5 — Replace outline block with planned_outline when available:**

Find the `## ARTICLE STRUCTURE (Follow Closely)` block (lines ~339–361). Replace the entire `if outline:` block with logic that prefers `planned_outline` when non-empty:

```python
        # Use planned_outline (from ContentPlannerService) when available; fall back to ContentOutline
        if planned_outline:
            prompt += "\n## ARTICLE STRUCTURE (Follow Closely)\n"
            prompt += "**Sections** (type-specific — follow this order):\n"
            for i, section in enumerate(planned_outline, 1):
                section_title = section.get("title", f"Section {i}")
                section_type = section.get("section_type", "general")
                key_points = section.get("key_points", [])
                writing_notes = section.get("writing_notes", "")
                prompt += f"\n{i}. **{section_title}** ({section_type})\n"
                if writing_notes:
                    prompt += f"   Writer note: {writing_notes}\n"
                for point in key_points[:3]:
                    prompt += f"   - {point}\n"
        elif outline:
            # Fallback: use ContentOutline from ContentIntelligence (existing logic preserved)
            prompt += "\n## ARTICLE STRUCTURE (Follow Closely)\n"
            if outline.get('hook'):
                prompt += f"**Opening Hook**: {outline['hook']}\n\n"
            sections = outline.get('sections', [])
            if sections:
                prompt += "**Sections**:\n"
                for i, section in enumerate(sections, 1):
                    section_title = section.get('title', f'Section {i}')
                    content_type = section.get('content_type', 'general')
                    key_points = section.get('key_points', [])
                    prompt += f"\n{i}. **{section_title}** ({content_type})\n"
                    if key_points:
                        for point in key_points[:3]:
                            prompt += f"   - {point}\n"
            if outline.get('conclusion_type'):
                prompt += f"\n**Conclusion Type**: {outline['conclusion_type'].upper()}\n"
```

**Step 6 — Add regression tests to test_content_planner.py:**

```python
class TestContentCreatorAgentIntegration:
    """Verify ContentCreatorAgent consumes new SEOContext fields without error."""

    def test_build_synchronized_prompt_with_content_type(self):
        from src.agents.content_creator import ContentCreatorAgent
        agent = ContentCreatorAgent()
        prompt = agent._build_synchronized_prompt(
            keyword="hdpe bottles",
            title_must_use="How to Choose HDPE Bottles",
            hook_type=None,
            products=[],
            research_context={},
            outline={},
            page_type="category_support",
            category_context={},
            tag_context={},
            primary_catalog_context={},
            decision_questions=[],
            commercial_facts=[],
            supporting_tags=[],
            semantic_keywords=[],
            internal_links=[],
            article_content_type="how_to",
            planned_outline=[{"title": "Step 1: Assess Needs", "section_type": "step", "key_points": ["point"], "writing_notes": "numbered list"}],
        )
        assert "CONTENT TYPE: HOW_TO" in prompt
        assert "Step 1: Assess Needs" in prompt
        assert "numbered list" in prompt

    def test_build_synchronized_prompt_fallback_to_generic_outline(self):
        from src.agents.content_creator import ContentCreatorAgent
        agent = ContentCreatorAgent()
        prompt = agent._build_synchronized_prompt(
            keyword="packaging",
            title_must_use="Packaging Guide",
            hook_type=None,
            products=[],
            research_context={},
            outline={"hook": "The answer is here", "sections": [{"title": "Overview", "content_type": "general", "key_points": []}]},
            page_type="category_support",
            category_context={},
            tag_context={},
            primary_catalog_context={},
            decision_questions=[],
            commercial_facts=[],
            supporting_tags=[],
            semantic_keywords=[],
            internal_links=[],
            article_content_type=None,
            planned_outline=[],  # empty — should fall back to outline
        )
        assert "The answer is here" in prompt  # ContentOutline fallback used

    def test_to_content_creator_task_includes_new_fields(self):
        from src.models.seo_context import ArticleContentType, SEOContext
        ctx = SEOContext(
            source="GSC", target_keyword="kw", topic_title="T",
            article_content_type=ArticleContentType.PRICING,
            planned_outline=[{"title": "Price Range", "section_type": "price_range"}]
        )
        task = ctx.to_content_creator_task()
        assert task["article_content_type"] == "pricing"
        assert len(task["planned_outline"]) == 1
```

**Step 7 — Run full test suite:**
```
pytest tests/unit/content/test_content_planner.py -v 2>&1
```

**Step 8 — Run existing tests to confirm no regressions:**
```
pytest tests/unit/ tests/services/content/ -v --tb=short 2>&1
```
  </action>
  <verify>
    <automated>pytest tests/unit/content/test_content_planner.py tests/unit/ tests/services/content/ -v --tb=short 2>&1</automated>
  </verify>
  <done>
    - ContentCreatorAgent._build_synchronized_prompt() signature has article_content_type and planned_outline params (Optional, default None/[])
    - _get_content_type_guidance() injects "CONTENT TYPE: X" block and opening/closing instructions when type is non-general
    - planned_outline non-empty → uses planned sections block; planned_outline empty → falls back to ContentOutline (existing behavior preserved)
    - to_content_creator_task() returns article_content_type (str value) and planned_outline (list)
    - All 12 tests in test_content_planner.py pass (Tasks 1+2+3 combined)
    - All previously passing unit tests continue to pass (no regressions)
  </done>
</task>

</tasks>

<verification>
After all three tasks complete, verify the full implementation:

```bash
# 1. All new unit tests pass
pytest tests/unit/content/test_content_planner.py -v

# 2. No regressions in existing unit tests
pytest tests/unit/ tests/services/content/ -v --tb=short

# 3. Confirm bare except: eliminated from jobs.py
python -c "
import ast, sys
with open('src/scheduler/jobs.py') as f:
    content = f.read()
if 'except:\n' in content:
    print('FAIL: bare except: still present in jobs.py')
    sys.exit(1)
else:
    print('OK: no bare except: found')
"

# 4. Confirm all 6 content types present
python -c "
from src.services.content.content_type_templates import CONTENT_TYPE_TEMPLATES
from src.models.seo_context import ArticleContentType
missing = [ct for ct in ArticleContentType if ct not in CONTENT_TYPE_TEMPLATES]
assert not missing, f'Missing templates: {missing}'
print(f'OK: all {len(CONTENT_TYPE_TEMPLATES)} content type templates present')
"

# 5. Confirm ContentPlannerService is wired in jobs.py
python -c "
with open('src/scheduler/jobs.py') as f:
    content = f.read()
assert '_run_content_planner' in content, 'Missing _run_content_planner in jobs.py'
assert 'await _run_content_planner' in content, 'Missing await call in jobs.py'
print('OK: _run_content_planner wired into jobs.py')
"
```
</verification>

<success_criteria>
1. **ROBUST-01**: Zero bare `except:` clauses remain in `jobs.py`; all 4 locations use specific exception types
2. **CLASS-01/02**: `ContentPlannerService.plan()` classifies titles via JSON-mode LLM; confidence < 0.75 → GENERAL fallback (unit-tested with mocked LLM)
3. **TMPL-01/02/03**: All 6 `ArticleContentType` values mapped to `ContentTypeTemplate` with ≥3 ordered `SectionTemplate` entries each containing non-empty `writing_mode`
4. **PIPE-01**: `SEOContext` carries 3 new Optional fields; constructing with only pre-existing required fields raises no `ValidationError`
5. **PIPE-02**: `_run_content_planner()` is defined and called in `jobs.py` after `_ensure_catalog_outline()`, wrapped in non-fatal `try/except`
6. **PIPE-03**: `ContentCreatorAgent._build_synchronized_prompt()` injects content type guidance and uses `planned_outline` when non-empty, falls back to `outline` when not
7. All 12+ tests in `tests/unit/content/test_content_planner.py` pass
8. All previously passing tests in `tests/unit/` and `tests/services/content/` continue to pass
</success_criteria>

<output>
After completion, create `.planning/quick/260403-quq-content-type-planning/260403-quq-SUMMARY.md` with:
- What was implemented
- Files changed and key decisions made
- Any deviations from this plan and why
- Verification results
</output>
