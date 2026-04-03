# Roadmap: BoboPkg SEO Content Generation Improvement

## Overview

The autopilot currently generates every article with the same generic H2 skeleton regardless of what the title signals. This milestone delivers AI-driven content type classification and intent-matched article structure in two phases: first build the classification service and templates in isolation (zero pipeline risk), then wire it end-to-end so every production article receives type-specific structure and prose guidance from title to published post.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Classification & Template Infrastructure** - Build `ContentPlannerService`, `ArticleContentType` enum, and all 5 content-type templates — no pipeline touch, fully unit-testable in isolation
- [ ] **Phase 2: Pipeline Integration & Robustness** - Wire the planner into `jobs.py`, extend `SEOContext`, update `ContentCreatorAgent`, add hybrid intent and outline validation

## Phase Details

### Phase 1: Classification & Template Infrastructure
**Goal**: A standalone `ContentPlannerService` exists that can classify any article title into a content type with confidence score and return a type-specific section outline — proven correct in unit tests before touching the live pipeline
**Depends on**: Nothing (first phase) — prerequisite ROBUST-01 is included here as the first task
**Requirements**: ROBUST-01, CLASS-01, CLASS-02, TMPL-01, TMPL-02, TMPL-03
**Success Criteria** (what must be TRUE):
  1. Bare `except:` clauses in `jobs.py` are replaced with specific exception types — new field errors will surface immediately in logs rather than being silently swallowed
  2. `ContentPlannerService.classify_title()` returns an `ArticleContentType` enum value and a float confidence score for any string input
  3. When the LLM call fails or returns confidence < 0.75, the service returns `ArticleContentType.GENERAL` without raising — existing pipeline is never disrupted
  4. All 5 content types (how-to, listicle, comparison, review, pricing) plus general fallback have defined `ContentTypeTemplate` dataclasses with ordered `SectionTemplate` lists and per-section writing instructions
  5. Unit tests pass for classifier (correct type returned, fallback triggered on low confidence, LLM error handled) and templates (all 6 types return non-empty section lists with prose instructions)
**Plans**: TBD

### Phase 2: Pipeline Integration & Robustness
**Goal**: Every article produced by the autopilot receives a type-classified, type-structured outline before writing begins — `ContentCreatorAgent` consumes content type and planned outline from enriched `SEOContext`, and hybrid/ambiguous titles are handled without silent fallback to generic structure
**Depends on**: Phase 1
**Requirements**: PIPE-01, PIPE-02, PIPE-03, CLASS-03, ROBUST-02
**Success Criteria** (what must be TRUE):
  1. `SEOContext` carries `content_type`, `content_type_confidence`, and `planned_outline` fields (all Optional with defaults) — constructing `SEOContext` with only pre-existing fields raises no `ValidationError`
  2. A content generation job run produces a log entry showing `ContentPlannerService` was invoked, what type was classified, and whether it fell back to general — classification is observable without reading source code
  3. `ContentCreatorAgent` injects type-specific prose instructions and the planned section outline into the LLM writing prompt — the generated article's H2 structure matches the type template, not the generic fallback skeleton
  4. Ambiguous titles (e.g. "Best X Reviews") are classified with a `secondary_type` field, and the writer receives blended template guidance from both types rather than forcing one or silently ignoring the secondary signal
  5. Before the outline reaches the writer, a programmatic check confirms the target keyword appears in at least one H2 heading and the section count meets the per-type minimum — if either fails, the outline is regenerated once before falling back to general
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Classification & Template Infrastructure | 0/? | Not started | - |
| 2. Pipeline Integration & Robustness | 0/? | Not started | - |
