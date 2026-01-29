# Bug 追踪文档 (Bug Tracking Document)

**项目**: SEO Autopilot - AI Marketing Content System  
**版本**: 4.1.0  
**创建日期**: 2026-01-28  
**最后更新**: 2026-01-28

---

## 🔴 严重 Bug (Critical Bugs)

### BUG-001: SEO 自检接口未实现

**优先级**: P0 (Critical)  
**状态**: 🔴 Open  
**发现日期**: 2026-01-28  
**影响模块**: P0 - 基础发布系统

#### 问题描述
根据 UPGRADE_ROADMAP.md 中的 P0-5 票据要求，应该实现一个 SEO 自检接口，用于验证 Rank Math SEO 元数据是否正确写入。但该接口目前完全未实现。

#### 复现步骤
1. 启动后端服务: `python -m uvicorn src.api.main:app --reload --port 8080`
2. 访问 Admin Panel: `http://localhost:8080/admin`
3. 查找 "SEO 集成自检" 功能
4. **预期**: 应该有一个测试按钮，可以选择文章进行 meta 写入测试
5. **实际**: 该功能不存在

#### 技术细节
- **缺失文件**: 应该在 `src/api/admin.py` 中添加 `/api/v1/admin/seo-check` 端点
- **预期功能**:
  1. 接收 post_id 参数
  2. 写入测试 meta 数据到 WordPress
  3. 读取验证是否成功
  4. 返回诊断建议

#### 影响范围
- 用户无法验证 Rank Math 集成是否正确配置
- 无法诊断 SEO 元数据写入失败的原因
- 增加配置难度和调试时间

#### 建议修复方案

**文件**: `src/api/admin.py`

```python
@router.post("/api/v1/admin/seo-check")
async def seo_integration_check(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_admin)
):
    """
    SEO 集成自检接口
    测试 Rank Math meta 写入和读取
    """
    try:
        # 1. 获取 WordPress 客户端
        wp_client = get_wordpress_client()
        
        # 2. 写入测试 meta
        test_meta = {
            "rank_math_title": "SEO Test Title",
            "rank_math_description": "SEO Test Description",
            "rank_math_focus_keyword": "test keyword"
        }
        
        success = await wp_client.update_post_meta(post_id, test_meta)
        
        # 3. 读取验证
        post = await wp_client.get_post(post_id)
        meta = post.get("meta", {})
        
        # 4. 生成诊断报告
        diagnostics = {
            "write_success": success,
            "meta_found": {
                "title": "rank_math_title" in meta,
                "description": "rank_math_description" in meta,
                "keyword": "rank_math_focus_keyword" in meta
            },
            "values": {
                "title": meta.get("rank_math_title"),
                "description": meta.get("rank_math_description"),
                "keyword": meta.get("rank_math_focus_keyword")
            }
        }
        
        # 5. 提供修复建议
        if not all(diagnostics["meta_found"].values()):
            diagnostics["recommendation"] = (
                "Rank Math meta fields not accessible via REST API. "
                "Please install the MU plugin to register meta fields. "
                "See docs/rank-math-mu-plugin.php"
            )
        else:
            diagnostics["recommendation"] = "SEO integration is working correctly!"
        
        return diagnostics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**工作量估算**: 2-4 小时

---

### BUG-002: content_actions 表未创建

**优先级**: P1 (High)  
**状态**: 🔴 Open  
**发现日期**: 2026-01-28  
**影响模块**: P1 - 内容刷新和 CTR 优化

#### 问题描述
根据 UPGRADE_ROADMAP.md 中的 P1-9 票据，应该有一个 `content_actions` 表用于记录内容变更历史（before/after），以支持回滚功能。但该表目前未创建。

#### 复现步骤
1. 连接到数据库
2. 查询表列表: `SELECT name FROM sqlite_master WHERE type='table';`
3. **预期**: 应该看到 `content_actions` 表
4. **实际**: 该表不存在

#### 技术细节
- **缺失**: Alembic 迁移脚本
- **缺失**: SQLAlchemy 模型定义

#### 数据库 Schema 设计

```sql
CREATE TABLE content_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type VARCHAR(50) NOT NULL,  -- 'refresh', 'ctr_optimize', 'title_update', etc.
    post_id INTEGER NOT NULL,
    query VARCHAR(255),
    before_snapshot TEXT,  -- JSON: {title, description, content_excerpt}
    after_snapshot TEXT,   -- JSON: {title, description, content_excerpt}
    reason TEXT,           -- Why this change was made
    metrics_before TEXT,   -- JSON: {position, ctr, impressions, clicks}
    metrics_after TEXT,    -- JSON: same structure (populated after time)
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_by VARCHAR(100),
    rollback_at TIMESTAMP NULL,
    rollback_by VARCHAR(100) NULL,
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'rolled_back', 'superseded'
    
    INDEX idx_post_id (post_id),
    INDEX idx_action_type (action_type),
    INDEX idx_applied_at (applied_at)
);
```

#### 影响范围
- 无法追踪内容变更历史
- 无法实现一键回滚功能
- 无法分析优化效果（A/B 对比）

#### 建议修复方案

**步骤 1**: 创建模型

**文件**: `src/models/content_action.py`

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func
from src.models.base import Base

class ContentAction(Base):
    __tablename__ = "content_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String(50), nullable=False, index=True)
    post_id = Column(Integer, nullable=False, index=True)
    query = Column(String(255), nullable=True)
    before_snapshot = Column(Text, nullable=True)  # JSON
    after_snapshot = Column(Text, nullable=True)   # JSON
    reason = Column(Text, nullable=True)
    metrics_before = Column(Text, nullable=True)   # JSON
    metrics_after = Column(Text, nullable=True)    # JSON
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    applied_by = Column(String(100), nullable=True)
    rollback_at = Column(DateTime(timezone=True), nullable=True)
    rollback_by = Column(String(100), nullable=True)
    status = Column(String(20), default="active")  # active, rolled_back, superseded
    
    __table_args__ = (
        Index('idx_content_actions_post_type', 'post_id', 'action_type'),
        Index('idx_content_actions_applied_at', 'applied_at'),
    )
```

**步骤 2**: 创建迁移

```bash
cd c:\Users\DJS Tech\ZenflowProjects\bobopkgproject
alembic revision -m "add_content_actions_table"
```

**工作量估算**: 1-2 小时

---

### BUG-003: 机会池后台界面未实现

**优先级**: P1 (High)  
**状态**: 🔴 Open  
**发现日期**: 2026-01-28  
**影响模块**: P1 - 机会评分系统

#### 问题描述
根据 UPGRADE_ROADMAP.md 中的 P1-6 票据，应该有一个后台机会池界面，支持筛选、排序和一键执行。但该界面目前未实现。

#### 复现步骤
1. 访问 Admin Panel: `http://localhost:8080/admin`
2. 查找 "Opportunity Backlog" 或 "机会池" 菜单
3. **预期**: 应该有一个页面显示 SEO 机会列表
4. **实际**: 该页面不存在

#### 技术细节
- **缺失**: Admin Panel 前端页面
- **缺失**: API 端点 `/api/v1/opportunities`

#### 功能需求

**界面元素**:
1. 机会列表表格
   - 列: Query, Position, Impressions, CTR, Score, Action
   - 排序: 按 Score 降序
   - 筛选: Position 范围, Impressions 阈值
2. 操作按钮
   - "生成内容" - 创建 draft
   - "优化 CTR" - 生成 title/description 候选
   - "刷新内容" - 更新现有页面
3. 批量操作
   - 选择多个机会
   - 批量生成

#### 影响范围
- 无法可视化管理 SEO 机会
- 无法快速执行优化操作
- 降低系统可用性

#### 建议修复方案

**文件**: `src/api/opportunities.py` (新建)

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.agents.opportunity_scoring import OpportunityScoringAgent

router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])

@router.get("/")
async def list_opportunities(
    min_position: int = Query(4, ge=1, le=100),
    max_position: int = Query(20, ge=1, le=100),
    min_impressions: int = Query(100, ge=0),
    sort_by: str = Query("score", regex="^(score|impressions|position|ctr)$"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    获取 SEO 机会列表
    """
    # 1. 从 gsc_queries 表获取数据
    from src.models.gsc_query import GSCQuery
    
    queries = db.query(GSCQuery).filter(
        GSCQuery.position >= min_position,
        GSCQuery.position <= max_position,
        GSCQuery.impressions >= min_impressions
    ).all()
    
    # 2. 使用 OpportunityScoringAgent 评分
    agent = OpportunityScoringAgent()
    opportunities = []
    
    for query in queries:
        score = agent.calculate_score({
            "position": query.position,
            "impressions": query.impressions,
            "clicks": query.clicks,
            "ctr": query.ctr
        })
        
        opportunities.append({
            "query": query.query,
            "page": query.page,
            "position": query.position,
            "impressions": query.impressions,
            "clicks": query.clicks,
            "ctr": query.ctr,
            "score": score,
            "recommended_action": agent.recommend_action(score, query.position)
        })
    
    # 3. 排序
    opportunities.sort(key=lambda x: x[sort_by], reverse=True)
    
    return {
        "total": len(opportunities),
        "opportunities": opportunities[:limit]
    }

@router.post("/{query_id}/execute")
async def execute_opportunity(
    query_id: int,
    action: str,  # 'generate', 'optimize_ctr', 'refresh'
    db: Session = Depends(get_db)
):
    """
    执行机会优化操作
    """
    # Implementation here
    pass
```

**工作量估算**: 1-2 天

---

### BUG-004: 发布队列控制功能未实现

**优先级**: P2 (Medium)  
**状态**: 🔴 Open  
**发现日期**: 2026-01-28  
**影响模块**: P2 - pSEO 批量生成

#### 问题描述
根据 UPGRADE_ROADMAP.md 中的 P2-7 票据，批量发布应该支持暂停、恢复和撤回功能。但这些控制功能目前未实现。

#### 复现步骤
1. 启动批量生成任务
2. 尝试暂停任务
3. **预期**: 应该有暂停/恢复/撤回按钮
4. **实际**: 任务一旦启动无法控制

#### 技术细节
- **文件**: `src/pseo/page_factory.py`
- **缺失功能**: 
  - `pause_batch(batch_id)`
  - `resume_batch(batch_id)`
  - `cancel_batch(batch_id)`
  - `rollback_batch(batch_id)`

#### 影响范围
- 无法中止错误的批量生成
- 无法撤销已发布的低质量内容
- 增加运营风险

#### 建议修复方案

**文件**: `src/pseo/page_factory.py`

```python
class BatchJobQueue:
    def __init__(self):
        self.jobs = {}
        self.status = {}  # batch_id -> 'running', 'paused', 'cancelled'
    
    def pause_batch(self, batch_id: str) -> bool:
        """暂停批量任务"""
        if batch_id in self.status:
            self.status[batch_id] = 'paused'
            logger.info(f"Batch {batch_id} paused")
            return True
        return False
    
    def resume_batch(self, batch_id: str) -> bool:
        """恢复批量任务"""
        if batch_id in self.status and self.status[batch_id] == 'paused':
            self.status[batch_id] = 'running'
            logger.info(f"Batch {batch_id} resumed")
            return True
        return False
    
    def cancel_batch(self, batch_id: str) -> bool:
        """取消批量任务"""
        if batch_id in self.status:
            self.status[batch_id] = 'cancelled'
            logger.info(f"Batch {batch_id} cancelled")
            return True
        return False
    
    async def rollback_batch(self, batch_id: str, wp_client) -> dict:
        """
        回滚批量发布
        删除或设为草稿
        """
        if batch_id not in self.jobs:
            return {"success": False, "error": "Batch not found"}
        
        job = self.jobs[batch_id]
        published_ids = job.get("published_post_ids", [])
        
        results = {"deleted": 0, "failed": 0}
        
        for post_id in published_ids:
            try:
                # 选项 1: 删除
                # await wp_client.delete_post(post_id)
                
                # 选项 2: 改为草稿
                await wp_client.update_post(post_id, {"status": "draft"})
                results["deleted"] += 1
            except Exception as e:
                logger.error(f"Failed to rollback post {post_id}: {e}")
                results["failed"] += 1
        
        return results
```

**工作量估算**: 4-6 小时

---

### BUG-005: 索引监控完全未实现

**优先级**: P2 (Medium)  
**状态**: 🔴 Open  
**发现日期**: 2026-01-28  
**影响模块**: P2 - pSEO 工厂

#### 问题描述
根据 UPGRADE_ROADMAP.md 中的 P2-8 票据，应该实现索引与收录监控功能，包括站点地图提交、IndexNow 和收录状态面板。但这些功能完全未实现。

#### 复现步骤
1. 批量生成页面
2. 查找索引监控功能
3. **预期**: 应该能看到收录状态
4. **实际**: 无任何监控功能

#### 技术细节
- **缺失**: 站点地图自动提交
- **缺失**: IndexNow API 集成
- **缺失**: 收录状态面板

#### 功能需求

1. **站点地图提交**
   - 生成 sitemap.xml
   - 自动提交到 Google Search Console
   - 提交到 Bing Webmaster Tools

2. **IndexNow 集成**
   - 新页面发布后立即通知搜索引擎
   - 支持批量提交

3. **收录状态面板**
   - 显示已发布 vs 已收录数量
   - 显示收录率趋势
   - 标记未收录页面

#### 影响范围
- 无法追踪页面收录情况
- 无法加速索引过程
- 无法识别索引问题

#### 建议修复方案

**文件**: `src/integrations/indexnow.py` (新建)

```python
import httpx
from typing import List

class IndexNowClient:
    """
    IndexNow API 客户端
    支持 Google, Bing, Yandex 等
    """
    
    ENDPOINTS = [
        "https://www.bing.com/indexnow",
        "https://api.indexnow.org/indexnow"
    ]
    
    def __init__(self, api_key: str, host: str):
        self.api_key = api_key
        self.host = host
    
    async def submit_urls(self, urls: List[str]) -> dict:
        """
        提交 URL 到 IndexNow
        """
        payload = {
            "host": self.host,
            "key": self.api_key,
            "urlList": urls
        }
        
        results = []
        async with httpx.AsyncClient() as client:
            for endpoint in self.ENDPOINTS:
                try:
                    resp = await client.post(
                        endpoint,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    results.append({
                        "endpoint": endpoint,
                        "status": resp.status_code,
                        "success": resp.status_code == 200
                    })
                except Exception as e:
                    results.append({
                        "endpoint": endpoint,
                        "error": str(e),
                        "success": False
                    })
        
        return {
            "submitted_urls": len(urls),
            "results": results
        }
```

**工作量估算**: 2-3 天

---

## 🟡 重要 Bug (Major Bugs)

### BUG-006: job_runs 审计日志不够详细

**优先级**: P1 (High)  
**状态**: 🟡 Open  
**发现日期**: 2026-01-28  
**影响模块**: P0 - 任务调度

#### 问题描述
当前的 job_runs 记录不够详细，缺少输入/输出快照，导致调试困难。

#### 建议修复
在 `src/scheduler/job_runner.py` 中增强日志记录：

```python
class JobRun(Base):
    __tablename__ = "job_runs"
    
    id = Column(Integer, primary_key=True)
    job_name = Column(String(100), nullable=False)
    input_snapshot = Column(Text, nullable=True)  # 新增: JSON
    output_snapshot = Column(Text, nullable=True)  # 新增: JSON
    error_detail = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)  # 新增: 完整堆栈
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20))  # success, failed, timeout
    retry_count = Column(Integer, default=0)  # 新增: 重试次数
```

**工作量估算**: 4-6 小时

---

### BUG-007: GSC 数据源状态页未实现

**优先级**: P1 (High)  
**状态**: 🟡 Open  
**发现日期**: 2026-01-28  
**影响模块**: P1 - GSC 集成

#### 问题描述
根据 P1-3 票据，应该有一个数据源连接状态页，显示配额、最近同步时间和错误提示。

#### 建议修复
在 Admin Panel 中添加 "Data Sources" 页面：

**API 端点**: `/api/v1/gsc/status`

```python
@router.get("/status")
async def gsc_status(db: Session = Depends(get_db)):
    """
    GSC 连接状态和配额信息
    """
    try:
        gsc_client = get_gsc_client()
        
        # 获取配额信息 (Google API 限制)
        quota_info = {
            "daily_limit": 2000,  # GSC API 每日限制
            "used_today": await get_daily_usage(db),
            "remaining": 2000 - await get_daily_usage(db)
        }
        
        # 最近同步时间
        last_sync = db.query(GSCQuery).order_by(
            GSCQuery.date.desc()
        ).first()
        
        return {
            "connected": True,
            "quota": quota_info,
            "last_sync": last_sync.date if last_sync else None,
            "total_queries": db.query(GSCQuery).count(),
            "health": "healthy" if quota_info["remaining"] > 100 else "warning"
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "health": "error"
        }
```

**工作量估算**: 1 天

---

### BUG-008: TopicMap 为简化版本

**优先级**: P1 (High)  
**状态**: 🟡 Open  
**发现日期**: 2026-01-28  
**影响模块**: P1 - 内链引擎

#### 问题描述
当前的 TopicMap 是简化版本，缺少完整的 Hub/Spoke 关系管理，导致内链策略不够智能。

#### 建议增强

**文件**: `src/agents/internal_linking.py`

```python
class TopicMap:
    """
    完整的主题图谱
    支持 Hub/Spoke 关系和意图分组
    """
    
    def __init__(self):
        self.hubs = {}  # hub_id -> Hub
        self.spokes = {}  # spoke_id -> Spoke
        self.intent_groups = {}  # intent -> [post_ids]
    
    def add_hub(self, post_id: int, title: str, intent: str):
        """添加支柱页 (Hub)"""
        self.hubs[post_id] = {
            "title": title,
            "intent": intent,
            "spokes": [],
            "authority_score": 0.0
        }
    
    def add_spoke(self, post_id: int, title: str, hub_id: int):
        """添加辐射页 (Spoke)"""
        self.spokes[post_id] = {
            "title": title,
            "hub_id": hub_id
        }
        if hub_id in self.hubs:
            self.hubs[hub_id]["spokes"].append(post_id)
    
    def detect_cannibalization(self, intent: str) -> List[dict]:
        """
        检测关键词蚕食
        同意图多页面竞争检测
        """
        posts = self.intent_groups.get(intent, [])
        if len(posts) > 1:
            return [{
                "intent": intent,
                "conflicting_posts": posts,
                "recommendation": "merge or set canonical"
            }]
        return []
    
    def recommend_internal_links(self, post_id: int, count: int = 5) -> List[dict]:
        """
        推荐内链
        优先链接到 Hub，然后是相关 Spokes
        """
        links = []
        
        # 1. 如果是 Spoke，必须链接到 Hub
        if post_id in self.spokes:
            hub_id = self.spokes[post_id]["hub_id"]
            links.append({
                "target_id": hub_id,
                "anchor_text": self.hubs[hub_id]["title"],
                "reason": "hub_link"
            })
        
        # 2. 链接到相关 Spokes
        # (基于意图相似度)
        
        return links[:count]
```

**工作量估算**: 2-3 天

---

### BUG-009: QualityGateAgent 功能不完整

**优先级**: P2 (Medium)  
**状态**: 🟡 Open  
**发现日期**: 2026-01-28  
**影响模块**: P2 - pSEO 质量控制

#### 问题描述
QualityGateAgent 的相似度检测和信息增量验证功能不完整。

#### 建议增强

```python
from difflib import SequenceMatcher
from typing import List, Dict

class QualityGateAgent:
    """
    质量门禁 Agent
    防止低质量和重复内容
    """
    
    SIMILARITY_THRESHOLD = 0.85  # 85% 相似度视为重复
    MIN_MODULES_REQUIRED = 3     # 至少包含 3 个信息模块
    
    async def check_similarity(self, new_content: str, existing_contents: List[str]) -> dict:
        """
        检查内容相似度
        """
        max_similarity = 0.0
        most_similar = None
        
        for idx, existing in enumerate(existing_contents):
            similarity = SequenceMatcher(None, new_content, existing).ratio()
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar = idx
        
        return {
            "max_similarity": max_similarity,
            "is_duplicate": max_similarity > self.SIMILARITY_THRESHOLD,
            "most_similar_index": most_similar,
            "threshold": self.SIMILARITY_THRESHOLD
        }
    
    async def check_information_value(self, page_data: dict) -> dict:
        """
        检查信息增量
        确保页面包含足够的独特模块
        """
        modules = page_data.get("modules", [])
        module_types = set([m["type"] for m in modules])
        
        required_types = {"summary", "table", "faq"}
        has_required = required_types.issubset(module_types)
        
        return {
            "module_count": len(modules),
            "unique_types": len(module_types),
            "has_required_modules": has_required,
            "missing_modules": list(required_types - module_types),
            "passed": len(modules) >= self.MIN_MODULES_REQUIRED and has_required
        }
    
    async def execute(self, page_data: dict, context: dict) -> dict:
        """
        执行质量检查
        """
        # 1. 相似度检查
        similarity_result = await self.check_similarity(
            page_data["content"],
            context.get("existing_contents", [])
        )
        
        # 2. 信息增量检查
        value_result = await self.check_information_value(page_data)
        
        # 3. 综合判断
        passed = (
            not similarity_result["is_duplicate"] and
            value_result["passed"]
        )
        
        return {
            "passed": passed,
            "similarity_check": similarity_result,
            "value_check": value_result,
            "recommendation": self._generate_recommendation(
                similarity_result, value_result
            )
        }
    
    def _generate_recommendation(self, sim: dict, val: dict) -> str:
        if sim["is_duplicate"]:
            return f"Content too similar ({sim['max_similarity']:.1%}). Add unique information."
        if not val["passed"]:
            return f"Add more modules. Missing: {', '.join(val['missing_modules'])}"
        return "Quality check passed."
```

**工作量估算**: 2-3 天

---

### BUG-010: 归因分析缺少 ROI 回写

**优先级**: P3 (Low)  
**状态**: 🟡 Open  
**发现日期**: 2026-01-28  
**影响模块**: P3 - 转化追踪

#### 问题描述
当前的归因分析是基础实现，缺少 ROI 计算和回写到机会评分的功能。

#### 建议增强

```python
class ConversionTracker:
    async def calculate_roi(self, page_url: str, time_range: tuple) -> dict:
        """
        计算页面 ROI
        """
        # 1. 获取该页面的转化事件
        conversions = self.get_conversions_by_page(page_url, time_range)
        
        # 2. 计算收入 (假设有订单数据)
        revenue = sum([c.revenue for c in conversions if c.revenue])
        
        # 3. 计算成本 (内容生成 token 成本)
        cost = self.get_content_cost(page_url)
        
        # 4. ROI
        roi = (revenue - cost) / cost if cost > 0 else 0
        
        return {
            "page_url": page_url,
            "revenue": revenue,
            "cost": cost,
            "roi": roi,
            "conversion_count": len(conversions)
        }
    
    async def update_opportunity_score(self, page_url: str, roi: float):
        """
        将 ROI 回写到机会评分
        高 ROI 页面应该优先刷新和优化
        """
        # 更新 OpportunityScore 表
        # 或者调整 OpportunityScoringAgent 的权重
        pass
```

**工作量估算**: 3-5 天

---

## 🟢 次要 Bug (Minor Bugs)

### BUG-011: 部分表缺少索引

**优先级**: P2 (Medium)  
**状态**: 🟢 Open  
**发现日期**: 2026-01-28

#### 问题描述
部分数据库表缺少索引，可能影响查询性能。

#### 建议添加索引

```sql
-- gsc_queries 表
CREATE INDEX idx_gsc_queries_position ON gsc_queries(position);
CREATE INDEX idx_gsc_queries_impressions ON gsc_queries(impressions);
CREATE INDEX idx_gsc_queries_date_query ON gsc_queries(date, query);

-- job_runs 表
CREATE INDEX idx_job_runs_status ON job_runs(status);
CREATE INDEX idx_job_runs_started_at ON job_runs(started_at);
```

**工作量估算**: 1-2 小时

---

### BUG-012: WP MU 插件文档缺失

**优先级**: P1 (High)  
**状态**: 🟢 Open  
**发现日期**: 2026-01-28

#### 问题描述
缺少 WordPress MU 插件示例，用户不知道如何启用 Rank Math meta 的 REST API 访问。

#### 建议添加文档

**文件**: `docs/rank-math-mu-plugin.php`

```php
<?php
/**
 * Plugin Name: Rank Math REST API Enabler
 * Description: Enable Rank Math meta fields in WordPress REST API
 * Version: 1.0.0
 */

add_action('init', function() {
    // Register Rank Math meta fields for REST API
    $meta_fields = [
        'rank_math_title',
        'rank_math_description',
        'rank_math_focus_keyword',
        'rank_math_robots',
        'rank_math_canonical_url'
    ];
    
    foreach ($meta_fields as $field) {
        register_meta('post', $field, [
            'show_in_rest' => true,
            'single' => true,
            'type' => 'string',
            'auth_callback' => function() {
                return current_user_can('edit_posts');
            }
        ]);
    }
});
```

**安装说明**:
1. 将此文件复制到 `wp-content/mu-plugins/` 目录
2. 如果 `mu-plugins` 目录不存在，创建它
3. 无需激活，MU 插件自动加载

**工作量估算**: 30 分钟

---

### BUG-013: 蚕食检测仅基础实现

**优先级**: P2 (Medium)  
**状态**: 🟢 Open  
**发现日期**: 2026-01-28

#### 问题描述
当前的关键词蚕食检测过于简单，可能遗漏复杂的冲突情况。

#### 建议增强
- 基于 TF-IDF 的语义相似度检测
- 考虑 URL 结构相似度
- 分析 GSC 数据中的排名波动

**工作量估算**: 2-3 天

---

### BUG-014: Backlink Copilot 功能简化

**优先级**: P3 (Low)  
**状态**: 🟢 Open  
**发现日期**: 2026-01-28

#### 问题描述
Backlink Copilot 为基础实现，需要增强机会发现和 outreach 自动化。

#### 建议增强
- 集成 Ahrefs/SEMrush API 发现机会
- 自动化邮件发送 (SMTP 集成)
- CRM 式的状态跟踪

**工作量估算**: 5-7 天

---

## ⚙️ 配置问题 (Configuration Issues)

### CFG-001: .env 缺少 WordPress 配置

**优先级**: P0 (Critical)  
**状态**: ⚙️ Open

#### 问题
`.env` 文件缺少必要的 WordPress 配置。

#### 解决方案
在 `.env.example` 中添加:

```bash
# WordPress Integration (Required for P0)
WORDPRESS_URL=https://your-wordpress-site.com
WORDPRESS_USERNAME=your_wp_username
WORDPRESS_PASSWORD=your_wp_app_password
```

---

### CFG-002: .env 缺少 Redis 配置

**优先级**: P1 (High)  
**状态**: ⚙️ Open

#### 问题
`.env` 文件缺少 Redis 配置，且没有降级方案。

#### 解决方案
1. 在 `.env.example` 中添加:
```bash
# Redis (Optional - for caching and queue)
REDIS_URL=redis://localhost:6379/0
```

2. 在代码中添加降级逻辑:
```python
try:
    redis_client = redis.from_url(settings.redis_url)
    redis_client.ping()
except:
    logger.warning("Redis not available, using in-memory cache")
    redis_client = None  # 使用内存缓存
```

---

### CFG-003: 缺少示例配置文件

**优先级**: P1 (High)  
**状态**: ⚙️ Open

#### 问题
`.env.example` 不够完整，缺少详细说明。

#### 解决方案
完善 `.env.example`，添加所有必要配置和注释。

---

## 📊 Bug 统计

### 按优先级

- **P0 (Critical)**: 3 个
- **P1 (High)**: 6 个
- **P2 (Medium)**: 4 个
- **P3 (Low)**: 2 个
- **配置问题**: 3 个

### 按状态

- **🔴 Open**: 5 个 (严重)
- **🟡 Open**: 5 个 (重要)
- **🟢 Open**: 4 个 (次要)
- **⚙️ Open**: 3 个 (配置)

### 按模块

- **P0 基础发布**: 3 个
- **P1 GSC 驱动**: 5 个
- **P2 pSEO 工厂**: 4 个
- **P3 转化闭环**: 2 个
- **基础设施**: 1 个
- **配置**: 3 个

---

## 🎯 修复优先级建议

### 本周 (Week 1)
1. CFG-001, CFG-002, CFG-003 - 配置问题
2. BUG-001 - SEO 自检接口
3. BUG-002 - content_actions 表
4. BUG-012 - WP MU 插件文档

### 下周 (Week 2)
5. BUG-003 - 机会池界面
6. BUG-006 - 审计日志增强
7. BUG-007 - GSC 状态页
8. BUG-011 - 数据库索引

### 两周后 (Week 3-4)
9. BUG-004 - 发布队列控制
10. BUG-008 - TopicMap 增强
11. BUG-009 - QualityGate 增强
12. BUG-013 - 蚕食检测增强

### 一个月后 (Month 1)
13. BUG-005 - 索引监控
14. BUG-010 - ROI 回写
15. BUG-014 - Backlink Copilot 增强

---

**文档维护者**: Antigravity AI  
**最后更新**: 2026-01-28  
**下次审查**: 2026-02-04
