# Requirements: BoboPkg SEO Automation Platform

**Defined:** 2026-04-03
**Core Value:** The autopilot reliably publishes SEO-optimized articles that are structurally matched to their keyword intent — so every article earns its ranking by actually serving what the searcher needs.

## v1 Requirements

### Classification

- [ ] **CLASS-01**: System classifies article title intent into one of 5 types (how-to, listicle, comparison, review, pricing) plus a general fallback, via a single JSON-mode LLM call
- [ ] **CLASS-02**: Classification includes a confidence score; falls back to general template when confidence < 0.75 or when the LLM call fails
- [ ] **CLASS-03**: Hybrid intent detection: system can identify a secondary content type for ambiguous titles (e.g. "Best X Reviews" = listicle + review) and merge template guidance accordingly

### Templates

- [ ] **TMPL-01**: Each of the 5 content types has a defined ordered section structure (H2/H3 skeletons) — how-to gets numbered steps, listicle gets ranked items with pros/cons, comparison gets side-by-side tables, review gets verdict section in first 200 words, pricing gets price tier tables
- [ ] **TMPL-02**: Each content type has per-section writing instructions (prose style, structural requirements, SEO directives) used to enrich the LLM writing prompt
- [ ] **TMPL-03**: A general/fallback template is available for unclassified or low-confidence titles that maintains quality without type-specific structure

### Pipeline Integration

- [ ] **PIPE-01**: `SEOContext` DTO extended with `content_type` (ArticleContentType enum), `content_type_confidence` (float), and `planned_outline` (list of section dicts) — all Optional with defaults, fully backward-compatible
- [ ] **PIPE-02**: New `ContentPlannerService` inserted in `content_generation_job()` between outline creation and writer invocation, wrapped in non-fatal try/except so existing pipeline degrades gracefully if planner fails
- [ ] **PIPE-03**: `ContentCreatorAgent` consumes `content_type` and `planned_outline` from enriched `SEOContext` to inject type-specific writing guidance and section structure into the LLM writing prompt

### Robustness

- [ ] **ROBUST-01**: Bare `except:` clauses in `jobs.py` patched to specific exception types (prerequisite for safe pipeline schema changes — prevents silent failures masking new field errors)
- [ ] **ROBUST-02**: Outline validation: programmatic check that generated outline contains keyword anchor in at least one heading and meets minimum section count before passing to writer

## v2 Requirements

### Quality Gate Extension

- **QGATE-01**: `QualityGateService` extended with type-aware structural checks (comparison table presence, review verdict position, how-to numbered step count, pricing table presence)
- **QGATE-02**: FAQ section auto-injection for how-to, pricing, and review articles (structured data opportunity)

### Analytics

- **ANALYTICS-01**: Content type classification results logged per job run (type, confidence, fallback used) for pipeline monitoring
- **ANALYTICS-02**: Admin dashboard shows content type distribution across published articles

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web research enrichment before writing | Adds latency and complexity; structure improvement delivers value without it — deferred |
| Custom user-defined content types | Admin UI complexity; 5 types + general cover ~95% of SEO content — deferred |
| Schema markup / FAQ structured data injection | Separate concern from content structure; v2 quality gate phase |
| Replacing LangChain/LangGraph orchestration framework | Too disruptive; dependency upgrades are a separate tech-debt phase |
| Security fixes (hardcoded credentials, CORS, plain-text auth) | Critical but separate from content generation; tracked in CONCERNS.md |
| Multi-platform publishing (non-WordPress) | WebhookAdapter already stubbed; not current focus |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ROBUST-01 | Phase 1 — Classification & Template Infrastructure | Pending |
| CLASS-01 | Phase 1 — Classification & Template Infrastructure | Pending |
| CLASS-02 | Phase 1 — Classification & Template Infrastructure | Pending |
| TMPL-01 | Phase 1 — Classification & Template Infrastructure | Pending |
| TMPL-02 | Phase 1 — Classification & Template Infrastructure | Pending |
| TMPL-03 | Phase 1 — Classification & Template Infrastructure | Pending |
| PIPE-01 | Phase 2 — Pipeline Integration & Robustness | Pending |
| PIPE-02 | Phase 2 — Pipeline Integration & Robustness | Pending |
| PIPE-03 | Phase 2 — Pipeline Integration & Robustness | Pending |
| CLASS-03 | Phase 2 — Pipeline Integration & Robustness | Pending |
| ROBUST-02 | Phase 2 — Pipeline Integration & Robustness | Pending |

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-03*
*Last updated: 2026-04-03 after initial definition*
