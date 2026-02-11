# SEO Autopilot - AI Marketing Content System

> 全栈 SEO 自动化 + 转化闭环平台

[![Version](https://img.shields.io/badge/version-4.1.0-blue.svg)](https://github.com/yourusername/seo-autopilot)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-开发版本-yellow.svg)](REPAIR_PLAN.md)

## ⚠️ 项目状态

**当前状态**: 开发版本 (代码完成度 65%)  
**目标状态**: 生产就绪 (代码完成度 90%+)  

**📋 查看 [REPAIR_PLAN.md](REPAIR_PLAN.md) 了解修复方案**

本项目已完成功能框架，但需要修复关键问题才能达到生产就绪。详见修复方案文档。

---

## 🚀 概述

**SEO Autopilot** 是一个企业级的 AI 驱动 SEO 自动化平台，集成了内容生成、程序化 SEO、Google Search Console 数据分析、转化追踪和外链建设等全流程功能。

### 核心能力

- ✅ **自动内容发布** - WordPress 集成 + Rank Math SEO
- ✅ **GSC 数据驱动** - 低垂之果发现 + 机会评分 (P1)
- ✅ **规模化 pSEO** - 10,000+ 页面自动生成 (P2)
- ✅ **转化追踪** - 多触点归因 + ROI 分析 (P3)
- ✅ **简易部署** - Admin 后台可视化配置，无需复杂环境变量

---

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     SEO Autopilot Platform                   │
├─────────────────────────────────────────────────────────────┤
│  P0: 基础发布  │  P1: GSC 驱动  │  P2: pSEO 工厂  │  P3: 转化闭环  │
├─────────────────────────────────────────────────────────────┤
│ • WordPress API │ • GSC 集成    │ • 组件系统     │ • 动态 CTA     │
│ • Autopilot    │ • 5x Agents   │ • 质量门禁     │ • 归因分析     │
│ • 任务队列      │ • 内链引擎    │ • 索引监控     │ • Lead 评分    │
│ • Rank Math    │ • 机会评分    │ • 批量生成     │ • Outreach     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈

### 后端
- **FastAPI** - 异步 Web 框架
- **SQLAlchemy** - ORM (PostgreSQL)
- **APScheduler** - 定时任务
- **Alembic** - 数据库迁移

### AI & 算法
- **OpenAI GPT-4** - 内容生成
- **LangChain** - LLM 编排

### 集成
- **WordPress REST API** - 发布平台
- **Google Search Console** - 数据源 (Service Account / OAuth)
- **Rank Math** - SEO 优化

---

## 📦 快速部署

我们采用了简化的部署流程，推荐使用 **Docker** 或 **Zeabur/Railway** 等 PaaS 平台。

### 1. 部署服务
只需设置最基础的环境变量即可启动：

```bash
# 必填
DATABASE_URL=postgresql://user:pass@host:5432/db
ADMIN_PASSWORD=your_secure_password
ADMIN_SESSION_SECRET=your_random_secret

# 选填
REDIS_URL=redis://host:6379/0
```

### 2. 系统配置 (Admin Panel)
服务启动后，访问 `/admin` 进入后台：
1. 使用 `ADMIN_PASSWORD` 登录
2. 进入 **Configuration** 页面
3. 在界面上配置：
   - WordPress URL & 账号密码
   - OpenAI API Key
   - Google Search Console 凭证
   - 自动发布策略

点击保存即刻生效，无需重启服务。

👉 详细指南请参阅 [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📚 API 端点概览

### Autopilot (P0)

```bash
POST /api/v1/autopilot/start    # 启动自动发布
POST /api/v1/autopilot/run-now  # 立即运行一次
GET  /api/v1/autopilot/status   # 查看状态
```

### Google Search Console (P1)

```bash
POST /api/v1/gsc/auth           # 认证 GSC
GET  /api/v1/gsc/opportunities  # 获取 SEO 机会
POST /api/v1/gsc/sync           # 同步数据
```

### pSEO (P2)

```bash
POST /api/v1/pseo/generate      # 生成程序化页面
GET  /api/v1/pseo/preview       # 预览生成
```

---

## 📖 文档

### 核心文档

- [📋 修复方案](REPAIR_PLAN.md) - **必读** 生产就绪修复计划
- [🚀 部署指南](DEPLOYMENT.md) - 部署和配置说明
- [📊 GSC 设置指南](docs/GSC_SETUP_GUIDE.md) - Google Search Console 配置
- [🏗️ 项目结构](docs/PROJECT_STRUCTURE.md) - 代码架构说明

### 其他

- [GitHub 集成指南](GITHUB_INTEGRATION.md)

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件
