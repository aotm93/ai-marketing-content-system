# Draft: 流量获取三大修复

## Requirements (confirmed)
- 修复1: 关键词研究无真实数据 → 集成 DataForSEO API
- 修复2: 外链发现是假数据 → 实现真实外链发现引擎
- 修复3: 无邮件获客系统 → 集成 Resend API

## Technical Decisions
- DataForSEO: 项目已有 KeywordClient 框架 (src/integrations/keyword_client.py)，需要完成真实 API 实现
- Resend: 用户指定使用 Resend，Python SDK 成熟 (resend-python)
- 外链: src/backlink/copilot.py 全是占位符数据，需要真实爬取

## Research Findings

### 1. 关键词研究现状
- src/integrations/keyword_client.py: 已有 KeywordClient 框架，支持 generic/dataforseo provider
- _fetch_dataforseo() 方法是空的 (pass)
- src/services/keyword_strategy.py: 基于模板生成关键词，无真实搜索量
- src/scheduler/jobs.py: content_generation_job 已有 3 层关键词获取逻辑 (GSC → Content-Aware → Keyword API → Fallback)
- settings.py: 已有 keyword_api_provider, keyword_api_key, keyword_api_username, keyword_api_base_url 配置
- DataForSEO API: /v3/dataforseo_labs/google/keyword_suggestions/live 提供搜索量+难度+CPC

### 2. 外链发现现状
- src/backlink/copilot.py: BacklinkDiscoveryEngine 全是 _generate_sample_* 方法
- find_unlinked_mentions(): 只是 logger.info + 假数据
- find_resource_pages(): 同上
- OutreachGenerator: 邮件模板存在但无发送能力
- OutreachTracker: 内存存储，无持久化

### 3. 邮件获客现状
- 完全不存在邮件获客模块
- Resend Python SDK: resend.Emails.send(), resend.Batch.send(), resend.Contacts.create()
- Resend 支持: Audiences, Segments, Broadcasts, Contacts 管理

## Scope Boundaries
- INCLUDE: DataForSEO 关键词 API 完整实现, 外链真实发现引擎, Resend 邮件获客系统
- EXCLUDE: 付费广告自动化, 社交媒体自动化, CRM 集成

## Open Questions
- 外链发现: 用 DataForSEO Backlinks API 还是自建爬虫?
- 邮件获客: 需要哪些邮件序列? (Welcome, Content digest, Lead nurture?)
