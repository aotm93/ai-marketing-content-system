## 项目升级开发路线文档（对标 AutoSEO / SEObotAI，面向自动化流量增长）

本文档用于评审与拆票落地：把当前系统从“内容生成器雏形”升级为可持续复利的 **SEO Autopilot（自动化流量增长系统）**。

已知约束与要求：

- CMS：WordPress（当前项目核心）
- SEO 插件：**Rank Math SEO**（必须支持写入 Title/Description/Focus Keyword 等元信息）
- 后台管理：可配置**频率**、**限额**、**策略开关**、**质量阈值**，并提供“推荐值/说明建议”

---

## 1. 对标拆解：AutoSEO / SEObotAI 的“可复用能力”

下面的能力点来自两类产品的公开定位与页面内容，可归纳为 6 个关键词：

1. **Autopilot**：无人值守持续运行（你睡觉也在增长）
2. **Keyword → Content → Publish**：自动选题、写作、发布
3. **Internal Linking**：自动内链（形成 topic cluster）
4. **Programmatic SEO (pSEO)**：程序化/模板化页面生成
5. **Backlinks（自动化“外链能力”）**：通过网络/机制/辅助流程获取链接
6. **多平台集成**：WordPress/Shopify/Webflow/自定义 webhook 等

对我们的启发不是“照抄功能”，而是把这些能力组合成可控闭环，并针对 B2B/电商业务强化“转化”。

### 1.1 竞品能力矩阵（用于评审对齐）

| 能力 | AutoSEO（官网描述） | SEObotAI（官网描述） | 我们的升级实现（建议） |
| --- | --- | --- | --- |
| 自动化选题 | low-hanging fruits / keyword research | auto keyword research | GSC 驱动 + 规则/模型评分 + 机会池 |
| 自动写作 | content writing / autoblogging | AI generated blog | 模块化页面资产 + RAG 约束 |
| 自动发布 | publishing blogs |（隐含：自动化执行）| WP 真发布 + Rank Math meta + 定时/草稿 |
| 自动内链 | linking pages | AI internal linking | Topic Map 驱动的内链引擎 + 防蚕食 |
| pSEO |（隐含：规模化 SEO）| Programmatic SEO | pSEO 工厂：属性组合页/场景页/对比页 |
| 外链能力 | free backlinks daily（网络式） | AI backlinks | 先做 Backlink Copilot；网络式外链仅可选且强约束 |
| 平台集成 | WordPress/Shopify/Webflow + webhook | CMS 列表 + REST/Webhooks/Zapier/Make | Publisher Adapter + Webhook 集成层（先 WP，后扩展） |

---

## 2. 我们的目标产品形态：SEO Autopilot（增长操作系统）

建议把系统产品化为 4 个后台看板（所有自动化都可被观察、干预、回滚）：

1. **Opportunity Backlog（机会池）**：低垂果实、缺口主题、可扩的 pSEO 维度
2. **Production Pipeline（生产流水线）**：Brief → Draft → Generated → Quality Passed → Scheduled/Published
3. **Topic Map（主题图谱）**：Hub/Spoke，内链与防蚕食的“唯一真相”
4. **Performance（效果面板）**：GSC/GA4 数据回写，触发刷新、CTR 优化、模板迭代

---

## 3. 关键能力设计（合并两站点思路后的“更有效组合”）

### 3.1 机会发现：优先做“低垂果实 + 可规模化”两条线

1) 低垂果实（最快看到效果）
- 从 GSC 找到：`impressions 高且 position 4–20` 的 query/page
- 自动生成：标题/描述优化建议、补充段落/FAQ、补内链

2) 可规模化（pSEO 工厂，做复利）
- 围绕产品属性维度（材质/规格/容量/场景/行业/认证/交期/MOQ）生成模板页
- 必须绑定“信息增量模块”：表格、FAQ、案例、规格、选型建议（避免批量低质）

### 3.2 内容生产：从“写文章”升级到“生成页面资产”

把内容拆成可复用模块，支持不同 SERP 意图：

- Informational：术语解释、流程、选型指南、FAQ
- Commercial：对比页、best X for Y、推荐列表（含表格）
- Transactional：类目聚合/属性组合落地页（强 CTA：询价/样品）

并加入 RAG（产品资料/工厂能力/参数库）保证真实性与一致性。

### 3.3 发布与 SEO 元信息：Rank Math“可验证写入”

目标：发布时同时写入（至少）SEO title / meta description / focus keyword。

推荐实现：

- 后端通过 WP REST 更新 post meta
- 若 Rank Math meta 默认不可 REST 更新：提供一个极小的 WP 端 MU 插件用于 `register_meta(..., show_in_rest=True)`

后台提供“SEO 集成自检”：选择一篇文章 → 写入测试 meta → 验证 Rank Math UI 是否展示 → 给出修复建议。

### 3.4 内链：把“自动链接”做成可控引擎，而非硬插

内链策略建议：

- 由 Topic Map 决定：新内容必须链接到 Hub（money page/支柱页）
- Anchor 文案生成要受控：避免过度优化、避免同词锚文本
- 反向补链：新内容发布后，自动在旧内容中补 1–3 条链回新内容（形成集群）

### 3.5 外链（Backlinks）：建议从“自动化能力”改为“可合规的外链协作/辅助”

竞品常见做法是“网络式自动外链”，但存在搜索引擎风险。建议分两层：

- **P1：Backlink Copilot（安全）**
  - 自动发现机会：品牌提及未链接、资源页、目录页、合作伙伴页
  - 自动生成 outreach 素材：邮件、落地页、资产包（规格书/素材）
  - 自动跟踪状态：已联系/已回复/已上链
- **P2：Cross-link Network（可选，强约束）**
  - 仅对“同集团多站/自有站群”开放
  - 默认 `rel="nofollow"` 或 `sponsored`（降低风险）
  - 严格限频与随机化，避免模式化链接

---

## 4. 分阶段开发路线（可直接用于拆票）

> 本节之后新增了“拆票清单”，可以直接导入 Jira/Trello。

### Phase P0（1–2 周）：跑通最小闭环（可发布 + 可调度 + 可审计）

**目标**：系统能按频率自动跑一次完整流程，并能在后台看到/控制。

交付物（必须）：

- WordPress 真发布（posts/media/taxonomy 基础能力）
- Rank Math 元信息写入（至少 1 项可验证）
- 调度器（APScheduler 或 Celery beat）+ 执行限额（每日发布上限、间隔）
- 后台参数（启用/暂停、频率、并发、超时、失败退避）+ 推荐值说明
- 执行审计（job_runs / logs）

验收：

- 后台点“立即运行一次”，能产生 1 篇草稿/发布并记录审计

#### P0 拆票清单（建议 10–14 张）

1) **WordPress 发布能力（后端）**
- [P0-1] 新增 `WordPressClient`：支持 `create_post/update_post/get_post`（REST + Basic/Auth）
- [P0-2] 支持媒体上传 `upload_media`（featured image、正文图片）
- [P0-3] 支持 taxonomy：category/tag 创建与绑定（避免发布后全是 uncategorized）

2) **Rank Math SEO 写入（后端 + 站点自检）**
- [P0-4] 新增 `RankMathAdapter`：将 `seo_title/meta_description/focus_keyword` 映射到 WP post meta
- [P0-5] 新增“SEO 自检接口”：对指定 post 进行 meta 写入测试 + 读取验证（输出诊断建议）
- [P0-6]（可选）提供 WP 端 MU 插件示例：`register_meta(..., show_in_rest=True)`

3) **调度器与限频（系统）**
- [P0-7] 新增 `JobRunner`：统一执行入口（限额、并发、退避、超时）
- [P0-8] 引入调度：优先 `APScheduler`（最小化改动），或直接上 `Celery + beat`
- [P0-9] 新增“立即运行一次”API（后台按钮触发）

4) **可观测性与审计（DB）**
- [P0-10] 新增 `job_runs` 表或模型：记录每次执行输入/输出/错误
- [P0-11] 后台页面：最近 N 次运行记录、失败原因、重试按钮

5) **后台参数（Admin Panel）**
- [P0-12] SEO 插件选项新增 `rank_math`
- [P0-13] 增加 Autopilot 关键参数：启用开关、发布间隔、每日上限、并发、失败退避
- [P0-14] 每个参数附“推荐值/说明”文案（先硬编码到前端 JSON，P1 再迁移到 DB）

### Phase P1（3–6 周）：机会池 + 内链 + 刷新（开始复利）

**目标**：从 GSC 驱动选题与优化，做出“自我迭代”。

交付物：

- GSC 数据接入（query/page 指标回写到 DB）
- Opportunity Scoring（低垂果实优先）+ 机会池看板
- CTR 优化：标题/描述候选 + 后台一键应用
- 内容刷新：position 8–20 或下滑页面触发 refresh
- 内链引擎 v1：topic cluster + 新文自动插入内链

验收：

- 每天自动生成 10 条机会（可解释/可执行）
- 至少 1 个页面完成 refresh 并可追踪前后变化

#### P1 拆票清单（建议 12–18 张）

1) **数据接入（GSC/GA4）**
- [P1-1] GSC OAuth/Service Account 接入（只读权限即可）
- [P1-2] `gsc_queries` 入库：date/query/page/impressions/clicks/ctr/position
- [P1-3] 后台“数据源连接状态”页：配额、最近同步时间、错误提示

2) **机会评分与 Backlog**
- [P1-4] `OpportunityScoringAgent`：基于 GSC 规则评分（优先 position 4–20）
- [P1-5] `BriefBuilderAgent`：按 SERP 意图输出结构化 brief（页面类型、模块、内链目标、CTA）
- [P1-6] 后台机会池：筛选/排序/一键入生产（生成 draft）

3) **刷新与 CTR 优化（增长闭环）**
- [P1-7] `ContentRefreshAgent`：对指定 page/query 生成 refresh patch（段落/FAQ/表格/内链）
- [P1-8] `TitleMetaOptimizer`：对 CTR 低页面给 3–5 组 title/description，支持一键应用
- [P1-9] “变更记录”表：content_actions（保存 before/after 摘要，便于回滚）

4) **内链引擎 v1**
- [P1-10] `TopicMap` 数据结构（最小化版本：hub_id + spoke_ids + intents）
- [P1-11] `InternalLinkAgent`：新内容插入 5–15 条内链 + 旧文反向补链 1–3 条
- [P1-12] 蚕食检测 v1：同意图多页面冲突 → 标记需要合并/设 canonical

5) **参数体系升级（可控性）**
- [P1-13] 参数分组（频率/策略/质量/成本），后台新增“简易模式/专家模式”
- [P1-14] 成本保护：`MAX_TOKENS_PER_DAY` 与队列熔断

### Phase P2（6–12 周）：pSEO 页面工厂 + 模板系统（规模化拿量）

**目标**：让“程序化页面”成为主要流量放大器，同时控制质量风险。

交付物：

- 模板系统（模块化组件：表格/FAQ/案例/CTA）
- pSEO 工厂：属性组合页、场景页、对比页
- 质量门禁升级：去重/蚕食检测/事实校验/RAG

验收：

- 可配置生成 N 个组合页（有差异化与信息增量）
- 可监控收录与排名变化

#### P2 拆票清单（建议 15–25 张）

1) **模板与组件系统**
- [P2-1] 定义页面组件协议：Summary/Table/FAQ/Case/CTA/Specs
- [P2-2] `QualityGateAgent`：相似度检测 + 信息增量强制（至少包含 N 个模块）
- [P2-3] RAG：产品资料向量库/检索（确保参数一致）

2) **pSEO 工厂**
- [P2-4] 定义维度模型：材质/容量/场景/行业/认证/瓶口/形状等
- [P2-5] 组合生成器：支持“白名单组合”（避免无限组合产生低质页面）
- [P2-6] canonical/分页/索引策略（防重复与抓取浪费）

3) **规模化发布与监控**
- [P2-7] 发布队列与回滚：批量发布支持暂停/恢复/撤回
- [P2-8] 索引与收录监控：站点地图提交/IndexNow（若适用）/收录状态面板

### Phase P3（可选，按业务优先级）：转化闭环 + 外链 Copilot

**目标**：从“拿流量”升级到“拿询盘/转化”。

交付物：

- CTA 与转化事件埋点（按意图动态 CTA）
- 线索回写（按页面/主题/模板计算 ROI）
- Backlink Copilot（机会发现 + outreach + 跟踪）

#### P3 拆票清单（建议 10–16 张）

- [P3-1] CTA 组件化：按意图切换（询价/样品/下载规格书）
- [P3-2] 转化埋点与回传：按 page/topic/template 归因
- [P3-3] 线索质量回写：以 ROI 反哺 OpportunityScore
- [P3-4] Backlink Copilot：品牌提及未链接、资源页机会发现、outreach 生成、状态跟踪

---

## 5. 后台参数体系（频控与“推荐值说明”）

建议把配置分组，并在 UI 上对每个参数提供：推荐值、风险提示、适用场景。

1) 频率/限额
- `AUTOPILOT_ENABLED`
- `PUBLISH_INTERVAL_MINUTES`
- `MAX_POSTS_PER_DAY`
- `MAX_CONCURRENT_AGENTS`

2) 策略开关
- `AUTO_DISCOVER_KEYWORDS`
- `AUTO_GENERATE_CONTENT`
- `AUTO_PUBLISH`
- `AUTO_INTERNAL_LINKING`
- `AUTO_REFRESH_CONTENT`
- `AUTO_CTR_OPTIMIZE`

3) 质量阈值
- `DUPLICATION_SIMILARITY_THRESHOLD`
- `MIN_IMPRESSIONS_THRESHOLD`
- `TARGET_POSITION_MIN/MAX`

4) 成本控制
- `MAX_TOKENS_PER_DAY`
- `MODEL_ROUTING_POLICY`（主模型/降级模型）

---

## 6. 风险与边界（必须在评审时确认）

- 自动外链策略是否启用（合规与风险偏好）
- 自动发布是否允许直发生产（建议默认草稿 + 抽检）
- 是否多站/多租户（决定权限模型与数据隔离）
- 目标语言/国家（决定 keyword 与 SERP 模式）

---

## 7. “忙碌创始人模式”：把复杂度隐藏到后台

SEObotAI/AutoSEO 的共同点是：把专业 SEO 的复杂度包装成“选一个强度等级就开始跑”。建议我们也做两层模式：

- **简易模式（推荐默认）**：
  - 只暴露 3 个旋钮：`增长强度(保守/标准/激进)`、`每日预算上限`、`是否自动发布(草稿/定时/直发)`
  - 其余参数由系统给推荐值（后台可解释）
- **专家模式（Advanced）**：
  - 展示完整频率/阈值/策略开关
  - 支持导出/导入配置（适配多站）

---

## 8. 多平台集成策略（先 WP、后扩展）

为了对齐竞品“多 CMS”能力，但不拖慢 MVP，建议用适配器架构：

- `PublisherAdapter` 接口：`create_post / update_post / upload_media / set_taxonomy / set_seo_meta`
- `WordPressAdapter`（P0 必做）：WP REST + Rank Math meta
- `WebhookAdapter`（P1 选做）：把“已生成页面资产”通过 webhook 推给外部系统（Shopify/Webflow/自研）
