# AI Marketing Content System - SEO Autopilot

## 项目结构 (P0 升级后)

```
bobopkgproject/
├── src/
│   ├── agents/                    # AI Agents
│   │   ├── __init__.py
│   │   ├── base_agent.py          # 基础 Agent 类
│   │   ├── orchestrator.py        # 编排器
│   │   ├── market_researcher.py   # 市场研究
│   │   ├── keyword_strategist.py  # 关键词策略
│   │   ├── content_creator.py     # 内容创作
│   │   ├── media_creator.py       # 媒体创作
│   │   └── publish_manager.py     # [P0升级] 发布管理器
│   │
│   ├── api/                       # REST API
│   │   ├── __init__.py
│   │   ├── main.py               # [P0升级] FastAPI 应用入口
│   │   ├── admin.py              # 管理面板 API
│   │   ├── autopilot.py          # [P0新增] Autopilot 控制 API
│   │   ├── agents.py             # Agent 执行 API
│   │   └── content.py            # 内容 API
│   │
│   ├── config/                    # 配置
│   │   ├── __init__.py
│   │   └── settings.py           # [P0升级] 添加 Autopilot 参数
│   │
│   ├── core/                      # 核心组件
│   │   ├── __init__.py
│   │   ├── ai_provider.py        # AI 服务提供商
│   │   ├── auth.py               # 认证
│   │   ├── event_bus.py          # 事件总线
│   │   ├── plugin_manager.py     # 插件管理
│   │   └── rate_limiter.py       # API 限流
│   │
│   ├── integrations/              # [P0新增] 外部服务集成
│   │   ├── __init__.py
│   │   ├── wordpress_client.py   # WordPress REST API 客户端
│   │   ├── rankmath_adapter.py   # Rank Math SEO 适配器
│   │   └── publisher_adapter.py  # 发布平台适配器
│   │
│   ├── models/                    # 数据模型
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── keyword.py
│   │   ├── content.py
│   │   ├── agent_execution.py
│   │   └── job_runs.py           # [P0新增] 任务执行审计
│   │
│   └── scheduler/                 # [P0新增] 调度系统
│       ├── __init__.py
│       ├── job_runner.py         # 任务执行引擎
│       ├── autopilot.py          # Autopilot 调度器
│       └── jobs.py               # 任务定义
│
├── migrations/                    # 数据库迁移
│   └── versions/
│       └── p0_001_job_runs.py    # [P0新增] 任务表迁移
│
├── wordpress/                     # [P0新增] WordPress 资源
│   └── mu-plugins/
│       └── seo-autopilot-rankmath.php  # Rank Math REST API 扩展
│
├── static/                        # 静态文件
│   └── admin/                     # 管理面板前端
│
├── docs/                          # 文档
│   └── P0_UPGRADE_COMPLETE.md    # [P0新增] 升级完成记录
│
├── .env.example                   # [P0升级] 环境变量模板
├── requirements.txt               # [P0升级] 添加 APScheduler
├── UPGRADE_ROADMAP.md            # 升级路线图
└── README.md                      # 项目说明
```

## P0 新增能力

### 1. WordPress 真发布
- REST API 完整集成
- 媒体上传支持
- 分类/标签自动创建

### 2. Rank Math SEO 集成
- SEO meta 自动写入
- 自检接口验证集成
- MU 插件扩展 REST API

### 3. Autopilot 调度系统
- APScheduler 定时执行
- 限频控制 (每日/间隔)
- 并发管理
- 指数退避重试

### 4. 可观测性
- 任务执行审计表
- 执行历史 API
- 失败任务追踪

### 5. 配置体系
- 完整参数配置
- 推荐值说明
- 简易/专家模式

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
cp .env.example .env
# 编辑 .env 填入你的配置

# 3. 运行数据库迁移
alembic upgrade head

# 4. 启动服务
uvicorn src.api.main:app --reload

# 5. 访问
# API 文档: http://localhost:8000/docs
# 管理面板: http://localhost:8000/admin
# Autopilot: http://localhost:8000/api/v1/autopilot/status
```

## API 端点速查

| 端点 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /api/v1/autopilot/status` | Autopilot 状态 |
| `POST /api/v1/autopilot/start` | 启动 Autopilot |
| `POST /api/v1/autopilot/run-now` | 立即执行一次 |
| `POST /api/v1/autopilot/seo-check` | SEO 集成自检 |
