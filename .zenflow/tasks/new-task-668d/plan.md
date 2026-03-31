# Auto

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

Ask the user questions when anything is unclear or needs their input. This includes:
- Ambiguous or incomplete requirements
- Technical decisions that affect architecture or user experience
- Trade-offs that require business context

Do not make assumptions on important decisions — get clarification first.

---

## Workflow Steps

### [x] Step: Implementation
<!-- chat-id: 9bc65e7a-6370-47ef-8108-3c0114636ffd -->

- Completed: Added restart-safe rotating selection for startup seeds/content-intelligence topics with persisted anti-repeat history.
- Completed: Optimized title generation with duplicate-token cleanup and SEO-friendly length constraints.
- Completed: Diversified content generation prompts with deterministic editorial blueprints and added regression tests.

**Debug requests, questions, and investigations:** answer or investigate first. Do not create a plan upfront — the user needs an answer, not a plan. A plan may become relevant later once the investigation reveals what needs to change.

**For all other tasks**, before writing any code, assess the scope of the actual change (not the prompt length — a one-sentence prompt can describe a large feature). Scale your approach:

- **Trivial** (typo, config tweak, single obvious change): implement directly, no plan needed.
- **Small** (a few files, clear what to do): write 2–3 sentences in `plan.md` describing what and why, then implement. No substeps.
- **Medium** (multiple components, design decisions, edge cases): write a plan in `plan.md` with requirements, affected files, key decisions, verification. Break into 3–5 steps.
- **Large** (new feature, cross-cutting, unclear scope): gather requirements and write a technical spec first (`requirements.md`, `spec.md` in `{@artifacts_path}/`). Then write `plan.md` with concrete steps referencing the spec.

**Skip planning and implement directly when** the task is trivial, or the user explicitly asks to "just do it" / gives a clear direct instruction.

To reflect the actual purpose of the first step, you can rename it to something more relevant (e.g., Planning, Investigation). Do NOT remove meta information like comments for any step.

Rule of thumb for step size: each step = a coherent unit of work (component, endpoint, test suite). Not too granular (single function), not too broad (entire feature). Unit tests are part of each step, not separate.

Update `{@artifacts_path}/plan.md`.

### [x] Step: 审查计划是否能达到目标，并完善
<!-- chat-id: 8c7a548e-a5f9-45eb-98ff-db8ab5c69a5d -->
<!-- agent: {"type":"custom","agent":"CODEX","config":{"model":"gpt-5.4"}} -->

审查计划文档是否完整能达到我们的计划和目标要求，有问题进行修复。审查代码修改是否完整根据我们的计划完成，并且测试完整能达到我们的目标。

- 审查结论：实现方向与计划目标一致，已覆盖“重启/重新部署避免重复种子”“标题去重并收敛到 SEO 友好长度”“内容结构去模板化”三项目标。
- 阻塞问题：`src/scheduler/jobs.py` 中 rotation history 的持久化去重会保留旧顺序，重复命中的 seed/topic 不会刷新到最近位置，仍可能在后续重启后再次过早被选中，合并前应修复。
- 验证结果：在设置 `DATABASE_URL=sqlite:///test.db` 后执行 `python -m pytest tests/services/content/test_hook_optimizer_integration.py tests/unit/services/test_keyword_strategy_routing.py tests/agents/test_content_creator_integration.py`，11 项测试通过。

### [ ] Step: 合并代码到main
<!-- chat-id: 70ad2ade-10cd-4cc0-ac83-13fefbee7fe4 -->

测试没有问题合并完整代码到main, 并且提交推送
