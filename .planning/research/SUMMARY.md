# Project Research Summary

**Project:** BoboPkg SEO Content Generation Improvement
**Domain:** AI-driven content type classification + intent-specific article structure generation
**Researched:** 2026-04-03
**Confidence:** HIGH (ARCHITECTURE + FEATURES + PITFALLS all grounded in direct codebase inspection and verified SEO canon; STACK.md not produced — stack constraints extracted from ARCHITECTURE.md)

---

## Executive Summary

BoboPkg currently generates every article with the same generic H2 skeleton regardless of what the title signals — a how-to guide, a product listicle, and a pricing comparison all get the same structure. This is a primary ranking failure mode: Google's systems evaluate content type before returning results, and mismatched structure is well-documented in Ahrefs/Semrush SEO research as a top reason quality content underperforms. The fix is an LLM-based content planning step that (a) classifies the article title into one of five types, (b) selects a type-specific section template, and (c) injects structured prose instructions into the writer's prompt.

The recommended approach is a single new `ContentPlannerService` inserted between `_ensure_catalog_outline()` and `ContentCreatorAgent.execute()` in `jobs.py`. It makes one JSON-mode LLM call to classify and outline simultaneously, enriches `SEOContext` in-place with three new Optional fields (`article_content_type`, `article_content_type_confidence`, `planned_outline`), and fails non-fatally — the existing catalog outline fallback continues to function if the planner errors. This is a low-disruption, high-leverage integration requiring changes to only five files with no database migrations.

The primary risks are LLM classification confidence failures (wrong type returned with spurious confidence), template bleed (LLM reverts to generic structure despite per-type prompts), and silent pipeline regressions caused by existing bare `except:` clauses in `jobs.py`. All three are mitigable with structured JSON output mode, explicit H2 skeletons in prompts, and patching the error-swallowing exception handlers before deploying. Build the fallback and validation logic on day one — do not defer.

---

## Key Findings

### Recommended Stack

*Note: STACK.md was not produced. Stack constraints were extracted from ARCHITECTURE.md's direct codebase analysis.*

The existing stack is fully sufficient for this feature — no new dependencies are required. All LLM calls use `OpenAICompatibleProvider` (raw OpenAI SDK 1.10.0) via `AIProviderInterface.generate_text()`. JSON mode (`response_format={"type": "json_object"}`) is supported natively and passes through the existing `**kwargs` forwarding — zero changes to the AI provider layer. Despite `langchain==0.1.4` being installed, LangChain is not used anywhere in the content generation path and must not be introduced here.

**Core technologies (as-is stack):**
- **OpenAI SDK 1.10.0** — structured LLM output via JSON mode; already in place
- **Pydantic v2 (2.5.3)** — `PlannerLLMOutput` validation model; `str` Enum for `ArticleContentType`
- **Python dataclasses** — `ContentTypeTemplate` / `SectionTemplate` in new `content_type_templates.py`; type-safe, IDE-navigable, no file I/O
- **Jinja2 3.1.3** — already in stack but explicitly NOT the right tool here; prompt-building is pure Python strings consistent with existing `_build_synchronized_prompt()` pattern

### Expected Features

**Must have (table stakes) — build in Phase 1:**
- LLM title classification into 6 types (5 + `general` fallback) with confidence score
- Type-specific H2/H3 section templates for: how-to, listicle, comparison, review, pricing
- `SEOContext` enrichment with `article_content_type`, `article_content_type_confidence`, `planned_outline`
- Type-aware prose instructions injected into `ContentCreatorAgent._build_synchronized_prompt()`
- `confidence < 0.75` fallback to `general` type with logged flag

**Should have (differentiators) — build in Phase 2:**
- `secondary_type` field for hybrid intent handling ("Best X Review" = listicle + review)
- Content angle detection from title (e.g., "for beginners", "2026 updated", "budget")
- Per-type optimal article length guidance injected as `suggested_length` hint
- FAQ section injection for how-to, pricing, and review types
- Quality gate extension: type-aware structural validation (keyword in H2s, table presence, verdict position)

**Defer to v2+:**
- SERP research / competitor analysis before classification (adds latency + API cost; title-only is ~85–90% accurate)
- Schema markup generation (HowTo, Review, ItemList schema; separate concern from content structure)
- Custom/user-configurable content types (admin UI burden; 5 types + generic covers dominant formats)
- A/B testing content structures (requires GSC feedback loop; not a content generation concern)
- Multi-language classification (English-only for v1; locale flag deferred)

### Architecture Approach

The integration is a surgical insertion into `jobs.py` with a new service class and data module — no new agents, no new API services, no database migrations. The `ContentPlannerService` is called via a thin `_run_content_planner()` wrapper (try/except, non-fatal) between `_ensure_catalog_outline()` and `ContentCreatorAgent.execute()`. It enriches `SEOContext` in-place; the creator agent reads new fields from the task dict via `to_content_creator_task()`.

**Major components:**

1. **`ArticleContentType` enum** (`src/models/seo_context.py`) — 5 types + `general`; `str` Enum to prevent serialization bugs
2. **`content_type_templates.py`** (`src/services/content/`) — Python dataclasses mapping each type to an ordered `SectionTemplate` list with `opening_instruction`, `writing_mode` per section, `closing_instruction`
3. **`ContentPlannerService`** (`src/services/content/content_planner.py`) — single JSON-mode LLM call; validates output via `PlannerLLMOutput(BaseModel)`; enriches `SEOContext` in-place; non-raising
4. **`_run_content_planner()` hook** (`src/scheduler/jobs.py`, ~line 1657) — one-line insertion; wraps service call in try/except
5. **`ContentCreatorAgent` extension** (`src/agents/content_creator.py`) — `_get_content_type_guidance()` reads `article_content_type` and `planned_outline` from task dict; falls back gracefully when empty

**Build order with dependencies:**
```
Task 1: ArticleContentType enum + SEOContext new fields (Optional, safe defaults)
     ↓
Task 2: content_type_templates.py (pure data, no pipeline coupling)
     ↓
Task 3: ContentPlannerService (unit-testable in isolation with mocked LLM)
     ↓
Task 4: Wire _run_content_planner() into jobs.py  ← integration risk gate
     ↓
Task 5: ContentCreatorAgent: consume article_content_type + planned_outline
     ↓
Task 6: SEOContext.to_content_creator_task() — add new fields to output dict
     ↓
Task 7: Tests (unit + pipeline integration)
```

Tasks 1–3 can be built and tested without touching the live pipeline.

### Critical Pitfalls

**Top 5 — address during implementation, not after:**

1. **LLM hallucinating a confident wrong type (C1)** — Use JSON mode + `PlannerLLMOutput` Pydantic validation to enforce enum outputs; include 2–3 few-shot disambiguation examples (listicle vs. comparison vs. review are the most confusable); `confidence < 0.75` → fall back to `general`. Pass `target_keyword`, `semantic_keywords`, and `page_type` to the prompt — not just the title.

2. **Template bleed to generic structure (C2)** — Put the explicit H2 skeleton in the prompt, not just style instructions. The planner produces a concrete `section_outline` list before writing begins; the writer fills it in rather than generating structure. Structural constraints in the first 200 tokens of the prompt. Validate outline shape before passing to writer.

3. **`SEOContext` schema drift breaking the existing pipeline (C4)** — All new fields MUST use `Optional[...] = None` or `Field(default_factory=list)`. Write a regression test that constructs `SEOContext` with only pre-existing fields and asserts no `ValidationError`. **Prerequisite: fix the bare `except:` clauses in `jobs.py`** (flagged HIGH severity in CONCERNS.md) before deploying new fields — silent exception swallowing will mask schema failures for days.

4. **Ambiguous title with no recovery path (C3)** — Detect at classification time: `confidence < 0.8` OR dual-type title signals → flag as `mixed_intent`, add `secondary_type: Optional[ArticleContentType]` to SEOContext. Route to a blended template for known hybrid patterns (pricing+comparison, listicle+review).

5. **LLM outline ignoring target keyword (C5)** — Require keyword anchoring in the outline prompt: "At least 2 H2 headings MUST contain the target keyword or a direct semantic variant." Add a programmatic check post-outline-generation before passing to writer; regenerate once if check fails.

---

## Implications for Roadmap

### Phase 1: Core Classification + Template Infrastructure
**Rationale:** Tasks 1–3 are fully decoupled from the live pipeline and can be built/tested in isolation. Establishes the data model and service contract before any integration risk.
**Delivers:** `ArticleContentType` enum, 5-type `ContentTypeTemplate` dataclasses, `ContentPlannerService` with unit tests. Nothing in production yet.
**Addresses:** Table stakes features — content type classification, type-specific section structures, prose instructions (all HIGH confidence)
**Avoids:** C4 (schema drift) — new SEOContext fields done right with Optional defaults from the start; N1 (enum serialization) — `str` Enum pattern applied immediately

### Phase 2: Pipeline Integration + Writer Consumption
**Rationale:** Integration risk gate (`_run_content_planner()` wiring into jobs.py) deserves its own phase after the service is proven. Prerequisite: bare `except:` patches in `jobs.py` must land first.
**Delivers:** End-to-end flow: title → classification → outline → ContentCreatorAgent receiving type-specific guidance in every production article
**Addresses:** SEOContext enrichment (article_content_type, planned_outline), to_content_creator_task() extension, ContentCreatorAgent _build_synchronized_prompt() update
**Avoids:** C4 (silent schema failures masked by bare except), N4 (legacy fallback masking classification failures — add `classification_used: bool` metric)

### Phase 3: Robustness + Validation
**Rationale:** First two phases get structure into production. This phase ensures the output is *correct* structure, not just any structure.
**Delivers:** Outline validation (keyword anchoring check, per-type section count bounds), `confidence < 0.75` fallback chain, `secondary_type` field for hybrid intent, blueprint selection gated on content type (M1 fix)
**Addresses:** Differentiators — confidence-based fallback chain, hybrid intent handling, per-type article length guidance
**Avoids:** C1 (overconfident wrong classification), C2 (template bleed), C3 (ambiguous title no recovery), M1 (B2B vocabulary bleed into non-B2B types), M2 (section depth inconsistency)

### Phase 4: Quality Gate Extension + FAQ Injection (v1.5)
**Rationale:** After the pipeline is stable, extend quality assurance to validate type-specific structural requirements. FAQ injection is low complexity but depends on the classification system being reliable.
**Delivers:** Quality gate type-aware structural checks (comparison has table, review has verdict in first 200 words, pricing has table in first half, how-to has numbered H2 steps), FAQ section auto-injection for how-to/pricing/review types
**Addresses:** Differentiators — type-specific FAQ injection, SERP feature targeting groundwork
**Avoids:** M4 (correct type, wrong structural details that still hurt rankings), N3 (duplicate-type article similarity — test before deploying)

### Phase Ordering Rationale

- **Infrastructure before integration** (Phase 1 → Phase 2): de-risks the pipeline insertion by validating service logic independently
- **Integration before validation** (Phase 2 → Phase 3): need real production output to tune thresholds and identify real failure modes
- **Bare except fix is a prerequisite for Phase 2, not part of it**: this is blocking technical debt that must be resolved first; it's a small change but the entire new feature's observability depends on it
- **Quality gate extension deferred** (Phase 4): don't block production value on optional enhancements; let ranking data accumulate first

### Research Flags

Phases with sufficient documentation (standard patterns, skip research-phase):
- **Phase 1:** Pure service/data layer — Python dataclasses, Pydantic models, JSON-mode LLM call. All patterns are established in existing codebase.
- **Phase 2:** One-line `jobs.py` insertion + agent prompt extension. Patterns are well-documented in ARCHITECTURE.md.

Phases that may benefit from deeper research during planning:
- **Phase 3 — Hybrid intent template merging:** The secondary_type merging logic (how to combine a listicle outer structure with review inner-item format) has no prior art in the codebase. Needs design work during planning.
- **Phase 3 — Blueprint selection refactor:** `_select_editorial_blueprint()` currently uses keyword/hook signals. Adding content type as a gating signal requires understanding the blueprint decision tree — review `content_creator.py` during planning.
- **Phase 4 — Quality gate structural checks:** `quality_gate.py` architecture needs review to understand how to add type-aware validation rules without coupling the gate to SEOContext internals.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Extracted from direct codebase inspection in ARCHITECTURE.md; all SDK/library constraints verified. STACK.md not produced but gap fully covered. |
| Features | HIGH | Core SEO canon cross-verified via Ahrefs, Semrush, Backlinko. Per-type structural conventions are industry-standard, not inferred. |
| Architecture | HIGH | Based on direct codebase inspection of all relevant files with line numbers. Integration point is unambiguous. |
| Pitfalls | HIGH | Grounded in both codebase analysis (confirmed bare excepts, SEOContext construction sites) and SEO research. Phase-specific warnings are concrete. |

**Overall confidence:** HIGH

### Gaps to Address

- **STACK.md not produced:** Stack constraints were fully covered by ARCHITECTURE.md's deep codebase analysis. No gap in practice — note for completeness.
- **`_select_editorial_blueprint()` decision logic:** M1 pitfall requires content type to gate blueprint selection. The full blueprint selection logic was not analyzed in depth. Needs review during Phase 3 planning to avoid unintended B2B-vocabulary bleed.
- **`QualityGateService` internal architecture:** Phase 4 quality gate extension is flagged but the gate's internal extensibility pattern was not fully mapped. Review `quality_gate.py` structure during Phase 4 planning.
- **LLM model JSON mode support:** If the configured model is a custom/local model that doesn't support `response_format`, the fallback path (regex JSON extraction) needs to be verified against the actual model in use. Flag for environment validation during Phase 2 deployment.
- **Confidence threshold calibration:** The `0.75` threshold for fallback-to-general is a reasonable starting estimate. Real-world threshold tuning requires observing production classification data — plan a monitoring pass after Phase 2.

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)
- `src/models/seo_context.py` — SEOContext fields, to_content_creator_task(), Pydantic patterns
- `src/agents/content_creator.py` — _build_synchronized_prompt(), EDITORIAL_BLUEPRINTS, ContentCreatorAgent architecture
- `src/scheduler/jobs.py` (lines 1620–1720) — exact insertion point, SEOContext construction sites, legacy fallback path
- `src/services/content/intent_analyzer.py`, `professional_writer.py`, `outline_generator.py` — existing intent/outline patterns
- `src/services/quality_gate.py` — existing structural validation rules
- `src/core/ai_provider.py` — OpenAICompatibleProvider generate_text() kwargs forwarding
- `.planning/codebase/CONCERNS.md` — bare except locations, schema risks

### Primary (HIGH confidence — industry SEO canon)
- Ahrefs: "Search Intent in SEO" — content type/format/angle framework, mixed intent keywords
- Ahrefs: "How to Write a Great Listicle", "How to Write a Blog Post" — per-type structural conventions
- Semrush: "What Is Search Intent?" — overlapping intents, SERP format dominance
- Backlinko: "SEO Copywriting: The Definitive Guide" — per-type prose conventions
- Google Search Quality Evaluator Guidelines (via Semrush) — Know/Do intent taxonomy

### Secondary (HIGH confidence — version-verified)
- OpenAI SDK 1.10.0 changelog — `response_format={"type": "json_object"}` support confirmed
- `requirements.txt` — `langchain==0.1.4`, `openai==1.10.0`, `pydantic==2.5.3`, `jinja2==3.1.3`

---

*Research completed: 2026-04-03*
*Ready for roadmap: yes*
