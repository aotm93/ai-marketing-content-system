# Deep Interview Transcript Summary: gsc-priority-upgrade

- Profile: standard
- Context type: brownfield
- Final ambiguity: 15.5%
- Threshold: 20%
- Interview ID: 7dc23d23-b5aa-41ea-9914-5ee3ccbb102a
- Context snapshot: `.omx/context/gsc-priority-upgrade-20260425T041755Z.md`

## Condensed Transcript

1. Q: If this upgrade can only move one result in the next 90 days, which matters most?
   A: Not generic traffic. Priority is traffic growth for customer-value inquiry/conversion keywords and pages.

2. Q: Which keyword/page types should V1 explicitly avoid chasing?
   A: Informational, tutorial, and science/popular-education style terms should not be the focus.

3. Q: If an informational-looking keyword historically assists RFQ/inquiry, how should V1 treat it?
   A: It can be included only as a supporting page for a conversion-driving page, not as a primary target.

4. Q: What should be V1's first-priority signal for identifying high-value keywords/pages?
   A: Initially answered as commercial page-intent signals such as pricing, manufacturer, supplier, wholesale, MOQ, custom, quote.

5. Q: If a query lacks explicit commercial modifiers but maps to a conversion-capable page, how should V1 judge it?
   A: Mixed scoring is better than relying only on keyword wording.

6. Q: If V1 uses mixed scoring, which signal should be the hard gate?
   A: No hard gate; use a weighted multi-signal model.

7. Q: For a high-impression, high-customer-value cluster, what should V1 do first by default?
   A: Dynamic decision engine; choose among page optimization, internal links, new content, and external links.

8. Q: What should be the decision unit?
   A: Topic/page cluster, not isolated keywords or pages.

## Pressure Pass

- Revisited assumption:
  - Earlier answer favored lexical/commercial intent as the primary signal.
  - After probing a case where the query lacks explicit commercial wording but maps to a conversion-capable page, the answer changed to weighted mixed scoring.
- Result:
  - The real objective is customer-value demand capture, not commercial keyword pattern matching by itself.

## Brownfield Findings

- `src/scheduler/jobs.py` already tries GSC first in `content_generation_job`, but mainly as a keyword source for new content.
- `src/integrations/gsc_client.py` exposes low-hanging fruit queries, declining pages, and raw search analytics.
- `src/agents/content_refresh.py`, `src/agents/internal_link.py`, `src/backlink/copilot.py`, and `src/agents/opportunity_scoring.py` exist, but they are not unified under a cluster-level action priority engine.
- Current system behavior is closer to `source precedence` than `asset/action prioritization`.

