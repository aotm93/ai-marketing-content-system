# Strategic Generation Improvement Plan
> **Objective**: Upgrade content generation logic from "Simple AI" to "SEO-Led Content Marketing Engine" to maximize traffic acquisition.

## 1. Analysis of Current Logic
- **Current State**: 
  - Dual Engine: GSC (Optimization) + Keyword API (Expansion).
  - Structure: Outline -> Post (HTML) -> Meta.
  - Deficiency: Logic is linear and simplistic. Lacks depth in "Ranking Factors" (E-E-A-T, Semantic entities, User Intent match, Internal Linking topology).
- **Goal**: Add "SEO Depth" + "Content Marketing Value".

## 2. Proposed "Advanced SEO Strategy" (The 5-Layer Model)

### Layer 1: Semantic SEO & Intent Matching (Keyword → Topic)
- **Problem**: Just targeting "keyword" is 2015 SEO.
- **Solution**: Use `KeywordClient` to fetch **Related Keywords** and **LSI (Latent Semantic Indexing)** terms.
- **Action**: 
  - Enhance `jobs.py`: Before generation, fetch `related_keywords`.
  - Inject these into the AI Prompt: "Must seamlessly integrate these 5 semantic terms: [...]"

### Layer 2: E-E-A-T Enforcement (Expertise, Experience, Authoritativeness, Trustworthiness)
- **Problem**: AI content feels generic.
- **Solution**: 
  - **Auto-Citing**: Configure AI to reference "Recent Studies" or "Industry Standards" (simulated or real if browsing enabled).
  - **Author Persona**: Assign an "Expert Persona" (e.g., "Certified Water Quality Expert") to the generation context.
  - **Action**: Update `AIProvider` prompts to enforce rigorous tone and citation style.

### Layer 3: Strategic Internal Linking (The "Cluster" Effect)
- **Problem**: Standalone posts get no link juice.
- **Solution**: 
  - **Cluster Logic**: Detect existing related posts in DB.
  - **Automatic Interlinking**: AI must insert 2-3 links to *existing* slug/titles provided in context.
  - **Action**: Add `get_related_posts(topic)` in `WordPressClient`, pass to AI prompt.

### Layer 4: Content Depth & Utility (Value > Word Count)
- **Problem**: Long content != Good content.
- **Solution**: 
  - **Mandatory Elements**: Every post MUST have a `Comparison Table`, `Pros/Cons List`, or `Step-by-Step Guide` (Schema valid).
  - **Action**: Enforce these structure requirements in `outline_prompt`.

### Layer 5: Post-Publishing Feedback Loop
- **Problem**: Publish and forget.
- **Solution**: 
  - **Rank Tracking**: Check rank 7 days later. If > pos 20, trigger "Content Refresh Job" (Add FAQ, rewrite intro).
  - *(Already partially in P2 design, but need to solidify).*

---

## 3. Implementation Steps (Orchestration Phase 2)

### Step 1: Update prompts in `jobs.py` (`seo-specialist`) - **Priority High**
- [ ] Inject `semantic_keywords` into prompts.
- [ ] Enforce `E-E-A-T` persona constraints.
- [ ] Add `structure_requirements` (Tables, Lists, Quotes).

### Step 2: Implement Internal Linking Logic (`backend-specialist`)
- [ ] Create `WordPressAdapter.get_recent_posts(category)`.
- [ ] Pass these to AI: "Link to these relevant articles: [A, B, C]".

### Step 3: Verify with "SEO Score" (`test-engineer`)
- [ ] Create `scripts/audit_content_quality.py`.
- [ ] Use LLM to "Grade" its own output based on Google's Quality Rater Guidelines.

## 4. Execution Role Assignment
- **Project Planner**: Define this roadmap.
- **SEO Specialist**: Design the Prompts & Ranking Factors.
- **Backend Specialist**: Implement the API calls and Data/Context piping.
