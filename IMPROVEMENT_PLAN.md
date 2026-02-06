# 高优先级改进方案

> 基于代码分析的详细实施方案

**改进项**:
1. 添加GSC每日使用量统计表
2. 实现自动索引状态检查

**分析日期**: 2026-02-06  
**基于代码**: src/models/gsc_data.py, src/pseo/indexing.py

---

## 改进一：添加GSC每日使用量统计表

### 📊 问题分析

**当前状况**:
- GSC API有每日2000次的配额限制
- 系统目前无法追踪每日使用量
- 无法预警配额不足
- 多个任务可能同时竞争配额

**需要解决**:
1. 记录每次GSC API调用
2. 统计每日使用量
3. 提供配额预警
4. 支持配额分配和限流

### 🏗️ 数据模型设计

#### 1. 创建新模型 `GSCApiUsage`

**文件**: `src/models/gsc_data.py` (添加到现有文件末尾)

```python
class GSCApiUsage(Base, TimestampMixin):
    """
    GSC API Usage Tracking
    
    Tracks daily API quota consumption for:
    - Quota monitoring and alerting
    - Cost optimization
    - Usage pattern analysis
    - Rate limiting
    """
    __tablename__ = "gsc_api_usage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Date tracking (daily granularity)
    usage_date = Column(Date, nullable=False, index=True)
    
    # API call details
    call_type = Column(String(50), nullable=False, index=True)
    # Types: search_analytics, sites_list, url_inspection, sitemap_submit
    
    # Usage metrics
    rows_fetched = Column(Integer, default=0)  # Number of data rows returned
    api_calls = Column(Integer, default=1)  # Number of API calls (usually 1 per operation)
    
    # Cost estimation (GSC API is free, but track for analysis)
    estimated_cost = Column(Float, default=0.0)  # USD
    
    # Operation details
    site_url = Column(String(255), nullable=True)
    date_range_start = Column(Date, nullable=True)
    date_range_end = Column(Date, nullable=True)
    
    # Performance
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    
    # Status
    success = Column(Integer, default=1)  # 1 = success, 0 = failed
    error_message = Column(Text, nullable=True)
    
    # Source tracking
    triggered_by = Column(String(50), default="system")  # autopilot, manual, scheduled_task
    job_run_id = Column(String(36), nullable=True)  # Link to job_runs table
    
    __table_args__ = (
        Index('ix_gsc_usage_date_type', 'usage_date', 'call_type'),
        Index('ix_gsc_usage_site_date', 'site_url', 'usage_date'),
    )
    
    def __repr__(self):
        return f"<GSCApiUsage(date={self.usage_date}, type={self.call_type}, rows={self.rows_fetched})>"
```

#### 2. 创建配额监控模型 `GSCQuotaStatus`

```python
class GSCQuotaStatus(Base, TimestampMixin):
    """
    GSC API Quota Status
    
    Daily quota tracking and alerting
    """
    __tablename__ = "gsc_quota_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Date
    quota_date = Column(Date, nullable=False, unique=True, index=True)
    
    # Daily quota (Google's limit: 2000 calls/day)
    daily_limit = Column(Integer, default=2000)
    used_today = Column(Integer, default=0)
    remaining = Column(Integer, default=2000)
    
    # Breakdown by call type
    usage_breakdown = Column(Text, nullable=True)  # JSON: {"search_analytics": 1500, "sites_list": 100}
    
    # Alert thresholds
    warning_threshold = Column(Integer, default=1600)  # 80%
    critical_threshold = Column(Integer, default=1800)  # 90%
    
    # Status
    status = Column(String(20), default="healthy")  # healthy, warning, critical, exceeded
    last_alert_sent = Column(DateTime, nullable=True)
    
    # Projections
    projected_usage = Column(Integer, nullable=True)  # Projected usage by end of day
    
    def __repr__(self):
        return f"<GSCQuotaStatus(date={self.quota_date}, used={self.used_today}, status={self.status})>"
    
    @property
    def usage_percentage(self) -> float:
        """Calculate usage percentage"""
        if self.daily_limit == 0:
            return 0.0
        return round((self.used_today / self.daily_limit) * 100, 1)
    
    def update_status(self):
        """Update status based on thresholds"""
        usage_pct = self.usage_percentage
        
        if usage_pct >= 100:
            self.status = "exceeded"
        elif usage_pct >= 90:
            self.status = "critical"
        elif usage_pct >= 80:
            self.status = "warning"
        else:
            self.status = "healthy"
```

### 🔧 服务层实现

#### 3. 创建 `GSCUsageTracker` 服务

**文件**: `src/services/gsc_usage_tracker.py` (新建)

```python
"""
GSC API Usage Tracking Service

Monitors and manages GSC API quota consumption
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.gsc_data import GSCApiUsage, GSCQuotaStatus
from src.core.database import get_db

logger = logging.getLogger(__name__)


class GSCUsageTracker:
    """
    Track and manage GSC API usage
    
    Features:
    - Log every API call
    - Track daily quota consumption
    - Provide quota status queries
    - Alert on quota limits
    - Support rate limiting
    """
    
    DEFAULT_DAILY_LIMIT = 2000  # Google's default limit
    WARNING_THRESHOLD = 0.80  # 80%
    CRITICAL_THRESHOLD = 0.90  # 90%
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_api_call(
        self,
        call_type: str,
        rows_fetched: int = 0,
        site_url: str = None,
        date_range: tuple = None,
        response_time_ms: int = None,
        success: bool = True,
        error_message: str = None,
        triggered_by: str = "system",
        job_run_id: str = None
    ) -> GSCApiUsage:
        """
        Log a GSC API call
        
        Args:
            call_type: Type of API call (search_analytics, sites_list, etc.)
            rows_fetched: Number of data rows returned
            site_url: Site URL
            date_range: (start_date, end_date) tuple
            response_time_ms: API response time
            success: Whether call succeeded
            error_message: Error message if failed
            triggered_by: What triggered the call
            job_run_id: Associated job ID
            
        Returns:
            GSCApiUsage record
        """
        usage = GSCApiUsage(
            usage_date=date.today(),
            call_type=call_type,
            rows_fetched=rows_fetched,
            api_calls=1,
            site_url=site_url,
            date_range_start=date_range[0] if date_range else None,
            date_range_end=date_range[1] if date_range else None,
            response_time_ms=response_time_ms,
            success=1 if success else 0,
            error_message=error_message,
            triggered_by=triggered_by,
            job_run_id=job_run_id
        )
        
        self.db.add(usage)
        self.db.commit()
        
        # Update quota status
        self._update_quota_status()
        
        logger.info(f"Logged GSC API call: {call_type}, rows={rows_fetched}")
        
        return usage
    
    def _update_quota_status(self):
        """Update daily quota status"""
        today = date.today()
        
        # Get or create quota status for today
        quota = self.db.query(GSCQuotaStatus).filter(
            GSCQuotaStatus.quota_date == today
        ).first()
        
        if not quota:
            quota = GSCQuotaStatus(quota_date=today)
            self.db.add(quota)
        
        # Calculate today's usage
        usage_stats = self.db.query(
            func.sum(GSCApiUsage.api_calls).label('total_calls'),
            func.sum(GSCApiUsage.rows_fetched).label('total_rows')
        ).filter(
            GSCApiUsage.usage_date == today,
            GSCApiUsage.success == 1
        ).first()
        
        quota.used_today = usage_stats.total_calls or 0
        quota.remaining = quota.daily_limit - quota.used_today
        
        # Update status
        quota.update_status()
        
        self.db.commit()
        
        # Check if alert needed
        if quota.status in ["warning", "critical", "exceeded"]:
            if not quota.last_alert_sent or \
               (datetime.now() - quota.last_alert_sent).hours >= 1:
                self._send_quota_alert(quota)
    
    def _send_quota_alert(self, quota: GSCQuotaStatus):
        """Send quota alert notification"""
        # TODO: Implement notification (email, webhook, etc.)
        logger.warning(
            f"GSC Quota Alert: {quota.status.upper()} - "
            f"Used {quota.used_today}/{quota.daily_limit} ({quota.usage_percentage}%)"
        )
        quota.last_alert_sent = datetime.now()
        self.db.commit()
    
    def get_quota_status(self, target_date: date = None) -> Dict[str, Any]:
        """
        Get quota status for a date
        
        Returns:
            Dict with quota information
        """
        target_date = target_date or date.today()
        
        quota = self.db.query(GSCQuotaStatus).filter(
            GSCQuotaStatus.quota_date == target_date
        ).first()
        
        if not quota:
            # No usage recorded yet today
            return {
                "date": target_date.isoformat(),
                "daily_limit": self.DEFAULT_DAILY_LIMIT,
                "used_today": 0,
                "remaining": self.DEFAULT_DAILY_LIMIT,
                "usage_percentage": 0.0,
                "status": "healthy"
            }
        
        return {
            "date": quota.quota_date.isoformat(),
            "daily_limit": quota.daily_limit,
            "used_today": quota.used_today,
            "remaining": quota.remaining,
            "usage_percentage": quota.usage_percentage,
            "status": quota.status,
            "breakdown": quota.usage_breakdown
        }
    
    def check_quota_available(self, required_calls: int = 1) -> bool:
        """
        Check if quota is available for N more API calls
        
        Args:
            required_calls: Number of API calls needed
            
        Returns:
            True if quota available, False otherwise
        """
        status = self.get_quota_status()
        return status["remaining"] >= required_calls
    
    def get_usage_history(
        self,
        days: int = 30,
        call_type: str = None
    ) -> list:
        """
        Get usage history for analysis
        
        Args:
            days: Number of days to look back
            call_type: Filter by call type (optional)
            
        Returns:
            List of daily usage stats
        """
        from_date = date.today() - __import__('datetime').timedelta(days=days)
        
        query = self.db.query(
            GSCApiUsage.usage_date,
            func.sum(GSCApiUsage.api_calls).label('total_calls'),
            func.sum(GSCApiUsage.rows_fetched).label('total_rows'),
            func.avg(GSCApiUsage.response_time_ms).label('avg_response_time')
        ).filter(
            GSCApiUsage.usage_date >= from_date
        )
        
        if call_type:
            query = query.filter(GSCApiUsage.call_type == call_type)
        
        results = query.group_by(
            GSCApiUsage.usage_date
        ).order_by(
            GSCApiUsage.usage_date.desc()
        ).all()
        
        return [
            {
                "date": r.usage_date.isoformat(),
                "api_calls": r.total_calls,
                "rows_fetched": r.total_rows,
                "avg_response_time_ms": round(r.avg_response_time, 2) if r.avg_response_time else 0
            }
            for r in results
        ]
    
    def get_usage_by_type(self, days: int = 7) -> Dict[str, int]:
        """Get usage breakdown by call type"""
        from_date = date.today() - __import__('datetime').timedelta(days=days)
        
        results = self.db.query(
            GSCApiUsage.call_type,
            func.sum(GSCApiUsage.api_calls).label('total_calls')
        ).filter(
            GSCApiUsage.usage_date >= from_date
        ).group_by(
            GSCApiUsage.call_type
        ).all()
        
        return {r.call_type: r.total_calls for r in results}
```

### 🔌 集成到GSC客户端

#### 4. 修改 `src/integrations/gsc_client.py`

在GSCClient的关键方法中添加使用追踪:

```python
class GSCClient:
    def __init__(self, ...):
        # ... existing init ...
        self.usage_tracker = None  # Will be injected
    
    def set_usage_tracker(self, tracker: GSCUsageTracker):
        """Inject usage tracker"""
        self.usage_tracker = tracker
    
    def get_search_analytics(self, ...):
        """Modified to track usage"""
        import time
        start_time = time.time()
        
        try:
            # ... existing API call ...
            response = self._service.searchanalytics().query(...).execute()
            
            rows = response.get('rows', [])
            
            # Track successful call
            if self.usage_tracker:
                self.usage_tracker.log_api_call(
                    call_type="search_analytics",
                    rows_fetched=len(rows),
                    site_url=self.site_url,
                    date_range=(start_date, end_date),
                    response_time_ms=int((time.time() - start_time) * 1000),
                    success=True
                )
            
            return rows
            
        except Exception as e:
            # Track failed call
            if self.usage_tracker:
                self.usage_tracker.log_api_call(
                    call_type="search_analytics",
                    site_url=self.site_url,
                    response_time_ms=int((time.time() - start_time) * 1000),
                    success=False,
                    error_message=str(e)
                )
            raise
```

### 📡 API端点

#### 5. 添加到 `src/api/gsc.py`

```python
@router.get("/quota")
async def get_quota_status(
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Get GSC API quota status and usage statistics
    
    Returns:
    - Current day's quota consumption
    - Usage percentage
    - Status (healthy/warning/critical/exceeded)
    - Historical usage trend
    """
    from src.services.gsc_usage_tracker import GSCUsageTracker
    
    tracker = GSCUsageTracker(db)
    
    # Current quota status
    quota = tracker.get_quota_status()
    
    # Last 7 days history
    history = tracker.get_usage_history(days=7)
    
    # Usage breakdown by type
    breakdown = tracker.get_usage_by_type(days=7)
    
    return {
        "current": quota,
        "history": history,
        "breakdown_by_type": breakdown,
        "recommendations": generate_quota_recommendations(quota)
    }

def generate_quota_recommendations(quota: dict) -> list:
    """Generate recommendations based on quota status"""
    recommendations = []
    
    if quota["status"] == "exceeded":
        recommendations.append("⚠️ Quota exceeded! Wait until tomorrow or request increased quota from Google")
    elif quota["status"] == "critical":
        recommendations.append("🚨 Quota at 90%+ - Reduce sync frequency or batch operations")
    elif quota["status"] == "warning":
        recommendations.append("⚡ Quota at 80%+ - Consider optimizing query patterns")
    
    if quota["usage_percentage"] > 50:
        recommendations.append("📊 Consider reviewing sync schedule to spread load")
    
    return recommendations

@router.get("/quota/history")
async def get_quota_history(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get detailed quota usage history"""
    from src.services.gsc_usage_tracker import GSCUsageTracker
    
    tracker = GSCUsageTracker(db)
    history = tracker.get_usage_history(days=days)
    
    return {
        "days": days,
        "data": history,
        "summary": {
            "total_calls": sum(d["api_calls"] for d in history),
            "total_rows": sum(d["rows_fetched"] for d in history),
            "avg_daily_calls": sum(d["api_calls"] for d in history) / len(history) if history else 0
        }
    }
```

### 🗄️ 数据库迁移

```bash
# 1. 生成迁移
python -m alembic revision -m "add_gsc_usage_tracking"

# 2. 编辑迁移文件，添加:
# - gsc_api_usage 表
# - gsc_quota_status 表

# 3. 执行迁移
python -m alembic upgrade head
```

### ✅ 验收标准

- [ ] GSCApiUsage模型创建
- [ ] GSCQuotaStatus模型创建
- [ ] GSCUsageTracker服务实现
- [ ] GSCClient集成使用追踪
- [ ] API端点 /quota 实现
- [ ] 配额预警功能工作
- [ ] 历史查询功能工作
- [ ] 数据库迁移成功执行

---

## 改进二：实现自动索引状态检查

### 📊 问题分析

**当前状况**:
- IndexNow只能提交URL，无法确认是否被索引
- 不知道页面是否真的被搜索引擎收录
- 无法识别长期未索引的问题页面
- 缺乏自动化的索引监控

**需要解决**:
1. 定期检查页面索引状态
2. 识别未索引页面并预警
3. 自动重新提交长期未索引页面
4. 提供索引覆盖率报告

### 🏗️ 数据模型扩展

#### 1. 扩展 `src/pseo/indexing.py` 的IndexMonitor

添加数据库存储支持:

```python
# 在 src/models/ 下创建新文件 indexing_status.py

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index
from datetime import datetime
from .base import Base, TimestampMixin

class IndexingStatus(Base, TimestampMixin):
    """
    Page indexing status tracking
    
    Tracks submission and indexing status for each page
    """
    __tablename__ = "indexing_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Page identification
    page_url = Column(String(1024), nullable=False, index=True)
    page_slug = Column(String(255), nullable=True)
    post_id = Column(Integer, nullable=True, index=True)  # WordPress post ID
    
    # Submission tracking
    first_submitted_at = Column(DateTime, nullable=True)
    last_submitted_at = Column(DateTime, nullable=True)
    submission_count = Column(Integer, default=0)
    submission_methods = Column(Text, nullable=True)  # JSON: ["indexnow", "sitemap"]
    
    # Indexing status
    is_indexed = Column(Boolean, nullable=True)  # None = unknown, True/False = checked
    last_checked_at = Column(DateTime, nullable=True)
    check_count = Column(Integer, default=0)
    
    # Indexing details (when checked)
    index_status = Column(String(50), nullable=True)  # indexed, not_indexed, error, pending
    index_details = Column(Text, nullable=True)  # JSON with check results
    
    # Google Search Console data (if available)
    gsc_discovered_date = Column(DateTime, nullable=True)
    gsc_last_crawl_date = Column(DateTime, nullable=True)
    gsc_crawl_status = Column(String(50), nullable=True)  # success, error, redirect
    
    # Auto-retry tracking
    auto_retry_count = Column(Integer, default=0)
    last_auto_retry_at = Column(DateTime, nullable=True)
    next_scheduled_check = Column(DateTime, nullable=True)
    
    # Issue tracking
    issues = Column(Text, nullable=True)  # JSON array of issues
    issue_severity = Column(String(20), default="none")  # none, low, medium, high
    
    __table_args__ = (
        Index('ix_indexing_status_post_id', 'post_id'),
        Index('ix_indexing_status_is_indexed', 'is_indexed'),
        Index('ix_indexing_status_next_check', 'next_scheduled_check'),
        Index('ix_indexing_status_url_date', 'page_url', 'last_checked_at'),
    )
    
    def __repr__(self):
        return f"<IndexingStatus(url='{self.page_url[:50]}...', indexed={self.is_indexed})>"
```

#### 2. 创建索引检查服务

**文件**: `src/services/index_checker.py` (新建)

```python
"""
Automatic Index Status Checker

Checks indexing status of pages using multiple methods:
1. Google Search Console URL Inspection API
2. Search operator: site:example.com/page-url
3. Sitemap submission status
4. Log file analysis (if available)

Provides automatic retry and alerting for non-indexed pages.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from src.models.indexing_status import IndexingStatus
from src.integrations.indexnow import IndexNowClient
from src.config import settings

logger = logging.getLogger(__name__)


class IndexChecker:
    """
    Automatic index status checker
    
    Features:
    - Multiple checking methods
    - Automatic retry for non-indexed pages
    - Coverage reporting
    - Alerting for issues
    """
    
    # Check intervals (in days)
    CHECK_INTERVAL_NEW = 3  # Check new pages after 3 days
    CHECK_INTERVAL_PENDING = 7  # Check pending pages weekly
    CHECK_INTERVAL_INDEXED = 30  # Check indexed pages monthly
    
    # Retry settings
    MAX_AUTO_RETRIES = 3
    RETRY_INTERVAL_DAYS = 7
    
    def __init__(self, db: Session):
        self.db = db
        self.indexnow = None
        if hasattr(settings, 'indexnow_api_key') and settings.indexnow_api_key:
            self.indexnow = IndexNowClient(
                api_key=settings.indexnow_api_key,
                host=settings.wordpress_url
            )
    
    async def check_page_index_status(
        self,
        page_url: str,
        method: str = "gsc"  # gsc, search_operator, logs
    ) -> Dict[str, Any]:
        """
        Check if a page is indexed
        
        Args:
            page_url: Full URL to check
            method: Checking method to use
            
        Returns:
            Dict with status and details
        """
        result = {
            "url": page_url,
            "checked_at": datetime.now().isoformat(),
            "method": method,
            "is_indexed": None,
            "status": "unknown",
            "details": {}
        }
        
        try:
            if method == "gsc":
                # Use GSC URL Inspection API
                result = await self._check_via_gsc(page_url)
            elif method == "search_operator":
                # Use search operator (not implemented - would require scraping)
                result = await self._check_via_search_operator(page_url)
            else:
                result["status"] = "error"
                result["error"] = f"Unknown method: {method}"
                
        except Exception as e:
            logger.error(f"Index check failed for {page_url}: {e}")
            result["status"] = "error"
            result["error"] = str(e)
        
        # Update database
        self._update_indexing_status(page_url, result)
        
        return result
    
    async def _check_via_gsc(self, page_url: str) -> Dict[str, Any]:
        """Check indexing status via GSC URL Inspection API"""
        # TODO: Implement GSC URL Inspection API call
        # This requires special API permissions from Google
        
        return {
            "url": page_url,
            "is_indexed": None,
            "status": "not_implemented",
            "details": {"message": "GSC URL Inspection API requires special access"}
        }
    
    async def _check_via_search_operator(self, page_url: str) -> Dict[str, Any]:
        """Check via search operator (requires SERP scraping)"""
        # This would require a service like SerpAPI or scraping
        # Not implementing for MVP - placeholder
        
        return {
            "url": page_url,
            "is_indexed": None,
            "status": "not_implemented",
            "details": {"message": "Search operator check not implemented"}
        }
    
    def _update_indexing_status(self, page_url: str, check_result: Dict[str, Any]):
        """Update indexing status in database"""
        status = self.db.query(IndexingStatus).filter(
            IndexingStatus.page_url == page_url
        ).first()
        
        if not status:
            status = IndexingStatus(page_url=page_url)
            self.db.add(status)
        
        # Update fields
        status.last_checked_at = datetime.now()
        status.check_count = (status.check_count or 0) + 1
        status.is_indexed = check_result.get("is_indexed")
        status.index_status = check_result.get("status")
        status.index_details = str(check_result.get("details"))
        
        # Schedule next check
        if status.is_indexed:
            status.next_scheduled_check = datetime.now() + timedelta(days=self.CHECK_INTERVAL_INDEXED)
        elif status.is_indexed is False:
            # Not indexed - check sooner
            status.next_scheduled_check = datetime.now() + timedelta(days=self.CHECK_INTERVAL_PENDING)
        else:
            # Unknown - check after new page interval
            status.next_scheduled_check = datetime.now() + timedelta(days=self.CHECK_INTERVAL_NEW)
        
        self.db.commit()
    
    async def run_scheduled_checks(self, batch_size: int = 50) -> Dict[str, Any]:
        """
        Run scheduled index checks for pages due
        
        This should be called by a scheduled job (e.g., daily)
        
        Returns:
            Summary of checks performed
        """
        now = datetime.now()
        
        # Get pages due for checking
        pages_to_check = self.db.query(IndexingStatus).filter(
            and_(
                IndexingStatus.next_scheduled_check <= now,
                IndexingStatus.check_count < 100  # Safety limit
            )
        ).limit(batch_size).all()
        
        results = {
            "checked": 0,
            "indexed": 0,
            "not_indexed": 0,
            "errors": 0,
            "urls": []
        }
        
        for page in pages_to_check:
            try:
                result = await self.check_page_index_status(page.page_url)
                results["checked"] += 1
                
                if result["is_indexed"] is True:
                    results["indexed"] += 1
                elif result["is_indexed"] is False:
                    results["not_indexed"] += 1
                    
                    # Auto-retry if needed
                    await self._auto_retry_if_needed(page)
                else:
                    results["errors"] += 1
                    
                results["urls"].append(page.page_url)
                
            except Exception as e:
                logger.error(f"Failed to check {page.page_url}: {e}")
                results["errors"] += 1
        
        return results
    
    async def _auto_retry_if_needed(self, status: IndexingStatus):
        """Auto-retry submission for non-indexed pages"""
        if status.auto_retry_count >= self.MAX_AUTO_RETRIES:
            logger.info(f"Max retries reached for {status.page_url}")
            status.issues = str(["Max submission retries reached without indexing"])
            status.issue_severity = "high"
            self.db.commit()
            return
        
        # Check if enough time has passed since last retry
        if status.last_auto_retry_at:
            days_since_retry = (datetime.now() - status.last_auto_retry_at).days
            if days_since_retry < self.RETRY_INTERVAL_DAYS:
                return
        
        # Re-submit via IndexNow
        if self.indexnow:
            try:
                result = await self.indexnow.submit_url(status.page_url)
                
                if result.get("success"):
                    status.auto_retry_count = (status.auto_retry_count or 0) + 1
                    status.last_auto_retry_at = datetime.now()
                    status.last_submitted_at = datetime.now()
                    status.submission_count = (status.submission_count or 0) + 1
                    
                    logger.info(f"Auto-retry submitted: {status.page_url}")
                    self.db.commit()
                    
            except Exception as e:
                logger.error(f"Auto-retry failed for {status.page_url}: {e}")
    
    def get_coverage_report(self) -> Dict[str, Any]:
        """Get indexing coverage report"""
        total = self.db.query(IndexingStatus).count()
        
        indexed = self.db.query(IndexingStatus).filter(
            IndexingStatus.is_indexed == True
        ).count()
        
        not_indexed = self.db.query(IndexingStatus).filter(
            IndexingStatus.is_indexed == False
        ).count()
        
        unknown = self.db.query(IndexingStatus).filter(
            IndexingStatus.is_indexed.is_(None)
        ).count()
        
        pending_retry = self.db.query(IndexingStatus).filter(
            IndexingStatus.auto_retry_count < self.MAX_AUTO_RETRIES,
            IndexingStatus.is_indexed == False
        ).count()
        
        issues = self.db.query(IndexingStatus).filter(
            IndexingStatus.issue_severity.in_(["medium", "high"])
        ).count()
        
        return {
            "total_pages": total,
            "indexed": indexed,
            "not_indexed": not_indexed,
            "unknown": unknown,
            "index_rate": round(indexed / total * 100, 2) if total > 0 else 0,
            "pending_retry": pending_retry,
            "pages_with_issues": issues,
            "last_updated": datetime.now().isoformat()
        }
    
    def get_pages_needing_attention(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get pages that need manual attention"""
        pages = self.db.query(IndexingStatus).filter(
            and_(
                IndexingStatus.is_indexed == False,
                IndexingStatus.auto_retry_count >= self.MAX_AUTO_RETRIES
            )
        ).order_by(
            IndexingStatus.first_submitted_at.asc()
        ).limit(limit).all()
        
        return [
            {
                "url": p.page_url,
                "first_submitted": p.first_submitted_at.isoformat() if p.first_submitted_at else None,
                "retry_count": p.auto_retry_count,
                "issues": p.issues
            }
            for p in pages
        ]
    
    def register_page_submission(
        self,
        page_url: str,
        post_id: int = None,
        method: str = "indexnow"
    ):
        """Register a page submission for tracking"""
        status = self.db.query(IndexingStatus).filter(
            IndexingStatus.page_url == page_url
        ).first()
        
        if not status:
            status = IndexingStatus(
                page_url=page_url,
                post_id=post_id,
                first_submitted_at=datetime.now()
            )
            self.db.add(status)
        
        status.last_submitted_at = datetime.now()
        status.submission_count = (status.submission_count or 0) + 1
        
        # Track submission methods
        methods = []
        if status.submission_methods:
            import json
            methods = json.loads(status.submission_methods)
        if method not in methods:
            methods.append(method)
            status.submission_methods = json.dumps(methods)
        
        # Schedule first check
        status.next_scheduled_check = datetime.now() + timedelta(days=self.CHECK_INTERVAL_NEW)
        
        self.db.commit()
        
        logger.info(f"Registered page submission: {page_url} via {method}")
```

### 🔌 集成到发布流程

#### 3. 修改 `src/pseo/page_factory.py`

在页面发布时自动注册索引追踪:

```python
# 在 BatchJobQueue.process_queue 中，发布成功后添加:

from src.services.index_checker import IndexChecker

# ... inside the publish loop ...
if pub_result.status == "success":
    # Register for index tracking
    index_checker = IndexChecker(db_session)
    index_checker.register_page_submission(
        page_url=f"{wordpress_url}/{content.slug}",
        post_id=pub_result.post_id,
        method="indexnow"
    )
    
    # Submit to IndexNow immediately
    if indexnow_client:
        await indexnow_client.submit_url(f"{wordpress_url}/{content.slug}")
```

### 📡 API端点

#### 4. 添加API端点

**文件**: `src/api/indexing.py` (新建或扩展)

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.auth import get_current_admin
from src.services.index_checker import IndexChecker

router = APIRouter(prefix="/api/v1/indexing", tags=["indexing"])

@router.get("/status")
async def get_indexing_status(
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get indexing coverage status"""
    checker = IndexChecker(db)
    return checker.get_coverage_report()

@router.get("/pages/attention")
async def get_pages_needing_attention(
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Get pages that need manual attention"""
    checker = IndexChecker(db)
    return checker.get_pages_needing_attention(limit)

@router.post("/check/{post_id}")
async def check_page_index_status(
    post_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Trigger index check for a specific page"""
    from src.models.indexing_status import IndexingStatus
    
    page = db.query(IndexingStatus).filter(
        IndexingStatus.post_id == post_id
    ).first()
    
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Run check in background
    checker = IndexChecker(db)
    background_tasks.add_task(
        checker.check_page_index_status,
        page.page_url
    )
    
    return {"status": "checking", "url": page.page_url}

@router.post("/check-all")
async def run_index_checks(
    batch_size: int = 50,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Run scheduled index checks"""
    checker = IndexChecker(db)
    results = await checker.run_scheduled_checks(batch_size)
    return results
```

### ⏰ 定时任务配置

#### 5. 添加到调度器

**文件**: `src/scheduler/jobs.py`

```python
async def scheduled_index_status_check():
    """Daily job to check indexing status"""
    from src.services.index_checker import IndexChecker
    from src.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        checker = IndexChecker(db)
        results = await checker.run_scheduled_checks(batch_size=100)
        
        logger.info(f"Index check completed: {results}")
        
        # Send alert if many pages not indexed
        coverage = checker.get_coverage_report()
        if coverage["index_rate"] < 50 and coverage["total_pages"] > 10:
            logger.warning(f"Low index rate: {coverage['index_rate']}%")
            # TODO: Send notification
            
    finally:
        db.close()

# Register in scheduler (daily at 2 AM)
scheduler.add_job(
    scheduled_index_status_check,
    'cron',
    hour=2,
    minute=0,
    id='index_status_check',
    replace_existing=True
)
```

### ✅ 验收标准

- [ ] IndexingStatus模型创建
- [ ] IndexChecker服务实现
- [ ] 自动检查逻辑工作
- [ ] 自动重试机制工作
- [ ] 覆盖率报告功能
- [ ] API端点实现
- [ ] 定时任务配置
- [ ] 数据库迁移成功

---

## 📊 实施优先级和时间线

### 第一周
1. **GSC使用量统计**
   - Day 1-2: 数据模型和迁移
   - Day 3-4: 服务层实现
   - Day 5: API端点和集成

### 第二周
2. **自动索引检查**
   - Day 1-2: 数据模型和基础服务
   - Day 3-4: 自动检查和重试逻辑
   - Day 5: API端点和调度配置

### 第三周
3. **测试和优化**
   - 集成测试
   - 性能优化
   - 文档更新

---

## 🎯 预期效果

### GSC使用量统计
- ✅ 实时监控API配额
- ✅ 预警避免配额耗尽
- ✅ 使用模式分析优化成本
- ✅ 问题追踪和调试

### 自动索引检查
- ✅ 自动发现未索引页面
- ✅ 减少人工检查工作
- ✅ 提高整体索引率
- ✅ 及时发现问题页面

---

**改进方案制定时间**: 2026-02-06  
**基于代码版本**: v4.1.0-fixed  
**预计实施时间**: 2-3周
