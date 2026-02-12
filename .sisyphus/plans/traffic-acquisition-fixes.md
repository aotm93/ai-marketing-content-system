# Traffic Acquisition 三大核心功能实现

## TL;DR

> **Quick Summary**: 为 SEO Autopilot 实现三大缺失的流量获取功能：真实关键词研究（DataForSEO API）、真实外链发现（DataForSEO Backlinks API）、邮件线索捕获（Resend API）。替换所有硬编码假数据为真实 API 调用。
> 
> **Deliverables**:
> - DataForSEO 关键词研究客户端 + API 端点 + 策略层集成
> - DataForSEO 外链发现客户端 + 模型 + Copilot 重写 + Outreach 发送器
> - Resend 邮件客户端 + 订阅者模型 + 序列引擎 + API 端点 + WordPress 短代码
> - 3 个新定时任务 + 集成测试 + 数据库迁移 + 部署文档更新
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 → Task 2 → Task 3 | Task 4 → Task 5 → Task 6 | Task 7 → Task 8 → Task 9

---

## Context

### Original Request
为 SEO Autopilot 平台实现三大缺失的流量获取功能，替换所有占位符/假数据为真实 API 集成。

### Interview Summary
**Key Discussions**:
- DataForSEO 同时用于关键词和外链（项目已有框架）
- Resend 用于所有邮件发送（用户明确选择）
- Outreach 邮件需要管理员手动确认后才发送（非自动发送）
- 邮件序列仅支持线性流程（无条件分支）
- Subscribe/Unsubscribe 端点公开（无需认证）
- Admin 端点使用现有 `src/core/auth.py` 的 `get_current_admin`
- 每日 Outreach 限制：50 封
- MVP 阶段无 CAPTCHA、无 Double Opt-in

**Research Findings**:
- `src/integrations/keyword_client.py:89-92` — `_fetch_dataforseo()` 是空的 `pass`
- `src/backlink/copilot.py:127-147, 181-201` — `_generate_sample_*` 返回硬编码假数据
- `src/models/keyword.py:29-30` — `search_volume` 和 `difficulty` 列存在但始终为 NULL
- `src/config/settings.py:48-51` — 已有 keyword API 配置字段
- `src/scheduler/jobs.py` — 4 层关键词回退：GSC → Content-Aware → Keyword API → Fallback
- `src/models/base.py` — `Base = declarative_base()` + `TimestampMixin`
- `src/models/__init__.py` — 新模型必须在此注册
- `alembic.ini` — `script_location = migrations`，但 migrations/ 目录尚未创建
- 无测试基础设施（无 tests/ 目录）
- 无 `static/` JS 文件、无 `wp-content/` 目录、无 `src/email/` 目录

---

## Work Objectives

### Core Objective
将 SEO Autopilot 从 65% 完成度提升至 ~85%，通过实现真实的关键词研究、外链发现和邮件线索捕获功能。

### Concrete Deliverables
- 完整的 DataForSEO 关键词 API 客户端
- 完整的 DataForSEO 外链 API 客户端
- Resend 邮件客户端 + 序列引擎
- 4 个新 SQLAlchemy 模型 + Alembic 迁移
- 3 个新 FastAPI 路由模块
- 3 个新定时任务
- WordPress 订阅短代码
- 集成测试套件

### Definition of Done
- [x] `_fetch_dataforseo()` 返回真实关键词数据（非空 pass）
- [x] `_generate_sample_mentions()` 和 `_generate_sample_competitors()` 被真实 API 调用替换
- [x] 邮件订阅端点可接收和存储订阅者
- [x] 所有新端点在 `/docs` 中可见
- [x] Alembic 迁移可成功执行

### Must Have
- DataForSEO HTTP Basic Auth（base64 编码 username:password）
- 关键词按搜索量排序
- 外链去重逻辑
- Outreach 50/天限制
- 管理员确认后才发送 outreach
- 邮件退订功能

### Must NOT Have (Guardrails)
- 不要自动发送 outreach 邮件（必须管理员确认）
- 不要实现条件分支邮件序列
- 不要添加 CAPTCHA
- 不要实现 Double Opt-in
- 不要修改现有 GSC 集成代码
- 不要修改现有 WordPress 发布逻辑
- 不要过度抽象——保持与现有代码风格一致

---

## Verification Strategy

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: YES (tests-after, Task 10)
- **Framework**: pytest (与项目 Python 技术栈一致)

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

每个任务都包含 Agent-Executed QA Scenarios 作为主要验证方法。
验证工具：Bash (curl/python) 用于 API 验证，Bash (python import) 用于模块验证。

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — no dependencies):
├── Task 1: DataForSEO 关键词客户端实现
├── Task 4: 外链模型 + DataForSEO 外链客户端 + 迁移
└── Task 7: Resend 客户端 + 邮件模型 + 迁移 + Settings 更新

Wave 2 (After Wave 1):
├── Task 2: 关键词策略层集成真实数据 (depends: 1)
├── Task 3: Keywords API 端点 (depends: 1)
├── Task 5: 重写 Backlink Copilot (depends: 4)
└── Task 8: 序列引擎 + Email API 端点 (depends: 7)

Wave 3 (After Wave 2):
├── Task 6: Outreach 发送器 (depends: 5)
├── Task 9: 订阅表单 JS + WordPress 短代码 (depends: 8)
├── Task 10: 定时任务 + 集成测试 (depends: 2, 5, 8)
└── Task 11: 迁移合并 + .env.example + DEPLOYMENT.md (depends: all)
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3 | 4, 7 |
| 4 | None | 5 | 1, 7 |
| 7 | None | 8 | 1, 4 |
| 2 | 1 | 10 | 3, 5, 8 |
| 3 | 1 | None | 2, 5, 8 |
| 5 | 4 | 6, 10 | 2, 3, 8 |
| 8 | 7 | 9, 10 | 2, 3, 5 |
| 6 | 5 | 11 | 9, 10 |
| 9 | 8 | 11 | 6, 10 |
| 10 | 2, 5, 8 | 11 | 6, 9 |
| 11 | All | None | None (final) |

---

## TODOs

### Wave 1 — 基础客户端 + 模型（并行启动）

- [x] 1. DataForSEO 关键词客户端实现

  **What to do**:
  - 完善 `src/integrations/keyword_client.py` 中的 `_fetch_dataforseo()` 方法
  - 实现 DataForSEO HTTP Basic Auth：base64 编码 `username:password`
  - 调用 DataForSEO 三个端点：
    - `POST /v3/dataforseo_labs/google/keyword_suggestions/live` — 关键词建议
    - `POST /v3/dataforseo_labs/google/related_keywords/live` — 相关关键词
    - `POST /v3/dataforseo_labs/google/bulk_keyword_difficulty/live` — 批量难度
  - 解析响应，映射到现有 `KeywordOpportunity` dataclass（keyword, volume, difficulty, cpc, intent）
  - 添加错误处理：API 限流（429）、认证失败（401）、超时
  - 添加结果缓存（简单的内存 dict + TTL，避免重复调用）
  - 更新 `get_easy_wins()` 确保与新数据兼容

  **Must NOT do**:
  - 不要修改 `_fetch_generic()` 方法
  - 不要修改 `KeywordOpportunity` dataclass 结构
  - 不要添加新的配置字段（已有 keyword_api_key, keyword_api_username 等）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: API 集成任务，需要理解 DataForSEO API 文档和 HTTP 认证模式
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: 无浏览器交互需求

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 4, 7)
  - **Blocks**: Tasks 2, 3
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `src/integrations/keyword_client.py:62-87` — `_fetch_generic()` 方法，展示了 httpx 异步请求模式和响应解析
  - `src/integrations/keyword_client.py:33-37` — 构造函数，展示了 provider/api_key/username/base_url 的初始化
  - `src/integrations/keyword_client.py:19-26` — `KeywordOpportunity` dataclass，目标返回类型

  **API/Type References**:
  - `src/config/settings.py:48-51` — `keyword_api_provider`, `keyword_api_key`, `keyword_api_username`, `keyword_api_base_url` 配置字段

  **External References**:
  - DataForSEO API 文档: `https://docs.dataforseo.com/v3/dataforseo_labs/google/keyword_suggestions/live/` — keyword_suggestions 端点
  - DataForSEO 认证: `https://docs.dataforseo.com/v3/auth/` — HTTP Basic Auth (base64 of login:password)

  **Acceptance Criteria**:

  - [ ] `_fetch_dataforseo()` 不再是空 `pass`，包含完整实现
  - [ ] 使用 HTTP Basic Auth（base64 编码）
  - [ ] 返回 `List[KeywordOpportunity]`，每个包含 keyword, volume, difficulty, cpc
  - [ ] 处理 401/429/超时错误，返回空列表并记录日志
  - [ ] `get_easy_wins()` 可正常调用并过滤结果

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: 模块可正常导入且无语法错误
    Tool: Bash (python)
    Steps:
      1. python -c "from src.integrations.keyword_client import KeywordClient; kc = KeywordClient(provider='dataforseo', api_key='test', api_username='test'); print('OK')"
      2. Assert: stdout contains "OK"
      3. Assert: exit code 0
    Expected Result: 模块导入成功
    Evidence: stdout 输出

  Scenario: 无 API Key 时优雅降级
    Tool: Bash (python)
    Steps:
      1. python -c "import asyncio; from src.integrations.keyword_client import KeywordClient; kc = KeywordClient(provider='dataforseo'); result = asyncio.run(kc.get_keyword_suggestions('test')); print(f'Results: {len(result)}')"
      2. Assert: stdout contains "Results: 0"
      3. Assert: exit code 0
    Expected Result: 无 key 时返回空列表，不抛异常
    Evidence: stdout 输出
  ```

  **Commit**: YES
  - Message: `feat(keywords): implement DataForSEO keyword research client`
  - Files: `src/integrations/keyword_client.py`
  - Pre-commit: `python -c "from src.integrations.keyword_client import KeywordClient"`

- [x] 4. 外链模型 + DataForSEO 外链客户端 + 迁移

  **What to do**:
  - 新建 `src/models/backlink.py` — `BacklinkOpportunityModel(Base, TimestampMixin)`:
    - id, target_url, target_domain, opportunity_type (enum), domain_authority, page_authority,
      traffic_estimate, relevance_score, contact_email, contact_name, outreach_status (enum),
      brand_mention, anchor_text_suggestion, suggested_link_url, notes, discovered_at
    - 添加索引：target_domain, outreach_status, relevance_score
    - 添加唯一约束：(target_url, opportunity_type) 防止重复
  - 在 `src/models/__init__.py` 注册新模型
  - 新建 `src/integrations/dataforseo_backlinks.py` — `DataForSEOBacklinksClient`:
    - `__init__(api_key, api_username)` — 使用 settings 中的 keyword_api_key/username
    - `async get_referring_domains(target_domain, limit=100)` — POST `/v3/backlinks/referring_domains/live`
    - `async get_backlinks_for_domain(target_domain, limit=100)` — POST `/v3/backlinks/backlinks/live`
    - `async check_backlink_exists(source_url, target_url)` — POST `/v3/backlinks/backlinks/live` with filter
    - HTTP Basic Auth (同 Task 1 模式)
    - 错误处理 + 日志
  - 创建 Alembic 迁移：先确保 `migrations/` 目录结构存在（env.py, script.py.mako, versions/），然后 `alembic revision --autogenerate -m "add_backlink_opportunities"`

  **Must NOT do**:
  - 不要修改现有 `src/backlink/copilot.py`（Task 5 负责）
  - 不要修改现有模型文件
  - 不要在迁移中包含邮件表（Task 7 单独处理）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 涉及 SQLAlchemy 模型设计 + API 客户端 + Alembic 迁移，多文件协调
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 7)
  - **Blocks**: Task 5
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `src/models/indexing_status.py:1-87` — SQLAlchemy 模型完整示例（Base, TimestampMixin, Column 定义, __table_args__, to_dict）
  - `src/models/base.py:1-12` — Base 和 TimestampMixin 定义
  - `src/models/__init__.py:1-22` — 模型注册模式（import + __all__）
  - `src/integrations/keyword_client.py:62-87` — httpx 异步 API 调用模式

  **API/Type References**:
  - `src/backlink/copilot.py:21-38` — `OpportunityType` 和 `OutreachStatus` 枚举（模型应复用这些值）
  - `src/backlink/copilot.py:42-81` — `BacklinkOpportunity` dataclass（模型字段参考）
  - `src/config/settings.py:48-51` — API 认证配置

  **Documentation References**:
  - `alembic.ini:5` — `script_location = migrations`（迁移目录路径）

  **External References**:
  - DataForSEO Backlinks API: `https://docs.dataforseo.com/v3/backlinks/referring_domains/live/`
  - DataForSEO Backlinks: `https://docs.dataforseo.com/v3/backlinks/backlinks/live/`

  **Acceptance Criteria**:

  - [ ] `src/models/backlink.py` 存在且包含 `BacklinkOpportunityModel` 类
  - [ ] 模型在 `src/models/__init__.py` 中注册
  - [ ] `src/integrations/dataforseo_backlinks.py` 存在且包含三个 async 方法
  - [ ] Alembic 迁移文件生成成功

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: 外链模型可正常导入
    Tool: Bash (python)
    Steps:
      1. python -c "from src.models.backlink import BacklinkOpportunityModel; print(BacklinkOpportunityModel.__tablename__)"
      2. Assert: stdout contains table name
      3. Assert: exit code 0
    Expected Result: 模型类可导入

  Scenario: 外链客户端可正常导入
    Tool: Bash (python)
    Steps:
      1. python -c "from src.integrations.dataforseo_backlinks import DataForSEOBacklinksClient; print('OK')"
      2. Assert: stdout contains "OK"
    Expected Result: 客户端类可导入

  Scenario: 迁移文件存在
    Tool: Bash
    Steps:
      1. ls migrations/versions/*.py
      2. Assert: 至少一个 .py 文件存在
    Expected Result: 迁移文件已生成
  ```

  **Commit**: YES
  - Message: `feat(backlinks): add backlink model, DataForSEO backlinks client, and migration`
  - Files: `src/models/backlink.py`, `src/integrations/dataforseo_backlinks.py`, `src/models/__init__.py`, `migrations/`
  - Pre-commit: `python -c "from src.models.backlink import BacklinkOpportunityModel"`

- [x] 7. Resend 客户端 + 邮件模型 + 迁移 + Settings 更新

  **What to do**:
  - 新建 `src/email/__init__.py`（空文件）
  - 新建 `src/email/resend_client.py` — `ResendClient`:
    - `__init__(api_key)` — 从 settings 读取
    - `async send_email(to, subject, html_body, from_email=None)` — POST `https://api.resend.com/emails`
    - `async send_batch(emails: List[dict])` — POST `https://api.resend.com/emails/batch`
    - `async create_contact(email, first_name=None, audience_id=None)` — POST `https://api.resend.com/contacts`
    - 使用 httpx，Bearer token 认证
    - 错误处理 + 日志
  - 新建 `src/models/email.py` — `EmailSubscriber(Base, TimestampMixin)`:
    - id, email (unique), first_name, source, subscribed_at, unsubscribed_at, is_active
    - 索引：email, is_active
  - 新建 `src/models/email_sequence.py`:
    - `EmailSequence(Base, TimestampMixin)` — id, name, description, is_active
    - `EmailSequenceStep(Base, TimestampMixin)` — id, sequence_id (FK), step_order, subject, html_body, delay_hours
  - 新建 `src/models/email_enrollment.py`:
    - `EmailEnrollment(Base, TimestampMixin)` — id, subscriber_id (FK), sequence_id (FK), current_step, status (active/completed/cancelled), enrolled_at, last_step_sent_at, next_step_due_at
  - 在 `src/models/__init__.py` 注册所有新邮件模型
  - 在 `src/config/settings.py` 添加：`resend_api_key: Optional[str] = None` 和 `resend_from_email: Optional[str] = None`
  - 创建 Alembic 迁移：`alembic revision --autogenerate -m "add_email_tables"`

  **Must NOT do**:
  - 不要实现序列引擎逻辑（Task 8 负责）
  - 不要创建 API 端点（Task 8 负责）
  - 不要在迁移中包含外链表（Task 4 单独处理）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 多文件创建（5 个新文件 + 2 个修改），涉及模型设计和 API 客户端
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 4)
  - **Blocks**: Task 8
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `src/models/indexing_status.py:1-87` — SQLAlchemy 模型完整示例
  - `src/models/base.py:1-12` — Base + TimestampMixin
  - `src/models/__init__.py:1-22` — 模型注册模式
  - `src/integrations/keyword_client.py:62-87` — httpx 异步请求模式
  - `src/config/settings.py:47-51` — 配置字段添加位置（在 Keyword Research 区块后）

  **External References**:
  - Resend API: `https://resend.com/docs/api-reference/emails/send-email`
  - Resend Batch: `https://resend.com/docs/api-reference/emails/send-batch-emails`
  - Resend Contacts: `https://resend.com/docs/api-reference/contacts/create-contact`

  **Acceptance Criteria**:

  - [ ] `src/email/resend_client.py` 存在且包含 `ResendClient` 类
  - [ ] `src/models/email.py` 包含 `EmailSubscriber` 模型
  - [ ] `src/models/email_sequence.py` 包含 `EmailSequence` 和 `EmailSequenceStep`
  - [ ] `src/models/email_enrollment.py` 包含 `EmailEnrollment`
  - [ ] `src/config/settings.py` 包含 `resend_api_key` 和 `resend_from_email`
  - [ ] 所有新模型在 `__init__.py` 中注册
  - [ ] Alembic 迁移文件生成成功

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Resend 客户端可导入
    Tool: Bash (python)
    Steps:
      1. python -c "from src.email.resend_client import ResendClient; print('OK')"
      2. Assert: exit code 0
    Expected Result: 客户端类可导入

  Scenario: 邮件模型可导入
    Tool: Bash (python)
    Steps:
      1. python -c "from src.models.email import EmailSubscriber; from src.models.email_sequence import EmailSequence, EmailSequenceStep; from src.models.email_enrollment import EmailEnrollment; print('OK')"
      2. Assert: exit code 0
    Expected Result: 所有模型类可导入

  Scenario: Settings 包含新字段
    Tool: Bash (python)
    Steps:
      1. python -c "from src.config.settings import Settings; s = Settings.model_fields; assert 'resend_api_key' in s; assert 'resend_from_email' in s; print('OK')"
      2. Assert: exit code 0
    Expected Result: 新配置字段存在
  ```

  **Commit**: YES
  - Message: `feat(email): add Resend client, email models, and migration`
  - Files: `src/email/__init__.py`, `src/email/resend_client.py`, `src/models/email.py`, `src/models/email_sequence.py`, `src/models/email_enrollment.py`, `src/models/__init__.py`, `src/config/settings.py`, `migrations/`
  - Pre-commit: `python -c "from src.email.resend_client import ResendClient"`

### Wave 2 — 集成层 + API 端点（依赖 Wave 1）

- [x] 2. 关键词策略层集成真实数据

  **What to do**:
  - 修改 `src/services/keyword_strategy.py` 的 `generate_keyword_pool()`:
    - 在生成模板关键词后，调用 `KeywordClient` 获取真实搜索量和难度
    - 用真实数据丰富 `KeywordCandidate`（将 difficulty_estimate 从 "low/medium/high" 映射为实际数值）
    - 按搜索量降序排序结果
  - 修改 `src/scheduler/jobs.py` Layer 1.2（Keyword API 层）:
    - 确保从 `KeywordClient` 获取的关键词按 `volume` 降序排序
    - 将真实 volume/difficulty 写入 `Keyword` 模型的 `search_volume` 和 `difficulty` 列
  - 添加 `KeywordCandidate` 新可选字段：`search_volume: Optional[int] = None`, `difficulty_score: Optional[int] = None`

  **Must NOT do**:
  - 不要修改 GSC 层（Layer 1.1）逻辑
  - 不要修改 Content-Aware 层（Layer 1.3）的模板生成逻辑
  - 不要删除 Fallback 层（Layer 1.4）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要理解多层关键词回退架构并精确修改
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 5, 8)
  - **Blocks**: Task 10
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `src/services/keyword_strategy.py:69-114` — `generate_keyword_pool()` 方法，需要在此集成 API 数据
  - `src/services/keyword_strategy.py:36-46` — `KeywordCandidate` dataclass，需要添加可选字段
  - `src/integrations/keyword_client.py:42-60` — `get_keyword_suggestions()` 调用方式
  - `src/integrations/keyword_client.py:94-108` — `get_easy_wins()` 过滤逻辑

  **API/Type References**:
  - `src/models/keyword.py:23-33` — `Keyword` 模型，`search_volume` 和 `difficulty` 列需要被填充

  **Documentation References**:
  - `src/scheduler/jobs.py` — 4 层关键词回退架构（需要找到 Layer 1.2 的具体位置）

  **Acceptance Criteria**:

  - [ ] `generate_keyword_pool()` 返回的关键词包含真实搜索量数据（当 API 可用时）
  - [ ] 关键词按搜索量降序排序
  - [ ] `Keyword` 模型的 `search_volume` 和 `difficulty` 列被填充（非 NULL）
  - [ ] 无 API key 时优雅降级到模板关键词

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: KeywordCandidate 支持新字段
    Tool: Bash (python)
    Steps:
      1. python -c "from src.services.keyword_strategy import KeywordCandidate; kc = KeywordCandidate(keyword='test', intent='informational', journey_stage='awareness', category='test', difficulty_estimate='low', is_long_tail=True, semantic_group='test', search_volume=1000, difficulty_score=25); print(f'vol={kc.search_volume}')"
      2. Assert: stdout contains "vol=1000"
    Expected Result: 新字段可用

  Scenario: 模块无语法错误
    Tool: Bash (python)
    Steps:
      1. python -c "from src.services.keyword_strategy import ContentAwareKeywordGenerator; print('OK')"
      2. Assert: exit code 0
    Expected Result: 模块可正常导入
  ```

  **Commit**: YES
  - Message: `feat(keywords): enrich keyword strategy with real search volume data`
  - Files: `src/services/keyword_strategy.py`, `src/scheduler/jobs.py`
  - Pre-commit: `python -c "from src.services.keyword_strategy import ContentAwareKeywordGenerator"`

- [x] 3. Keywords API 端点

  **What to do**:
  - 新建 `src/api/keywords.py` — `keyword_router`:
    - `GET /api/v1/keywords/suggestions?seed={keyword}&limit=10` — 返回关键词建议（调用 KeywordClient）
    - `GET /api/v1/keywords/difficulty?keywords=kw1,kw2` — 返回批量难度
    - `GET /api/v1/keywords/pool?limit=50` — 返回当前关键词池（从 DB 读取 Keyword 模型）
    - `POST /api/v1/keywords/refresh` — 触发关键词池刷新（调用 generate_keyword_pool + API enrichment）
    - 所有端点需要 admin 认证（`Depends(get_current_admin)`）
  - 在 `src/api/main.py` 注册路由：`app.include_router(keyword_router)`

  **Must NOT do**:
  - 不要创建公开端点（所有端点需要认证）
  - 不要修改现有路由

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 标准 FastAPI 路由创建，模式已有大量参考
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 2, 5, 8)
  - **Blocks**: None
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `src/api/main.py:181-192` — 路由注册模式（import + include_router）
  - `src/api/gsc.py` — FastAPI 路由示例（Depends, Session, 响应格式）
  - `src/core/auth.py:64-93` — `get_current_admin` 依赖注入

  **API/Type References**:
  - `src/integrations/keyword_client.py:28-109` — KeywordClient 类（调用方式）
  - `src/models/keyword.py:23-33` — Keyword 模型（DB 查询）
  - `src/core/database.py:28-34` — `get_db` 依赖

  **Acceptance Criteria**:

  - [ ] `src/api/keywords.py` 存在且包含 4 个端点
  - [ ] 路由在 `src/api/main.py` 中注册
  - [ ] 所有端点需要 admin 认证

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: 路由模块可导入
    Tool: Bash (python)
    Steps:
      1. python -c "from src.api.keywords import keyword_router; print(f'Routes: {len(keyword_router.routes)}')"
      2. Assert: stdout contains "Routes: 4"
    Expected Result: 4 个路由已注册

  Scenario: 路由在 main.py 中注册
    Tool: Bash (grep)
    Steps:
      1. grep "keyword_router" src/api/main.py
      2. Assert: 包含 include_router
    Expected Result: 路由已注册
  ```

  **Commit**: YES
  - Message: `feat(keywords): add keyword research API endpoints`
  - Files: `src/api/keywords.py`, `src/api/main.py`
  - Pre-commit: `python -c "from src.api.keywords import keyword_router"`

- [x] 5. 重写 Backlink Copilot 使用真实数据

  **What to do**:
  - 重写 `src/backlink/copilot.py` 中的 `BacklinkDiscoveryEngine`:
    - 替换 `_generate_sample_mentions()` — 调用 `DataForSEOBacklinksClient.get_referring_domains()` 获取真实提及
    - 替换 `_generate_sample_resource_pages()` — 调用 `DataForSEOBacklinksClient.get_backlinks_for_domain()` 获取真实资源页
    - 在 `__init__` 中接受 `DataForSEOBacklinksClient` 实例和 DB session
    - `find_unlinked_mentions()` — 用真实 API 数据替换假数据，过滤已链接的域名
    - `find_resource_pages()` — 用真实 API 数据替换假数据
    - 将发现的机会持久化到 `BacklinkOpportunityModel`
    - 添加去重逻辑：检查 (target_url, opportunity_type) 是否已存在
  - 保留 `score_opportunity()` 和 `get_top_opportunities()` 逻辑不变
  - 保留 `OutreachGenerator` 和 `OutreachTracker` 类不变

  **Must NOT do**:
  - 不要修改 `score_opportunity()` 评分算法
  - 不要修改 `OutreachGenerator` 模板
  - 不要修改 `OutreachTracker` 类
  - 不要删除 `BacklinkOpportunity` dataclass（保持向后兼容）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要精确替换假数据方法同时保持现有接口兼容
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 2, 3, 8)
  - **Blocks**: Tasks 6, 10
  - **Blocked By**: Task 4

  **References**:

  **Pattern References**:
  - `src/backlink/copilot.py:84-147` — `BacklinkDiscoveryEngine` 类和 `_generate_sample_mentions()`（要替换的代码）
  - `src/backlink/copilot.py:149-201` — `find_resource_pages()` 和 `_generate_sample_resource_pages()`（要替换的代码）
  - `src/backlink/copilot.py:203-256` — `score_opportunity()` 和 `get_top_opportunities()`（保持不变）
  - `src/backlink/copilot.py:42-81` — `BacklinkOpportunity` dataclass（保持不变，用于内存表示）

  **API/Type References**:
  - `src/models/backlink.py` — `BacklinkOpportunityModel`（Task 4 创建，用于持久化）
  - `src/integrations/dataforseo_backlinks.py` — `DataForSEOBacklinksClient`（Task 4 创建，用于 API 调用）

  **Acceptance Criteria**:

  - [ ] `_generate_sample_mentions()` 被替换为真实 API 调用
  - [ ] `_generate_sample_resource_pages()` 被替换为真实 API 调用
  - [ ] 发现的机会持久化到 DB
  - [ ] 去重逻辑：相同 (target_url, opportunity_type) 不重复插入
  - [ ] 无 API key 时优雅降级（返回空列表）

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Copilot 模块可正常导入
    Tool: Bash (python)
    Steps:
      1. python -c "from src.backlink.copilot import BacklinkDiscoveryEngine; print('OK')"
      2. Assert: exit code 0
    Expected Result: 模块导入成功

  Scenario: 不再包含硬编码假数据
    Tool: Bash (grep)
    Steps:
      1. grep -c "example-blog" src/backlink/copilot.py
      2. Assert: count is 0
      3. grep -c "resource-site" src/backlink/copilot.py
      4. Assert: count is 0
    Expected Result: 所有假数据已移除
  ```

  **Commit**: YES
  - Message: `feat(backlinks): replace sample data with real DataForSEO backlink discovery`
  - Files: `src/backlink/copilot.py`
  - Pre-commit: `python -c "from src.backlink.copilot import BacklinkDiscoveryEngine"`

- [x] 8. 序列引擎 + Email API 端点

  **What to do**:
  - 新建 `src/email/sequence_engine.py` — `SequenceEngine`:
    - `__init__(db: Session, resend_client: ResendClient)`
    - `async enroll(subscriber_id, sequence_id)` — 创建 EmailEnrollment，设置 next_step_due_at
    - `async process_pending_steps()` — 查询所有 next_step_due_at <= now 的 enrollment，发送邮件，更新 current_step
    - `async get_progress(enrollment_id)` — 返回进度信息
    - `async cancel_enrollment(enrollment_id)` — 取消订阅序列
    - 线性序列：按 step_order 顺序发送，delay_hours 控制间隔
  - 新建 `src/api/email.py` — `email_router`:
    - 公开端点（无认证）：
      - `POST /api/v1/email/subscribe` — 接收 email + first_name，创建 EmailSubscriber
      - `POST /api/v1/email/unsubscribe` — 接收 email，标记 is_active=False
    - Admin 端点（需要 `get_current_admin`）：
      - `GET /api/v1/email/subscribers?page=1&limit=20` — 分页列表
      - `GET /api/v1/email/sequences` — 列出所有序列
      - `POST /api/v1/email/sequences` — 创建序列
      - `POST /api/v1/email/broadcast` — 群发邮件给所有活跃订阅者
  - 在 `src/api/main.py` 注册 `email_router`

  **Must NOT do**:
  - 不要实现条件分支序列
  - 不要添加 CAPTCHA
  - 不要实现 Double Opt-in
  - 不要在 subscribe 端点添加认证

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 涉及业务逻辑（序列引擎）+ API 端点设计，多文件协调
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 2, 3, 5)
  - **Blocks**: Tasks 9, 10
  - **Blocked By**: Task 7

  **References**:

  **Pattern References**:
  - `src/api/main.py:181-192` — 路由注册模式
  - `src/api/gsc.py` — FastAPI 路由示例
  - `src/core/auth.py:64-93` — `get_current_admin` 依赖
  - `src/core/database.py:28-34` — `get_db` 依赖

  **API/Type References**:
  - `src/email/resend_client.py` — ResendClient（Task 7 创建）
  - `src/models/email.py` — EmailSubscriber（Task 7 创建）
  - `src/models/email_sequence.py` — EmailSequence, EmailSequenceStep（Task 7 创建）
  - `src/models/email_enrollment.py` — EmailEnrollment（Task 7 创建）

  **Acceptance Criteria**:

  - [ ] `src/email/sequence_engine.py` 存在且包含 SequenceEngine 类
  - [ ] `src/api/email.py` 存在且包含 6 个端点
  - [ ] subscribe/unsubscribe 无需认证
  - [ ] admin 端点需要 get_current_admin
  - [ ] 路由在 main.py 中注册

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: 序列引擎可导入
    Tool: Bash (python)
    Steps:
      1. python -c "from src.email.sequence_engine import SequenceEngine; print('OK')"
      2. Assert: exit code 0
    Expected Result: 引擎类可导入

  Scenario: Email 路由可导入
    Tool: Bash (python)
    Steps:
      1. python -c "from src.api.email import email_router; print(f'Routes: {len(email_router.routes)}')"
      2. Assert: stdout contains "Routes: 6"
    Expected Result: 6 个路由已注册
  ```

  **Commit**: YES
  - Message: `feat(email): add sequence engine and email API endpoints`
  - Files: `src/email/sequence_engine.py`, `src/api/email.py`, `src/api/main.py`
  - Pre-commit: `python -c "from src.email.sequence_engine import SequenceEngine"`

### Wave 3 — 集成 + 收尾（依赖 Wave 2）

- [x] 6. Outreach 发送器（Resend + 50/天限制）

  **What to do**:
  - 新建 `src/backlink/outreach_sender.py` — `OutreachSender`:
    - `__init__(db: Session, resend_client: ResendClient)`
    - `async send_outreach(opportunity_id, email_content, admin_approved=False)`:
      - 检查 `admin_approved` 必须为 True，否则拒绝发送
      - 检查今日已发送数量 < 50，否则拒绝
      - 调用 `resend_client.send_email()` 发送
      - 更新 `BacklinkOpportunityModel.outreach_status` 为 SENT
      - 记录发送时间
    - `async get_pending_outreach()` — 返回待发送列表（status=DRAFTED）
    - `async approve_and_send(opportunity_id)` — 管理员确认后发送
    - `get_daily_send_count()` — 返回今日已发送数量
    - `DAILY_LIMIT = 50` 常量

  **Must NOT do**:
  - 不要实现自动发送（必须 admin_approved=True）
  - 不要超过 50/天限制
  - 不要修改 OutreachGenerator 模板类

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文件创建，逻辑清晰
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 10)
  - **Blocks**: Task 11
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - `src/backlink/copilot.py:259-318` — `OutreachGenerator` 类（生成邮件内容）
  - `src/backlink/copilot.py:378-455` — `OutreachTracker` 类（状态追踪模式）

  **API/Type References**:
  - `src/email/resend_client.py` — ResendClient（Task 7 创建）
  - `src/models/backlink.py` — BacklinkOpportunityModel（Task 4 创建）

  **Acceptance Criteria**:

  - [ ] `src/backlink/outreach_sender.py` 存在
  - [ ] 未经 admin 确认时拒绝发送
  - [ ] 超过 50/天时拒绝发送
  - [ ] 发送后更新 outreach_status

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: OutreachSender 可导入
    Tool: Bash (python)
    Steps:
      1. python -c "from src.backlink.outreach_sender import OutreachSender; print(f'Limit: {OutreachSender.DAILY_LIMIT}')"
      2. Assert: stdout contains "Limit: 50"
    Expected Result: 类可导入且限制为 50
  ```

  **Commit**: YES
  - Message: `feat(backlinks): add outreach sender with daily limit and admin approval`
  - Files: `src/backlink/outreach_sender.py`
  - Pre-commit: `python -c "from src.backlink.outreach_sender import OutreachSender"`

- [x] 9. 订阅表单 JS + WordPress 短代码

  **What to do**:
  - 新建 `static/js/subscribe.js` — 纯 vanilla JS 订阅表单：
    - 渲染表单（email input + optional name + submit button）
    - POST 到 `/api/v1/email/subscribe`
    - 显示成功/错误消息
    - 无外部依赖，无 CAPTCHA
    - 支持自定义 API base URL（通过 data attribute）
  - 新建 `wp-content/mu-plugins/seo-autopilot-subscribe.php`:
    - 注册 `[seo_subscribe]` shortcode
    - Shortcode 输出：加载 subscribe.js + 渲染容器 div
    - 支持属性：`api_url`（后端地址）
    - 在 WordPress 页面/文章中使用 `[seo_subscribe api_url="https://your-api.com"]`

  **Must NOT do**:
  - 不要使用 React/Vue 等框架
  - 不要添加 CAPTCHA
  - 不要实现 Double Opt-in

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 两个小文件，逻辑简单
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 6, 10)
  - **Blocks**: Task 11
  - **Blocked By**: Task 8

  **References**:

  **API/Type References**:
  - `src/api/email.py` — subscribe 端点（Task 8 创建，POST /api/v1/email/subscribe）

  **Documentation References**:
  - `wp-content/mu-plugins/` — WordPress MU-Plugin 目录约定（自动加载）

  **Acceptance Criteria**:

  - [ ] `static/js/subscribe.js` 存在且为纯 vanilla JS
  - [ ] `wp-content/mu-plugins/seo-autopilot-subscribe.php` 存在
  - [ ] PHP 文件注册 `[seo_subscribe]` shortcode
  - [ ] JS 文件 POST 到正确端点

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: JS 文件语法正确
    Tool: Bash
    Steps:
      1. node -e "require('fs').readFileSync('static/js/subscribe.js', 'utf8')" 
      2. Assert: exit code 0
    Expected Result: 文件可读取无语法错误

  Scenario: PHP 文件包含 shortcode 注册
    Tool: Bash (grep)
    Steps:
      1. grep "add_shortcode" wp-content/mu-plugins/seo-autopilot-subscribe.php
      2. Assert: 包含 "seo_subscribe"
    Expected Result: Shortcode 已注册
  ```

  **Commit**: YES
  - Message: `feat(email): add subscribe form JS and WordPress shortcode`
  - Files: `static/js/subscribe.js`, `wp-content/mu-plugins/seo-autopilot-subscribe.php`

- [x] 10. 定时任务 + 集成测试

  **What to do**:
  - 在 `src/scheduler/jobs.py` 添加 3 个新定时任务：
    - `weekly_backlink_scan()` — 每周一次，调用 BacklinkDiscoveryEngine 扫描新外链机会
    - `hourly_email_sequence_processor()` — 每小时一次，调用 SequenceEngine.process_pending_steps()
    - `weekly_keyword_refresh()` — 每周一次，调用 KeywordClient 刷新关键词池
  - 在 `JOB_REGISTRY` 中注册新任务
  - 新建 `tests/` 目录结构：
    - `tests/__init__.py`
    - `tests/conftest.py` — pytest fixtures（SQLite 内存 DB、mock settings）
    - `tests/integration/__init__.py`
    - `tests/integration/test_traffic_acquisition.py`:
      - `test_keyword_client_init` — KeywordClient 初始化
      - `test_keyword_client_no_key_returns_empty` — 无 key 返回空
      - `test_backlink_model_creation` — BacklinkOpportunityModel CRUD
      - `test_email_subscriber_model` — EmailSubscriber CRUD
      - `test_resend_client_init` — ResendClient 初始化
      - `test_sequence_engine_enroll` — 序列注册
      - `test_outreach_sender_daily_limit` — 50/天限制

  **Must NOT do**:
  - 不要修改现有定时任务
  - 不要使用真实 API key 做测试（全部 mock）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 涉及定时任务注册 + 完整测试套件创建
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 6, 9)
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 2, 5, 8

  **References**:

  **Pattern References**:
  - `src/scheduler/jobs.py:1154-1168` — `JOB_REGISTRY` 和 `register_all_jobs()` 模式
  - `src/scheduler/jobs.py:1218-1226` — `INDEX_CHECK_JOB` 独立任务注册模式（cron trigger）
  - `src/scheduler/jobs.py:1171-1216` — `scheduled_index_status_check()` 完整任务示例

  **API/Type References**:
  - `src/backlink/copilot.py` — BacklinkDiscoveryEngine（Task 5 重写后）
  - `src/email/sequence_engine.py` — SequenceEngine（Task 8 创建）
  - `src/integrations/keyword_client.py` — KeywordClient（Task 1 完善后）

  **Acceptance Criteria**:

  - [ ] 3 个新任务在 JOB_REGISTRY 中注册
  - [ ] `tests/` 目录结构存在
  - [ ] `pytest tests/` 可执行且全部通过
  - [ ] 测试不依赖真实 API key

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: 新任务已注册
    Tool: Bash (grep)
    Steps:
      1. grep "backlink_scan\|email_sequence\|keyword_refresh" src/scheduler/jobs.py
      2. Assert: 3 个任务名称都出现
    Expected Result: 任务已注册

  Scenario: 测试套件通过
    Tool: Bash
    Steps:
      1. pip install pytest pytest-asyncio -q
      2. pytest tests/integration/test_traffic_acquisition.py -v
      3. Assert: exit code 0
      4. Assert: "passed" in output
    Expected Result: 所有测试通过
  ```

  **Commit**: YES
  - Message: `feat(scheduler): add backlink/email/keyword jobs and integration tests`
  - Files: `src/scheduler/jobs.py`, `tests/`
  - Pre-commit: `pytest tests/ -v`

- [x] 11. 迁移合并 + .env.example + DEPLOYMENT.md 更新

  **What to do**:
  - 检查 Task 4 和 Task 7 生成的迁移文件是否有冲突，如有则运行 `alembic merge heads -m "merge_traffic_acquisition_migrations"`
  - 更新 `.env.example` 添加新环境变量：
    ```
    # Keyword Research (DataForSEO)
    KEYWORD_API_PROVIDER=dataforseo
    KEYWORD_API_USERNAME=your_dataforseo_email
    KEYWORD_API_KEY=your_dataforseo_password
    KEYWORD_API_BASE_URL=https://api.dataforseo.com

    # Email (Resend)
    RESEND_API_KEY=re_your_resend_api_key
    RESEND_FROM_EMAIL=noreply@yourdomain.com
    ```
  - 更新 `DEPLOYMENT.md` 添加新功能的部署说明：
    - DataForSEO 配置步骤
    - Resend 配置步骤
    - 新 API 端点列表
    - 邮件订阅短代码使用说明

  **Must NOT do**:
  - 不要修改现有 .env.example 中的变量
  - 不要删除 DEPLOYMENT.md 中的现有内容

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 文件更新，无复杂逻辑
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (final task)
  - **Blocks**: None
  - **Blocked By**: All previous tasks

  **References**:

  **Pattern References**:
  - `.env.example:1-49` — 现有环境变量格式
  - `alembic.ini:5` — `script_location = migrations`

  **Acceptance Criteria**:

  - [ ] `alembic heads` 只显示一个 head（无分叉）
  - [ ] `.env.example` 包含 KEYWORD_API_*, RESEND_API_KEY, RESEND_FROM_EMAIL
  - [ ] `DEPLOYMENT.md` 包含新功能说明

  **Agent-Executed QA Scenarios**:

  ```
  Scenario: Alembic 无分叉 head
    Tool: Bash
    Steps:
      1. alembic heads
      2. Assert: 只有一个 head
    Expected Result: 迁移链无分叉

  Scenario: .env.example 包含新变量
    Tool: Bash (grep)
    Steps:
      1. grep "RESEND_API_KEY" .env.example
      2. Assert: 存在
      3. grep "KEYWORD_API_USERNAME" .env.example
      4. Assert: 存在
    Expected Result: 新变量已添加
  ```

  **Commit**: YES
  - Message: `chore: merge migrations, update env example and deployment docs`
  - Files: `.env.example`, `DEPLOYMENT.md`, `migrations/`

---

## Commit Strategy

| After Task | Message | Key Files | Verification |
|------------|---------|-----------|--------------|
| 1 | `feat(keywords): implement DataForSEO keyword research client` | `src/integrations/keyword_client.py` | python import |
| 4 | `feat(backlinks): add backlink model, DataForSEO backlinks client, and migration` | `src/models/backlink.py`, `src/integrations/dataforseo_backlinks.py` | python import |
| 7 | `feat(email): add Resend client, email models, and migration` | `src/email/`, `src/models/email*.py` | python import |
| 2 | `feat(keywords): enrich keyword strategy with real search volume data` | `src/services/keyword_strategy.py` | python import |
| 3 | `feat(keywords): add keyword research API endpoints` | `src/api/keywords.py` | python import |
| 5 | `feat(backlinks): replace sample data with real DataForSEO backlink discovery` | `src/backlink/copilot.py` | grep no fake data |
| 8 | `feat(email): add sequence engine and email API endpoints` | `src/email/sequence_engine.py`, `src/api/email.py` | python import |
| 6 | `feat(backlinks): add outreach sender with daily limit and admin approval` | `src/backlink/outreach_sender.py` | python import |
| 9 | `feat(email): add subscribe form JS and WordPress shortcode` | `static/js/`, `wp-content/` | file exists |
| 10 | `feat(scheduler): add backlink/email/keyword jobs and integration tests` | `src/scheduler/jobs.py`, `tests/` | pytest |
| 11 | `chore: merge migrations, update env example and deployment docs` | `.env.example`, `DEPLOYMENT.md` | grep |

---

## Success Criteria

### Verification Commands
```bash
# 模块导入验证
python -c "from src.integrations.keyword_client import KeywordClient; print('Keywords OK')"
python -c "from src.integrations.dataforseo_backlinks import DataForSEOBacklinksClient; print('Backlinks OK')"
python -c "from src.email.resend_client import ResendClient; print('Email OK')"
python -c "from src.email.sequence_engine import SequenceEngine; print('Sequence OK')"
python -c "from src.backlink.outreach_sender import OutreachSender; print('Outreach OK')"

# 假数据已移除
grep -c "example-blog" src/backlink/copilot.py  # Expected: 0
grep -c "resource-site" src/backlink/copilot.py  # Expected: 0

# 新端点已注册
python -c "from src.api.keywords import keyword_router; print(f'Keyword routes: {len(keyword_router.routes)}')"
python -c "from src.api.email import email_router; print(f'Email routes: {len(email_router.routes)}')"

# 测试通过
pytest tests/integration/test_traffic_acquisition.py -v

# 迁移无分叉
alembic heads
```

### Final Checklist
- [x] `_fetch_dataforseo()` 不再是空 pass
- [x] `_generate_sample_mentions()` 和 `_generate_sample_resource_pages()` 已被真实 API 调用替换
- [x] 邮件订阅端点可接收请求
- [x] 所有新端点在 `/docs` 中可见
- [x] Outreach 发送需要管理员确认
- [x] 每日 Outreach 限制 50 封
- [x] 邮件序列为线性（无条件分支）
- [x] `.env.example` 包含所有新环境变量
- [x] 所有测试通过
- [x] Alembic 迁移链无分叉
