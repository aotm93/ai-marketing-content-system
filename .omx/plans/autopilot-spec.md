# Autopilot Spec

Task: Fix ongoing production issues where generated article titles remain generic, repetitive, professionally weak, and mismatched to keywords.

Requirements:
- Stop generic awareness-style keyword templates from producing publishable topics.
- Prevent non-publishable fragments like `quality 100ml white pump explained` from entering title generation.
- Tighten website/category extraction so components like pumps/caps do not become article heads.
- Add stronger keyword/title mismatch blocking before publish.
- Introduce a more specific SERP role layer beyond broad lane classification.
- Propagate SERP role into title generation, planning, and content-writing prompts.
- Preserve existing lane-aware meta/CTA quality scoring and prior regressions.

Constraints:
- No new dependencies.
- Keep brownfield compatibility with scheduler/SEOContext pipeline.
- Verify with targeted regression tests.
