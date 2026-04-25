# Context Snapshot: gsc-priority-upgrade

- Timestamp: 2026-04-25T04:17:55Z
- Task statement: Upgrade and refactor the production system so it prioritizes content generation and link generation using Google Search Console keywords/pages that already have substantial impressions and evident user demand.
- Desired outcome: A clarified, execution-ready upgrade direction for a GSC-driven SEO operating system that increases traffic from proven demand instead of treating GSC as only one keyword source.
- Stated solution: Rebuild the prioritization layer and reference current professional Google SEO optimization systems as input to the upgrade plan.
- Probable intent hypothesis: Shift the platform from generic topic generation toward demand-capture, page-level optimization, and asset expansion around already validated search demand.

## Known Facts / Evidence

- This is a brownfield SEO automation platform with GSC, WordPress, content generation, internal linking, backlink discovery, opportunities, and scheduler pipelines.
- `src/scheduler/jobs.py` currently uses GSC first inside `content_generation_job`, but only as a keyword source for new content selection.
- `src/integrations/gsc_client.py` provides:
  - low-hanging fruit query discovery
  - declining page detection
  - raw search analytics access
- `src/agents/opportunity_scoring.py` scores low-hanging fruit, CTR optimization, and cannibalization opportunities.
- `src/agents/content_refresh.py` exists, but the current job path mainly refreshes declining pages and appends generic AI-generated sections.
- `src/agents/internal_link.py` exists, but `internal_linking_job` currently focuses on recent drafts/new posts rather than sitewide demand-prioritized reinforcement.
- `src/backlink/copilot.py` and weekly backlink scan exist, but backlink discovery is not visibly tied to GSC impression clusters/pages.
- `src/api/opportunities.py` manages opportunity records, but repository evidence so far suggests no unified action planner across:
  - new content
  - refresh
  - CTR/meta optimization
  - internal links
  - external links
- Existing scheduler comments say: `Opportunity Discovery: GSC > Keyword API > Static Fallback`, which indicates source precedence, not a full action-priority operating system.

## Constraints

- Production system; planning must preserve current operation safety.
- Brownfield integration should reuse existing GSC, opportunity, scheduler, content, and linking modules where possible.
- No evidence yet that the user wants a pure strategy memo only; likely needs an implementation-oriented upgrade plan after clarification.

## Unknowns / Open Questions

- Primary business KPI for this upgrade:
  - clicks
  - qualified traffic
  - leads/conversions
  - revenue per page cluster
- Desired scope of the first release:
  - prioritization logic only
  - action orchestration
  - data model/API/dashboard
  - full automation loop
- What should be prioritized first when a page/query has demand:
  - CTR optimization
  - content refresh
  - internal links
  - net-new supporting pages
  - external link acquisition
- How much authority OMX may have to redesign scoring, tables, jobs, and workflow boundaries without further confirmation.
- Which existing production pain is most acute:
  - low traffic growth
  - wrong action selection
  - duplicated content generation
  - weak page refresh quality
  - internal link irrelevance
  - backlink inefficiency
- Whether the user wants Google-official guidance only, or also wants reputable industry systems/frameworks included.

## Decision-Boundary Unknowns

- Can the upgrade introduce new tables / job types / opportunity types?
- Can current autopilot sequencing be changed from "pick keyword then generate" to "score asset then choose best action"?
- Can the system deprioritize net-new content when existing pages have stronger GSC demand?
- Can external SEO frameworks materially reshape current opportunity scoring and workflow design?

## Likely Touchpoints

- `src/scheduler/jobs.py`
- `src/integrations/gsc_client.py`
- `src/models/gsc_data.py`
- `src/api/gsc.py`
- `src/api/opportunities.py`
- `src/agents/opportunity_scoring.py`
- `src/agents/content_refresh.py`
- `src/agents/internal_link.py`
- `src/backlink/copilot.py`

