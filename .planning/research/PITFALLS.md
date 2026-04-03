# Domain Pitfalls: AI-Driven Content Type Classification & SEO Writing

**Domain:** AI content type classification + intent-specific outline/writing in an existing SEO pipeline
**Project:** BoboPkg SEO Automation Platform
**Researched:** 2026-04-03
**Confidence:** HIGH (grounded in codebase analysis + SEO industry sources)

---

## Critical Pitfalls

Mistakes that cause rewrites, ranking failures, or pipeline regressions.

---

### Pitfall C1: LLM Classification Hallucinating a Confident Wrong Type

**What goes wrong:** The LLM is asked to classify a title's intent (e.g., "how-to" vs. "listicle" vs. "comparison") and returns a plausible-sounding but wrong type with high apparent confidence. Example: "Best 10 Polyethylene Pipe Fittings for Industrial Use" gets classified as `comparison` instead of `listicle` because the LLM anchors on "industrial use" as a comparison signal.

**Why it happens:**
- LLMs are trained to be confident and fluent. They do not spontaneously surface uncertainty.
- Title-only classification gives the model minimal signal — no keyword data, no SERP context.
- The 5-type taxonomy (how-to, listicle, comparison, review, pricing) has overlapping signals: listicle titles often contain comparative language; reviews overlap with pricing guides; how-to guides may embed lists.
- The existing `SearchIntentAnalyzer` in `intent_analyzer.py` uses keyword pattern matching (rule-based, not LLM); the new LLM classifier will have different failure modes that bypass those rules.

**Consequences:**
- A listicle gets a comparison H2 structure (e.g., "X vs. Y" table sections instead of numbered picks with rationale)
- Misclassified type cascades: the wrong `section_outline` is inserted into `SEOContext`, the `ProfessionalContentWriter` generates wrong prose format, and the `QualityGateService` may not catch the mismatch (it validates structure, not semantic type fitness)
- Published articles underperform because their format doesn't match what Google's SERP dominance pattern expects for that keyword

**Warning signs:**
- Repeating runs of the same title produce different type labels
- "Comparison" or "review" over-represented vs. actual title distribution
- Listicle articles shipping with `<table>` as primary structure instead of ordered/unordered lists

**Prevention:**
1. **Return a typed response, not free text.** Use a structured output schema with an explicit enum: `{"type": "listicle" | "how-to" | "comparison" | "review" | "pricing", "confidence": float, "rationale": string}`. With LangChain 0.1.x (current stack), use `PydanticOutputParser` or `StructuredOutputParser` — do not rely on free-text parsing of a classification answer.
2. **Provide a confidence threshold fallback.** If `confidence < 0.75`, fall back to the existing rule-based `SearchIntentAnalyzer` or default to `"how-to"` (safest generic fallback). Log the low-confidence classifications for monitoring.
3. **Include SERP signal or keyword alongside the title.** The `SEOContext` already has `target_keyword`, `semantic_keywords`, and `page_type` — pass all three to the classification prompt, not just the `topic_title`. More signal → less hallucination.
4. **Few-shot examples in the prompt.** Include 2–3 canonical examples per type. Especially disambiguate listicle vs. comparison vs. review — the three most confusable types.

**Phase:** Classification step (new planning step); build the fallback and structured output on day one.

---

### Pitfall C2: The "Template Bleed" Problem — Type-Specific Prompts Producing Generic Output

**What goes wrong:** Each content type gets a dedicated writing prompt, but the LLM gradually reverts to a generic article skeleton: intro paragraph → 4–6 H2 sections → conclusion. The type-specific instructions become decorative rather than structural. A how-to article gets numbered steps but the steps are embedded inside prose paragraphs instead of being the H2/H3 spine of the article. A pricing guide produces a comparison table but buries it in section 4 instead of opening with it.

**Why it happens:**
- The existing `ContentCreatorAgent._build_synchronized_prompt()` already uses `EDITORIAL_BLUEPRINTS` (4 defined: `diagnostic_playbook`, `procurement_briefing`, `spec_tradeoff_lab`, `buyer_qa_interview`). These blueprints describe *tone and flow*, not *structural skeleton*. The new content type system will need to add *section-level scaffolding*, which is a harder constraint for the LLM to maintain.
- LLMs are pre-trained on generic article structure. Without explicit H2-level ordering in the prompt, they revert to the learned prior.
- Long prompts with many competing instructions cause the model to honor the most familiar pattern (generic article) over the unusual one (strict type template).

**Consequences:**
- How-to articles lack a step-by-step numbered spine → fail Google's "featured snippet for how-to" eligibility
- Comparison articles lack a side-by-side table at the decision point → lower engagement, lower dwell time
- Pricing articles bury the price table → higher bounce rate from users who scan for the number first

**Warning signs:**
- `content_html` word count varies wildly between runs with same type (1800 words vs. 3500 words for same type)
- H2 headings are generic ("Introduction", "Conclusion") rather than type-specific ("Step 1: ...", "#1 Best For...")
- Quality gate `insufficient_section_headings` warnings increase after type prompts are introduced

**Prevention:**
1. **Put the skeleton in the prompt, not just the style.** For each content type, explicitly list the required H2 sequence. Example for listicle: `Required H2 order: [#1 [Product Name] — Best For [Use Case], #2 ..., Buyer Checklist, FAQ]`. The LLM can fill in the content but must follow the declared skeleton.
2. **Separate the outline step from the writing step.** The new planning step should produce a concrete `section_outline` (list of `{h2_title, h3_titles[], key_points[]}`) before writing begins. The writer is then instructed to *fill in* the outline — not generate the structure. This matches how `ContentOutline` is already modeled in `content_intelligence.py`.
3. **Use a "skeleton first, validate, then write" pattern.** Generate the outline, check it matches the expected type structure (e.g., "listicle must have N items with parallel structure"), then pass to writer. Reject and regenerate if mismatched.
4. **Keep type-specific prompts short and structural.** Long per-type prompts with prose style guidance tend to override the skeleton rules. Structural constraints should appear in the first 200 tokens.

**Phase:** Outline generation step and per-type prompt design.

---

### Pitfall C3: Ambiguous Title → Wrong Type → No Recovery Path

**What goes wrong:** Some titles are genuinely ambiguous. "HDPE Pipe Fittings Cost Guide vs PVC" is simultaneously a pricing guide AND a comparison. The LLM picks one. The resulting article ignores the other dimension. There is no fallback or blended type.

**Why it happens:**
- The 5-type taxonomy is mutually exclusive in implementation (one enum value), but reality has mixed-intent keywords
- Ahrefs research confirms: many keywords have "overlapping intents" (e.g., "best air fryer" is simultaneously informational, commercial, and comparison)
- The existing `SEOContext.page_type` field only stores one value (`category_support` by default)
- The title is classified in isolation from the keyword's actual SERP competition

**Consequences:**
- Pricing guide structure for a title that signals comparison → misses the comparison table Google expects to see
- Article ranks for neither intent because it's 70% one format and missing the elements expected for the other

**Warning signs:**
- Titles containing both "best" AND a number AND "vs" or "cost/price" signal ambiguity
- Low word count and sparse H3 structure when the LLM picks the "simpler" of two overlapping types

**Prevention:**
1. **Detect ambiguity at classification time.** If the LLM returns `confidence < 0.8` OR the prompt contains signals from two type categories, flag as `mixed_intent`. Route to a blended template that covers both (e.g., comparison-with-pricing always includes both a comparison matrix AND a pricing breakdown section).
2. **Define a `secondary_type` field on `SEOContext`.** A `primary_type: ContentType` and `secondary_type: Optional[ContentType]` pair lets the outline generator produce a hybrid section sequence.
3. **Keyword-level SERP patterns beat title-level inference.** Where keyword data (from DataForSEO, already integrated) is available, use SERP format distribution to validate or override the title-based classification.

**Phase:** Classification step and `SEOContext` schema extension.

---

### Pitfall C4: `SEOContext` Schema Drift Breaking the Existing Pipeline

**What goes wrong:** Adding `content_type` and `section_outline` fields to `SEOContext` (the central DTO) causes validation failures in the existing flow. `SEOContext` is constructed in **5 separate places** in `jobs.py` (lines 1119, 1197, 1246, 1355, 1444, 1534 — confirmed by codebase analysis). Each construction site specifies only a subset of fields. New required fields added without defaults will raise Pydantic `ValidationError` at any construction site that doesn't pass the new field.

**Why it happens:**
- `SEOContext` is a Pydantic `BaseModel`. Any field without a default value is required. The existing fields use `Field(...)` (required) and `Field(default=...)` (optional). New fields must be optional with safe defaults.
- The `to_content_creator_task()` and `to_publishable_content()` methods serialize the full model — if `content_type` is added as an enum field, all downstream deserializers (WordPress adapter, quality gate) must handle the new key or fail silently.
- `jobs.py` has bare `except:` clauses (confirmed in CONCERNS.md, lines 1574, 1861, 2075, 2438) that will swallow a `ValidationError` and silently run the legacy fallback path — meaning a schema bug might go undetected for days in production.

**Consequences:**
- Autopilot silently falls back to legacy generation (line 1676–1705 in `jobs.py`) without surfacing the schema failure
- The `QualityGateService` never sees the new `content_type` field and cannot validate type-specific structure requirements
- Alembic migrations are not required for `SEOContext` (it's an in-memory DTO, not a DB model), but if `generation_metrics: Dict[str, Any]` stores content_type and the metrics are later persisted, schema drift in persisted payloads becomes a problem

**Warning signs:**
- `SEOContext not available, using legacy content generation` log messages appearing after the new planning step is deployed
- `ValidationError` exceptions silently caught by bare `except:` in `jobs.py`
- Sudden increase in legacy-path article publications (no `selected_title`, generic structure)

**Prevention:**
1. **New fields MUST have safe defaults.** Use `Optional[ContentType] = None` and `section_outline: Optional[List[SectionSpec]] = None`. The writer falls back gracefully if these are `None`.
2. **Add a schema migration test.** Write a unit test that constructs `SEOContext` with only the pre-existing fields (no `content_type`, no `section_outline`) and asserts no `ValidationError`. Run it as a regression gate.
3. **Fix the bare `except:` clauses in `jobs.py` BEFORE deploying the new fields.** This is already in CONCERNS.md as HIGH severity. At minimum, wrap the `SEOContext` construction sites in `except Exception as e: logger.error(...)` to surface schema failures.
4. **Don't overload `generation_metrics`.** Resist the temptation to store `content_type` in `generation_metrics: Dict[str, Any]` as a quick workaround. Use a typed field — `generation_metrics` is opaque and breaks type safety.

**Phase:** `SEOContext` schema extension and the new planning step insertion.

---

### Pitfall C5: LLM-Generated Outline Ignoring the Target Keyword

**What goes wrong:** The LLM generates an outline for the content type that is structurally correct (right number of sections, right format) but the H2/H3 headings drift away from the target keyword. Example: target keyword is "HDPE pipe fittings cost breakdown" but the listicle outline generates sections about general "pipe material selection", "installation methods", and "supplier comparison" — none of which directly address cost breakdown.

**Why it happens:**
- LLMs optimize for structural plausibility and topical breadth, not keyword focus. Without explicit keyword-anchoring instructions at the outline generation stage, the model fills sections with "reasonable" content for the type, not for the specific keyword.
- The current outline prompt in legacy `jobs.py` (line 1690) says "Semantic Terms to Weave in" — this is a weak constraint. Weaving terms in is different from *anchoring H2s to the keyword*.
- `SEOContext.semantic_keywords` is passed to the writer but not to the outline generator (in the existing flow there is no separate outline generation step).

**Consequences:**
- Keyword appears in the intro but is absent from H2/H3 anchor text → weak on-page SEO signals
- `QualityGateService` validates keyword density in body text (existing check, line 224–238 in `seo_context.py`) but does NOT check keyword presence in headings
- Google cannot confirm topical relevance from heading structure → lower probability of ranking for the target keyword

**Warning signs:**
- H2 headings in published articles don't contain target keyword or its direct variants
- `low_keyword_density` quality gate warnings (though these check body text, not headings)
- Articles for pricing keywords have no H2 that mentions "cost", "price", or "pricing"

**Prevention:**
1. **Require keyword anchoring in the outline generation prompt.** Instruction: "At least 2 of the generated H2 headings MUST contain the target keyword or a direct semantic variant. The first body H2 MUST establish the keyword topic."
2. **Validate the outline before passing to writer.** After outline generation, run a programmatic check: `assert any(keyword.lower() in h2.lower() for h2 in outline_headings)`. If it fails, regenerate (max 1 retry).
3. **Extend the quality gate** to check keyword presence in H2 headings using a heading-specific validation rule — separate from the body density check.

**Phase:** Outline generation step; quality gate extension as a follow-on.

---

## Moderate Pitfalls

Mistakes that degrade content quality or create maintenance overhead.

---

### Pitfall M1: Over-Fitting Type Prompts to B2B Industry Vocabulary

**What goes wrong:** The current codebase is heavily tuned for industrial B2B content (HDPE pipes, polymer fittings, MOQ, certifications — confirmed by `SEMANTIC_EXPANSIONS`, `EDITORIAL_BLUEPRINTS`, and prompt text throughout `content_creator.py`). New content type prompts that inherit this vocabulary will generate wrong prose for non-B2B keywords that flow through the same pipeline.

**Why it happens:**
- The `EDITORIAL_BLUEPRINTS` (diagnostic_playbook, procurement_briefing, etc.) contain B2B-specific language ("MOQ", "audit questions", "supplier shortlisting"). These are selected by `_select_editorial_blueprint()` — if blueprint selection doesn't account for content type, a how-to article about a non-industrial topic will get the "procurement_briefing" blueprint.
- `UserIntent.BUYING_GUIDE` in `intent_analyzer.py` specifically checks for "supplier", "manufacturer", "MOQ", "wholesale" — the new content types (review, how-to, pricing) must have their own independent intents.

**Warning signs:**
- Non-B2B articles contain procurement language ("MOQ", "lead time", "certifications")
- Blueprint selection logs always show `procurement_briefing` regardless of content type

**Prevention:**
1. **Content type should gate blueprint selection.** If `content_type == "how-to"`, `spec_tradeoff_lab` or a new `how_to_guide` blueprint is forced regardless of keyword signals.
2. **Add content type as a first-class signal in `_select_editorial_blueprint()`.** Currently this method uses keyword and hook type — it should also consume `content_type`.
3. **Define new blueprints for review and pricing guide types.** "review_verdict_lab" and "pricing_transparency_guide" as named blueprints alongside the existing 4.

**Phase:** Type-specific prompt design.

---

### Pitfall M2: Section Depth Inconsistency Across Content Types

**What goes wrong:** The LLM generates outlines with inconsistent depth: some types get 3 H2 sections, others get 9. The quality gate enforces a minimum heading count (line 673 in `quality_gate.py`) but does not enforce maximums or type-appropriate ranges. Excessively long outlines for simple types (e.g., a how-to with 12 steps for a 5-step process) produce bloated articles that dilute keyword focus.

**Why it happens:**
- LLMs fill requested depth based on topic complexity as they perceive it, not based on SERP-appropriate length
- The existing 4000-token max in `ContentCreatorAgent` (line 117) acts as a soft word count ceiling but doesn't control section count
- Type-specific depth norms: how-to guides rank well at 5–8 numbered steps; listicles rank well at 7–15 items; comparison articles rank well with 3–6 dimension rows; pricing guides need 4–8 factors

**Warning signs:**
- How-to articles shipping with 12+ numbered steps where SERPs show 5–7
- Comparison articles with one-row tables (only covers one dimension)
- Listicles with 3 items for keywords where SERPs show 10+ item lists

**Prevention:**
1. **Define per-type section count bounds in the outline prompt.** Example: `how-to: 5–8 steps`, `listicle: 7–12 items`, `comparison: 3–6 dimensions`, `review: 5–7 evaluation criteria`, `pricing: 4–8 cost factors`.
2. **Validate outline section count before writing.** Programmatic check: `assert min_sections <= len(outline.sections) <= max_sections`.
3. **Use a `target_word_count` per type** as an outline constraint. Listicles: 1500–2500 words. How-to guides: 1200–2000. Comparison articles: 1500–2500. Reviews: 1800–2800. Pricing guides: 1200–1800.

**Phase:** Outline generation step.

---

### Pitfall M3: Classification Running on Every Article Including Already-Typed Ones

**What goes wrong:** The new LLM classification step runs on every `content_generation_job()` execution — including articles where the keyword source already signals the content type (e.g., a keyword explicitly tagged "review" from the ContentIntelligence source). This wastes API tokens and latency, and introduces a chance of re-classifying a correctly typed keyword to the wrong type.

**Why it happens:**
- The 5 `SEOContext` construction sites in `jobs.py` each build the context from their keyword source. Some sources (ContentIntelligence) may already contain type metadata. Adding a classification step without checking existing type data will blindly re-classify.
- There is already a `page_type` field in `SEOContext` (defaulting to `"category_support"`). The new `content_type` must not conflict with `page_type`.

**Warning signs:**
- Classification API calls spike compared to article volume
- Keywords with explicit type signals getting re-classified differently on retry

**Prevention:**
1. **Check for existing type signal before classifying.** If `seo_context.page_type` already maps to a content type, skip LLM classification and derive `content_type` from it.
2. **Add a `classification_source` field** to track whether the type came from LLM, rule-based fallback, or existing metadata. Useful for debugging type-distribution drift.
3. **Cache classification results keyed on title + keyword hash.** Same title+keyword combination will always produce the same type — avoid re-classifying on retry cycles.

**Phase:** Classification step integration into `jobs.py`.

---

### Pitfall M4: SEO Structure Mistakes That Cause Low Rankings Despite Correct Classification

**What goes wrong:** The content type is correctly identified and the section structure is type-appropriate, but the article still ranks poorly because of content structure errors unrelated to type.

**Specific failure patterns confirmed by SEO research (Ahrefs/Semrush):**

| Structure Mistake | Why It Hurts Rankings | Content Type Most Affected |
|---|---|---|
| Keyword absent from first H2 | Google can't confirm topical relevance from heading hierarchy | All types |
| Step numbers not in H2/H3 text (buried in prose) | Loses "How-to" rich snippet eligibility | How-to |
| Comparison table placed below fold (section 5+) | Users bounce before reaching the comparison; low dwell time | Comparison |
| Listicle items not in parallel structure (item 1 is 50 words, item 7 is 300 words) | Looks low-quality to crawlers and users; reduces featured snippet chance | Listicle |
| Review verdict not in the first 200 words | Users searching for verdict bounce immediately; increases bounce rate | Review |
| Pricing table absent or in prose only | "Pricing" and "cost" queries expect tabular data; Google features tables in snippets | Pricing guide |
| FAQ section missing | Misses People Also Ask opportunities; well-confirmed by Semrush guidelines | All types |
| Keyword density correct in body but absent in H1/title | `validate_synchronization()` in `SEOContext` checks H1 match but not semantic presence | All types |

**Prevention:**
1. **Encode type-specific required elements as outline validation rules** (not just section count). Required: how-to needs numbered steps in H2/H3; comparison needs a table before section 4; review needs a verdict paragraph in the intro; pricing needs a `<table>` in the first 50% of content.
2. **Extend `QualityGateService`** with type-aware structural checks. Currently the quality gate has generic structure checks but no type-specific ones. Post-generation validation should check that the content structure matches the declared `content_type`.
3. **FAQ section is universal.** Regardless of type, a 3–5 item FAQ section should be required in all outlines (the existing quality gate already expects it per line 977 of `quality_gate.py`). Make it explicit in every type template.

**Phase:** Outline validation; quality gate extension.

---

## Minor Pitfalls

Technical issues that create noise but don't cause ranking failures on their own.

---

### Pitfall N1: `content_type` Enum Deserialization Failures at WordPress Publishing Time

**What goes wrong:** `SEOContext.to_publishable_content()` serializes the context to a dict for the WordPress adapter. If `content_type` is a Python `Enum` (like `ContentType.LISTICLE`), it will serialize as `<ContentType.LISTICLE: 'listicle'>` unless explicitly handled — breaking any downstream code that reads the field as a plain string.

**Prevention:** Use `str` enums (`class ContentType(str, Enum)`) — consistent with the existing `SEOElementStatus(str, Enum)` and `UserIntent(str, Enum)` patterns already in the codebase. Verify `to_publishable_content()` includes `content_type` in its output dict (or explicitly excludes it if WordPress doesn't need it).

**Phase:** `SEOContext` schema extension.

---

### Pitfall N2: Outline Generation Prompt Token Bloat from Full `SEOContext` Injection

**What goes wrong:** The new planning step may pass the entire `SEOContext` (serialized via `model_dump()`) into the outline generation prompt. At ~80 fields, the serialized context can exceed 3,000 tokens before the actual instruction. This leaves minimal token budget for the LLM to reason about the outline.

**Prevention:** Create a `to_classification_task()` and `to_outline_task()` on `SEOContext` (analogous to the existing `to_content_creator_task()`) that project only the fields needed: `target_keyword`, `topic_title`, `semantic_keywords[:5]`, `page_type`, and the new `content_type`. Pass the lean projection, not the full model dump.

**Phase:** Planning step implementation.

---

### Pitfall N3: Parallel Autopilot Cycles Producing Duplicate-Type Articles

**What goes wrong:** The `APScheduler` autopilot runs `content_generation_job()` on a schedule. If multiple jobs run concurrently (the scheduler configuration may allow this), two jobs may classify different keywords to the same `content_type` and produce structurally identical articles — triggering the `QualityGateService` duplicate detection even though the keywords are different.

**Prevention:** The duplicate check is similarity-based (Jaccard + shingle comparison — confirmed in `quality_gate.py`). Type-specific templates will increase structural similarity between articles of the same type. Ensure the outline generation step introduces sufficient type-instance differentiation (unique product names, specific keyword anchors) to keep structural similarity below the duplicate detection threshold. Test with two same-type articles through the quality gate before deploying.

**Phase:** Integration testing.

---

### Pitfall N4: Legacy Fallback Path Masking Classification Failures

**What goes wrong:** `jobs.py` lines 1674–1705 contain a full legacy content generation path that runs when `seo_context` is `None`. If the new classification/planning step fails silently (exception swallowed), `seo_context` will be `None` and the legacy path will produce an unstructured article — without any alert that the new step failed.

**Prevention:**
- Add a structured log event when the legacy fallback path is taken: `logger.error("CLASSIFICATION_FAILED: Falling back to legacy path for keyword: %s", keyword)`.
- Add a counter metric to `generation_metrics` tracking `classification_used: bool` and `outline_used: bool` — visible in the admin dashboard.
- Long-term: remove or clearly deprecate the legacy path once the new system is stable.

**Phase:** Planning step integration; monitoring.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| LLM classification prompt design | C1: Hallucinated confident wrong type | Structured output (Pydantic), confidence threshold, few-shot examples |
| `SEOContext` schema extension | C4: Schema drift / ValidationError on existing construction sites | Optional fields with defaults; regression test for all 5+ construction sites |
| Outline generation step | C2: Template bleed to generic structure | Explicit H2 skeleton in prompt; outline validation before writing |
| Ambiguous title handling | C3: Wrong type, no recovery | `confidence < 0.75` fallback; `secondary_type` field for hybrid templates |
| Per-type prompt writing | M1: B2B vocabulary over-fitting | Content type gates blueprint selection; add new blueprints for review/pricing |
| Section depth control | M2: Too many / too few sections | Per-type min/max section count bounds in outline prompt |
| Integration into `jobs.py` | C4, N4: Silent failures masked by bare except / legacy fallback | Fix bare `except:` clauses (CONCERNS.md HIGH priority) before deploying new step |
| Quality gate interaction | M4: Correct type, wrong structure details | Extend quality gate with type-aware structural checks |
| Publishing serialization | N1: Enum serialization failure | Use `str` Enum; test `to_publishable_content()` output |
| Concurrent autopilot runs | N3: Duplicate-type article similarity | Test two same-type articles through quality gate pre-deployment |

---

## Sources

- Codebase: `src/models/seo_context.py`, `src/agents/content_creator.py`, `src/services/content/intent_analyzer.py`, `src/services/content/professional_writer.py`, `src/scheduler/jobs.py` (lines 1620–1720), `src/services/quality_gate.py`
- `.planning/codebase/CONCERNS.md` — bare except clauses, schema risks, legacy fallback path
- Ahrefs: "Search Intent in SEO: What It Is & How to Optimize for It" — confirmed mixed-intent keywords, SERP format dominance patterns, Three Cs framework (content type / format / angle)
- Semrush: "What Is Search Intent? How to Identify It & Optimize for It" — overlapping intents, contextual factors, layered intent
- Google Search Quality Evaluator Guidelines (via Semrush citation) — Know/Do/Website/Visit-in-person intent taxonomy
- Training knowledge (MEDIUM confidence): LLM structured output best practices, Pydantic output parsing with LangChain 0.1.x

---

*Pitfalls audit: 2026-04-03*
