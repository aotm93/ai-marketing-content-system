# Deep Interview Spec: GSC Priority Upgrade

## Metadata

- Profile: standard
- Rounds: 8
- Final ambiguity: 15.5%
- Threshold: 20%
- Context type: brownfield
- Interview ID: 7dc23d23-b5aa-41ea-9914-5ee3ccbb102a
- Context snapshot: `.omx/context/gsc-priority-upgrade-20260425T041755Z.md`
- Transcript: `.omx/interviews/gsc-priority-upgrade-20260425T041755Z.md`

## Clarity Breakdown

| Dimension | Score |
| --- | ---: |
| Intent | 0.88 |
| Outcome | 0.86 |
| Scope | 0.90 |
| Constraints | 0.78 |
| Success | 0.84 |
| Context | 0.72 |

## Intent

Upgrade and refactor the production SEO system so it stops treating Google Search Console as only one keyword source and instead uses it as a demand-validation layer for prioritizing actions that increase qualified inquiries and conversion-oriented organic traffic.

## Desired Outcome

Build a cluster-level SEO operating system that:

- prioritizes customer-value query/page demand already visible in GSC
- dynamically chooses the best action for each cluster
- favors conversion impact over generic traffic growth
- uses supporting informational assets only when they strengthen conversion paths

## In-Scope

- Replace isolated keyword-source selection with cluster-level prioritization
- Score clusters using a mixed model across:
  - GSC demand
  - keyword intent
  - page type / conversion proximity
  - existing page performance
  - support-page / internal-link potential
- Dynamically select the best action per cluster:
  - existing page CTR/title/meta optimization
  - content refresh / content depth expansion
  - internal linking reinforcement
  - new supporting content generation
  - external link / backlink support
- Reframe GSC entities from single query opportunities into query-page cluster opportunities
- Preserve brownfield reuse of existing modules where possible
- Plan against latest Google official guidance and current Search Console usage patterns

## Out-of-Scope / Non-goals

- Chasing generic informational traffic as a primary objective
- Chasing tutorial-style traffic as a primary objective
- Chasing science/popular-education traffic as a primary objective
- Treating informational pages as first-class goals unless they support conversion pages
- Fixed-sequence automation that always generates new content first

## Decision Boundaries

- OMX may redesign prioritization from isolated keyword choice to cluster-level decisioning
- OMX may avoid single hard gates and use weighted mixed scoring instead
- OMX may dynamically choose among refresh, CTR optimization, internal links, supporting pages, and backlinks
- Informational-looking keywords may be included only when they materially support a conversion-driving cluster
- The default decision unit should be a topic/page cluster, not a single keyword or a single page

## Constraints

- The system is already in production; upgrade planning should minimize migration risk
- Existing brownfield components should be reused when possible:
  - `src/scheduler/jobs.py`
  - `src/integrations/gsc_client.py`
  - `src/models/gsc_data.py`
  - `src/api/opportunities.py`
  - `src/agents/opportunity_scoring.py`
  - `src/agents/content_refresh.py`
  - `src/agents/internal_link.py`
  - `src/backlink/copilot.py`
- V1 should optimize for qualified inquiry/conversion growth, not vanity traffic
- No single-signal hard gate should determine eligibility by itself

## Testable Acceptance Criteria

- A planning artifact defines a new cluster-level priority model rather than a single-keyword picker
- The model explicitly ranks conversion-value clusters above generic high-impression traffic
- The model supports mixed scoring across at least GSC demand, keyword intent, page type, and conversion relevance
- The action engine can recommend different next actions for different clusters instead of always generating new content
- Informational/tutorial/educational assets are represented as support assets, not primary targets, unless business logic overrides them
- Brownfield integration points are identified for scheduler, opportunity storage, APIs, and action execution modules
- The plan references current Google official SEO/Search Console guidance for titles, snippets, internal links, helpful content, and crawlable site structure

## Assumptions Exposed + Resolutions

- Assumption: Commercial keyword wording alone is the best first filter.
  - Resolution: Rejected. Mixed scoring is preferred because conversion-capable pages and GSC behavior can reveal value even when wording is not explicitly commercial.

- Assumption: High GSC impressions should automatically lead to new content creation.
  - Resolution: Rejected. Action choice should be dynamic and cluster-specific.

- Assumption: The decision unit should be a single query or page.
  - Resolution: Rejected. Cluster-level decisioning better matches conversion paths and internal-link strategy.

## Pressure-Pass Findings

- Revisited answer: first-priority signal for identifying high-value demand
- Change made: from lexical commercial-intent preference to weighted mixed scoring
- Why it changed: the user clarified that customer value can exist when page context and cluster role are strong even if keyword wording is not overtly commercial

## Brownfield Evidence vs Inference

### Repository-grounded evidence

- `src/scheduler/jobs.py` uses GSC first in `content_generation_job`, but currently as a source for selecting new content topics.
- `src/agents/content_refresh.py` exists and is GSC-triggerable for declining pages.
- `src/agents/internal_link.py` and `internal_linking_job` exist, but current orchestration is oriented to recent drafts/new posts.
- `src/backlink/copilot.py` exists, but weekly backlink scanning is not visibly tied to GSC demand clusters.
- `src/agents/opportunity_scoring.py` already scores opportunities such as low-hanging fruit and CTR optimization.

### Inference

- The current system has the building blocks for a demand-prioritized action engine, but not the orchestration layer that converts GSC evidence into cluster-level action choice.

## Technical Context Findings

- Current opportunity discovery order in content generation is effectively:
  - GSC
  - content-aware keyword strategy
  - other fallbacks
- This is not yet equivalent to:
  - cluster assembly
  - cluster scoring
  - best-action selection
  - action execution
  - feedback measurement

## Planning Direction Anchored To Current Google Guidance

These are planning anchors, not direct copied prescriptions:

- Google emphasizes helpful, reliable, people-first content rather than content created mainly to attract search visits.
- Search Console Performance should be used to understand which queries show the site and which queries/pages are bringing traffic.
- Title links should be descriptive and concise; keyword stuffing is discouraged.
- Meta descriptions should be descriptive and useful, not keyword lists.
- Internal links should use descriptive anchor text, and important pages should be linked from other pages on the site.
- URL/site structure should use descriptive, persistent URLs and avoid duplicate/temporary parameter patterns that waste crawl effort.

## Official References

- Google Search Central: Creating helpful, reliable, people-first content  
  https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- Search Console Help: Performance report  
  https://support.google.com/webmasters/answer/7576553
- Google Search Central: Influencing title links  
  https://developers.google.com/search/docs/appearance/title-link
- Google Search Central: Meta descriptions and snippets  
  https://developers.google.com/search/docs/appearance/snippet
- Google Search Central: SEO link best practices  
  https://developers.google.com/search/docs/crawling-indexing/links-crawlable
- Google Search Central: Designing a URL structure for ecommerce websites  
  https://developers.google.com/search/docs/specialty/ecommerce/designing-a-url-structure-for-ecommerce-sites

## Recommended Handoff

### `$ralplan` (Recommended)

- Why: the requirements are now clear enough, and the next need is architecture / scoring / data model / job sequencing design for a brownfield refactor.
- Input artifact: `.omx/specs/deep-interview-gsc-priority-upgrade.md`
- Expected output:
  - PRD for the cluster-priority upgrade
  - test-spec for scoring, action selection, and migration-safe rollout
  - phased implementation plan

