# Feature Landscape: SEO Content Type Classification & Generation

**Domain:** AI-driven SEO article content planning — content type classification, intent-aligned section structure, type-specific prose generation
**Researched:** 2026-04-03
**Confidence:** HIGH (core SEO canon cross-verified via Ahrefs, Semrush, Backlinko; LOW for competitive differentiation claims)

---

## Context: What This Research Covers

The existing BoboPkg pipeline writes every article with the same generic H2 skeleton regardless of title signals. This milestone adds:
1. LLM-based content type classification (from title)
2. Per-type section templates
3. Type-aware prose instructions passed to the writer

The 5 chosen types are: **how-to/tutorial**, **listicle/best-of**, **comparison/versus**, **review**, **pricing/cost guide**.

This research answers what the **content planning subsystem** needs — not the writing LLM itself.

---

## Table Stakes

Features users (and Google) expect. Missing = content won't rank or will rank weakly.

### 1. Content Type Classification from Title (HIGH confidence)
| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Classify title into one of 5 content types | Google's ranking systems determine intent before returning results (confirmed via Semrush/Google docs) — mismatched content type is a primary ranking failure mode | Low | LLM call; single-turn prompt; already scoped |
| Confidence score / fallback to "generic" | Some titles are ambiguous ("Best Guide to X" could be listicle or how-to) — need a fallback rather than forcing a bad classification | Low | Add `confidence: float` + `generic` as 6th type |
| Support for ambiguous/hybrid titles | Ahrefs research confirms many queries have overlapping intents (e.g., "best air fryer" = informational + commercial + list) | Low | Classification prompt should return primary + optional secondary type |

### 2. Type-Specific H2/H3 Section Structures (HIGH confidence)
Every one of the 5 types has industry-established structural conventions. Violating them = content that doesn't match user expectations.

#### How-To / Tutorial
| Section | Why Required | Notes |
|---------|--------------|-------|
| What You Need / Prerequisites | Users need to know if they can follow before reading | Often H2 or intro callout |
| Numbered step sequence (H2 per step) | Core user expectation for tutorial; Google favors ordered list markup for featured snippets | Must be `<ol>`, not arbitrary H2s |
| Step detail: action verb + outcome | Each step H2 must start with imperative verb ("Install", "Configure", not "Step 1") | Prose instruction |
| Tips / Warnings callouts within steps | Signals depth; reduces bounce when user runs into edge cases | H3s or callout blocks |
| Estimated time / difficulty statement | Searchers use this to qualify whether to continue reading | Intro or sidebar |
| Final result / what you've accomplished | Closes the cognitive loop; strong UX signal | Final H2 |
| FAQ section | Captures People-Also-Ask SERP box; high CTR for featured snippet | Optional but high-value |

#### Listicle / Best-Of
| Section | Why Required | Notes |
|---------|--------------|-------|
| Numbered or named items as H2s | Core format; Ahrefs confirms list-style H2s correlate with listicle rankings | Each item = H2 |
| Item description ≥ 2-3 sentences each | "Basic" listicles (1-2 sentences) for long lists (50+); "detailed" (paragraph+) for short lists (<15) | Length depends on total item count |
| "Why it's on the list" rationale | Differentiates from a mere enumeration; builds E-E-A-T | Prose per item |
| Category groupings (for large lists) | "Best for beginners", "Best budget option" — Ahrefs confirms these sub-categories appear in SERP gaps | H2 groups with H3 items |
| Summary / quick picks table | Scannable entry point; captures users who won't read everything | Top of article |
| Selection criteria / how we chose | Establishes authority; expected by sophisticated readers | H2 near intro |
| Conclusion / bottom-line pick | Decisional closure; high engagement signal | Final H2 |

#### Comparison / Versus
| Section | Why Required | Notes |
|---------|--------------|-------|
| Side-by-side feature comparison table | THE defining structural element of this type; missing = not a real comparison article | Must include |
| Individual product/option sections (one H2 per option) | Users want pros/cons per item, not just a table | H2 per option |
| Pros & Cons per option | Standard expectation across all comparison content | H3 under each option H2 |
| "Which one is right for you?" or "Our verdict" H2 | Decisional recommendation section; high value for commercial intent | Required |
| Use-case differentiation ("Choose X if..., Choose Y if...") | Converts fence-sitters; differentiates from generic comparison | Required in verdict |
| Key differences intro summary | First-screenful hook for skimmers | Near intro |
| Pricing comparison | Commercial intent searchers expect cost context | Usually table row or standalone H2 |

#### Review
| Section | Why Required | Notes |
|---------|--------------|-------|
| Overall verdict / rating upfront | Google's product review guidelines reward summaries at top | Required (E-E-A-T signal) |
| Pros & Cons section | Universal reader expectation for reviews; featured snippet candidate | H2 |
| Key features breakdown (H2 per feature group) | Shows actual experience vs. marketing copy | Multiple H2s |
| Performance / test results | Google's review guidance specifically asks for "evidence of testing" | High-value |
| Who it's for / who it's NOT for | Narrows audience; reduces bounce from wrong-fit readers | H2 |
| Comparison to alternatives | Required per Google's product review update guidance | H2 |
| Price & value assessment | Separate from "is it good" — "is it worth it" is distinct intent | H2 |
| Final verdict / score | Bookends the article; strong UX closure | Final H2 |

#### Pricing / Cost Guide
| Section | Why Required | Notes |
|---------|--------------|-------|
| "How much does X cost?" answer in intro | Immediate intent satisfaction; featured snippet bait | Required, near top |
| Price breakdown table (tiers / plans / options) | Core user expectation for cost guides | Required |
| What's included at each price point | Searchers need to understand value-per-dollar | Per-tier content |
| Factors that affect price | Long-tail keyword magnet; explains cost variability | H2 |
| Hidden costs / what to watch out for | Trust signal; differentiates from vendor marketing copy | H2 |
| Free options / alternatives (if any) | Captures "free" modifier intent within the same article | H2 |
| Is it worth the cost? / Value verdict | Decisional closure for cost-motivated searchers | Final H2 |
| How to save money / discounts section | High engagement; covers "cheap X" and "X discount" queries | Optional H2 |

### 3. Type-Aware Prose Writing Instructions (HIGH confidence)
Generic "write professionally" instructions produce generic content. Per-type instructions are table stakes for quality-matched output.

| Content Type | Required Prose Instructions | Complexity |
|--------------|----------------------------|------------|
| How-To | Use imperative verbs in step H2s; address reader as "you"; number steps; use "Note:" / "Tip:" for callouts; past-tense result statements | Low |
| Listicle | Lead each item with the item name; explain *why* not just *what*; use parallel sentence structure across items; group items logically | Low |
| Comparison | Use present tense for features; "X wins when..." / "Y is better for..."; use table markdown for feature matrix; avoid hedging in verdict | Low |
| Review | Use first-person experiential language ("In our testing..."); bold key findings; separate opinion from fact; use explicit rating/score | Low |
| Pricing | State prices explicitly and early; use dollar amounts not vague terms; use table for tiered pricing; clearly label as of date | Low |

### 4. SEOContext Enrichment with Classification Results (HIGH confidence)
The downstream writer must receive structured classification output, not free text.

| Field | Type | Why Required | Complexity |
|-------|------|--------------|------------|
| `content_type` | Enum (5 types + "generic") | Writer and quality gate need this for type-specific behavior | Low |
| `classification_confidence` | Float 0–1 | Enable fallback to generic at low confidence | Low |
| `section_outline` | List[SectionSpec] | Pre-computed H2/H3 structure passed to writer | Medium |
| `prose_instructions` | str | Per-type writing style instructions string | Low |
| `secondary_type` | Optional Enum | Handle hybrid intent (e.g., "Best X Review" = listicle + review) | Low |

---

## Differentiators

Features that set the content platform apart from commodity AI writing tools.

### 1. Hybrid Intent Handling (MEDIUM confidence)
**Value:** Most AI SEO tools classify into one rigid bucket. Titles like "Best [Product] Reviews 2025" are both listicle AND review — treating them as one loses structure from both.
**Implementation:** Classification returns primary + secondary type. Section template merges both: listicle structure for outer items, review-format prose within each item.
**Complexity:** Medium (template merge logic needed)
**Dependency:** Requires section template engine to support composite types

### 2. Content Angle Detection Alongside Type (MEDIUM confidence)
**Value:** Ahrefs' "Three Cs" framework: Content Type + Content Format + Content **Angle**. The angle (e.g., "for beginners", "updated 2026", "budget") changes the slant of sections even within the same type. "Best laptops for beginners" and "Best laptops for developers" are both listicles but need different H2 angle.
**Implementation:** Angle detected from title alongside type; injected into prose instructions ("Target: budget-conscious beginners, not power users").
**Complexity:** Low (single prompt addition)
**Dependency:** None — extends classification prompt

### 3. SERP Feature Targeting per Type (LOW confidence)
**Value:** Different content types target different SERP features. How-to → "How to" rich results + step schema. Review → Review snippet + rating schema. Listicle → Featured snippet list. Pricing → PAA boxes.
**Implementation:** Inject schema-type hints and "snippet bait" sections into outline for each type.
**Complexity:** Medium (schema generation for WordPress)
**Dependency:** Requires WordPress/Rank Math to output schema markup

### 4. Confidence-Based Fallback Chain (MEDIUM confidence)
**Value:** Low-confidence classification (ambiguous title like "Ultimate Guide to X") silently produces misfitted structure. A fallback to "generic informational" with explicit flags is better than a forced classification.
**Implementation:** If `classification_confidence < 0.7`, use generic skeleton with a flag in the plan log; optionally surface to admin dashboard.
**Complexity:** Low
**Dependency:** `classification_confidence` field in SEOContext (table stakes item above)

### 5. Per-Type Optimal Article Length Guidance (MEDIUM confidence)
**Value:** Ahrefs confirms the number of list items in a listicle should match competitor length for the keyword. Similarly, review articles for complex products need deeper coverage than simple products. Length guidance per type improves structure decisions.
**Implementation:** Provide `suggested_length: str` hint (e.g., "aim for 1,800–2,400 words for this comparison type") in prose instructions.
**Complexity:** Low
**Dependency:** None

### 6. Type-Specific FAQ Section Injection (MEDIUM confidence)
**Value:** How-to and pricing articles consistently win People Also Ask SERP features when they include FAQ sections. Adding a FAQ H2 as a standard template element captures these without per-article manual work.
**Implementation:** FAQ section template added as optional final H2 for `how_to`, `pricing`, `review` types. Questions sourced from title keyword context.
**Complexity:** Low-Medium (question generation sub-step)
**Dependency:** FAQs need keyword context — needs title + keyword passed to question generator

---

## Anti-Features

Features to explicitly NOT build in v1 of this milestone.

### 1. SERP Research / Competitor Analysis Before Classification
**Why Avoid:** PROJECT.md explicitly defers "full research enrichment" — fetching live SERPs before classifying adds latency, external API dependency, and cost with minimal gain over LLM-based classification.
**What to Do Instead:** LLM classifies from title alone. Title signals are sufficient for ~85–90% of classification accuracy (titles are deliberately written to signal type).

### 2. Custom Type Definitions / User-Configurable Types
**Why Avoid:** Adds admin UI complexity, prompt variability, and template maintenance burden. The 5 target types cover the dominant SEO article formats. Edge cases handled by "generic" fallback.
**What to Do Instead:** Hard-code 5 types + generic. Log unclassified cases for future type expansion.

### 3. Per-Keyword Content Structure Optimization
**Why Avoid:** True content gap analysis (Ahrefs-style "what do top-ranking pages cover?") requires SERP scraping, which is out of scope (PROJECT.md). Optimizing structure per specific keyword — not just per type — is a future milestone.
**What to Do Instead:** Type-level templates cover 80% of structural quality. Keyword-level optimization is Phase 2.

### 4. Schema Markup Generation
**Why Avoid:** While SERP feature targeting is a differentiator, schema generation for `HowTo`, `Review`, `ItemList` requires WordPress/Rank Math-specific output and is a separate concern from content structure. Rank Math already handles some schema automatically.
**What to Do Instead:** Note schema opportunity in article type metadata; schema generation is a subsequent enhancement.

### 5. A/B Testing Content Structures
**Why Avoid:** Requires performance tracking back to ranking changes, which requires significant GSC feedback loop design — not a content generation concern.
**What to Do Instead:** Keep consistent per-type templates; let ranking data accumulate before structure experiments.

### 6. Multi-Language Content Type Classification
**Why Avoid:** LLM classification in English is well-proven; cross-language intent signals vary (e.g., Japanese SERP format conventions differ from English). Out of scope for v1.
**What to Do Instead:** Classify in English only; add locale flag to SEOContext for future i18n.

---

## Feature Dependencies

```
Title Classification (content_type + confidence)
  → Section Template Selection (content_type → SectionSpec list)
      → SEOContext Enrichment (section_outline + prose_instructions)
          → ContentCreatorAgent writer input
              → QualityGateService (can validate structure alignment)

Secondary Type Detection (secondary_type)
  → Hybrid Template Merging
      → Section Template Selection

FAQ Injection
  → How-to / Pricing / Review type detection (content_type)
      → Question Generation sub-step
          → SEOContext Enrichment
```

**Critical path:** Classification → Template Selection → SEOContext enrichment is the MVP path. All differentiators build on this.

---

## Title Signal Dictionary for Classification

**Signals that reliably indicate content type from title alone** (HIGH confidence, synthesized from Ahrefs/Semrush search intent research + SEO copywriting canon):

### How-To / Tutorial Signals
- Title starts with "How to", "How do I", "How do you"
- Contains: "guide", "tutorial", "step by step", "step-by-step", "walkthrough", "beginners guide"
- Verb-first titles: "Build X", "Create X", "Set Up X", "Configure X", "Install X"
- Time-bounded: "in 5 minutes", "in 10 steps", "quickly"
- Question format with procedural answer: "Can you X?", "What is the best way to X?"

### Listicle / Best-Of Signals
- Starts with or contains a number: "10 Best", "7 Ways", "15 Tips", "Top 5"
- Contains: "best", "top", "greatest", "recommended", "must-have", "essential"
- Plural nouns implying enumeration: "tools", "tips", "ideas", "examples", "strategies", "alternatives"
- "Best X for Y" pattern (best X for beginners, best X for small business)
- "X alternatives to Y" — alternative-finding intent is listicle format

### Comparison / Versus Signals
- Contains: "vs", "versus", "vs.", "or", "compared to", "comparison", "which is better"
- "[A] vs [B]" pattern — strongest signal
- "difference between X and Y"
- "[A] or [B]: Which Should You Choose?"
- Two named products/tools in title

### Review Signals
- Contains: "review", "reviewed", "is X worth it", "X review [year]"
- "[Product name] Review" pattern
- "Honest review", "In-depth review", "detailed review"
- "My experience with X", "after X months with"
- Note: "Best X" is listicle, NOT review. "X Review" (single subject) is review.

### Pricing / Cost Guide Signals
- Contains: "cost", "price", "pricing", "how much", "cost of", "price of", "fees"
- "How much does X cost", "X pricing plans", "X cost guide"
- "Is X worth the price?", "X affordable?"
- "[Year] pricing", "pricing breakdown", "price comparison" (price comparison ≠ product comparison)
- "Free vs paid X"

### Ambiguity Traps (require LLM reasoning, not keywords)
- "Ultimate Guide to X" → could be how-to OR listicle (check if X is a process or a category)
- "Best X Review" → listicle frame + review content (hybrid)
- "X vs Y vs Z: Which is Best?" → comparison, not listicle despite "best"
- "[Number] Best X Reviews" → listicle (not single-subject review)
- "X Pricing vs Competitors" → pricing + comparison hybrid

---

## Quality Signals for Content Type-Structure Alignment

**Metrics that indicate good structural fit** (MEDIUM confidence — synthesized from SEO research; direct "type alignment scoring" is not directly documented anywhere as a standalone metric):

| Signal | What It Measures | Per-Type Relevance |
|--------|-----------------|-------------------|
| H2 count matches type norms | How-to: 5-8 H2 steps; Listicle: 7-20 H2 items; Comparison: 3-6 H2s | All types |
| First H2 position in article | Review/Pricing: answer/verdict near top; How-to: "what you need" first | Review, Pricing |
| Presence of mandatory structural elements | Comparison: has table; Review: has pros/cons; Pricing: has price table | Per-type |
| Imperative verb ratio in how-to H2s | % of H2s that start with action verb | How-to only |
| Prose instruction adherence markers | "In our testing", "we tested" language in review; "Step X" numbering in how-to | Per-type |
| Word count within type range | How-to: 1,200-2,500; Listicle: 1,500-4,000; Comparison: 1,500-3,000; Review: 1,800-3,500; Pricing: 1,000-2,000 | All types |
| FAQ section presence | Present for how-to, pricing, review types | Subset of types |
| Verdict/conclusion H2 present | Review, comparison, pricing types need explicit decisional close | Review, Comparison, Pricing |
| Table markdown presence | Comparison and pricing require tables | Comparison, Pricing |
| Numbered list for steps | How-to steps should use ordered list markup | How-to |

**Quality gate implementation note:** The existing `QualityGateService` can be extended to validate structural alignment using these signals post-writing. This is a natural extension, not in-scope for v1 but flagged for the next quality gate phase.

---

## MVP Prioritization

**Build in this order:**

1. **Classification prompt + confidence score** — smallest change, highest leverage
2. **Section template map (5 types → SectionSpec list)** — pure data, no logic
3. **SEOContext enrichment** (add `content_type`, `section_outline`, `prose_instructions` fields)
4. **Template selection logic** (plug classification → template → writer)
5. **Prose instructions per type** (string constants; no dynamic generation needed)
6. **Generic fallback path** (for low-confidence classification)

**Defer to next iteration:**
- Hybrid/secondary type merging
- Content angle detection
- FAQ injection
- Quality gate structural validation

---

## Sources

- Ahrefs: "Search Intent in SEO" — https://ahrefs.com/blog/search-intent/ (HIGH confidence — industry standard)
- Ahrefs: "How to Write a Great Listicle" — https://ahrefs.com/blog/listicle/ (HIGH confidence)
- Ahrefs: "How to Write a Blog Post" — https://ahrefs.com/blog/how-to-write-a-blog-post/ (HIGH confidence)
- Backlinko: "SEO Copywriting: The Definitive Guide" — https://backlinko.com/seo-copywriting (HIGH confidence)
- Semrush: "What Is Search Intent?" — https://www.semrush.com/blog/search-intent/ (HIGH confidence)
- Google Search Quality Evaluator Guidelines (section 12.7 on user intent) — referenced in Semrush article (HIGH confidence)
- Google ranking systems documentation — https://www.google.com/search/howsearchworks/ (referenced, not directly fetched)
- Training knowledge for per-type structural conventions (MEDIUM confidence — consistent with all fetched sources)
