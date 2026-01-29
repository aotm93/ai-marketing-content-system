# BUG-004 & BUG-005 实现方案 (Implementation Plan)

**文档版本**: 1.0  
**创建日期**: 2026-01-28  
**状态**: 待实现

---

## 🔧 BUG-004: 发布队列控制功能实现方案

### 概述

实现批量发布任务的暂停、恢复、取消和回滚功能，提供完整的队列控制能力。

### 实现步骤

#### 步骤 1: 更新 BatchJobQueue 类

**文件**: `src/pseo/page_factory.py`

```python
from enum import Enum
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class BatchStatus(str, Enum):
    """批量任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class BatchJobQueue:
    """
    批量任务队列管理器
    支持暂停、恢复、取消和回滚
    """
    
    def __init__(self):
        self.jobs: Dict[str, dict] = {}
        self.status: Dict[str, BatchStatus] = {}
        self.published_posts: Dict[str, List[int]] = {}  # batch_id -> [post_ids]
    
    def create_batch(self, batch_id: str, config: dict) -> dict:
        """创建新的批量任务"""
        self.jobs[batch_id] = {
            "batch_id": batch_id,
            "config": config,
            "created_at": datetime.now(),
            "total_pages": 0,
            "completed_pages": 0,
            "failed_pages": 0
        }
        self.status[batch_id] = BatchStatus.PENDING
        self.published_posts[batch_id] = []
        
        return {"batch_id": batch_id, "status": "created"}
    
    def pause_batch(self, batch_id: str) -> dict:
        """
        暂停批量任务
        
        Args:
            batch_id: 批量任务 ID
            
        Returns:
            操作结果
        """
        if batch_id not in self.status:
            return {"success": False, "error": "Batch not found"}
        
        current_status = self.status[batch_id]
        
        if current_status != BatchStatus.RUNNING:
            return {
                "success": False,
                "error": f"Cannot pause batch in {current_status} status"
            }
        
        self.status[batch_id] = BatchStatus.PAUSED
        logger.info(f"Batch {batch_id} paused")
        
        return {
            "success": True,
            "batch_id": batch_id,
            "status": "paused",
            "message": "Batch paused successfully"
        }
    
    def resume_batch(self, batch_id: str) -> dict:
        """
        恢复批量任务
        
        Args:
            batch_id: 批量任务 ID
            
        Returns:
            操作结果
        """
        if batch_id not in self.status:
            return {"success": False, "error": "Batch not found"}
        
        current_status = self.status[batch_id]
        
        if current_status != BatchStatus.PAUSED:
            return {
                "success": False,
                "error": f"Cannot resume batch in {current_status} status"
            }
        
        self.status[batch_id] = BatchStatus.RUNNING
        logger.info(f"Batch {batch_id} resumed")
        
        return {
            "success": True,
            "batch_id": batch_id,
            "status": "running",
            "message": "Batch resumed successfully"
        }
    
    def cancel_batch(self, batch_id: str) -> dict:
        """
        取消批量任务
        
        Args:
            batch_id: 批量任务 ID
            
        Returns:
            操作结果
        """
        if batch_id not in self.status:
            return {"success": False, "error": "Batch not found"}
        
        current_status = self.status[batch_id]
        
        if current_status in [BatchStatus.COMPLETED, BatchStatus.CANCELLED]:
            return {
                "success": False,
                "error": f"Cannot cancel batch in {current_status} status"
            }
        
        self.status[batch_id] = BatchStatus.CANCELLED
        logger.info(f"Batch {batch_id} cancelled")
        
        return {
            "success": True,
            "batch_id": batch_id,
            "status": "cancelled",
            "message": "Batch cancelled successfully"
        }
    
    async def rollback_batch(
        self, 
        batch_id: str, 
        wp_client,
        action: str = "draft"  # "draft" or "delete"
    ) -> dict:
        """
        回滚批量发布
        
        Args:
            batch_id: 批量任务 ID
            wp_client: WordPress 客户端
            action: 回滚操作 ("draft" 改为草稿, "delete" 删除)
            
        Returns:
            回滚结果
        """
        if batch_id not in self.published_posts:
            return {"success": False, "error": "Batch not found"}
        
        published_ids = self.published_posts[batch_id]
        
        if not published_ids:
            return {
                "success": True,
                "message": "No posts to rollback",
                "processed": 0
            }
        
        results = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "errors": []
        }
        
        for post_id in published_ids:
            results["processed"] += 1
            
            try:
                if action == "delete":
                    # 删除文章
                    await wp_client.delete_post(post_id)
                else:
                    # 改为草稿
                    await wp_client.update_post(post_id, {"status": "draft"})
                
                results["succeeded"] += 1
                logger.info(f"Rolled back post {post_id} ({action})")
                
            except Exception as e:
                results["failed"] += 1
                error_msg = f"Post {post_id}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(f"Failed to rollback post {post_id}: {e}")
        
        # 记录回滚操作
        self.jobs[batch_id]["rollback_at"] = datetime.now()
        self.jobs[batch_id]["rollback_action"] = action
        self.jobs[batch_id]["rollback_results"] = results
        
        return {
            "success": results["failed"] == 0,
            "batch_id": batch_id,
            "action": action,
            "results": results,
            "message": f"Rollback completed: {results['succeeded']} succeeded, {results['failed']} failed"
        }
    
    def get_batch_status(self, batch_id: str) -> Optional[dict]:
        """获取批量任务状态"""
        if batch_id not in self.jobs:
            return None
        
        job = self.jobs[batch_id]
        status = self.status.get(batch_id, BatchStatus.PENDING)
        published_count = len(self.published_posts.get(batch_id, []))
        
        return {
            "batch_id": batch_id,
            "status": status.value,
            "created_at": job["created_at"].isoformat(),
            "total_pages": job["total_pages"],
            "completed_pages": job["completed_pages"],
            "failed_pages": job["failed_pages"],
            "published_count": published_count,
            "can_pause": status == BatchStatus.RUNNING,
            "can_resume": status == BatchStatus.PAUSED,
            "can_cancel": status in [BatchStatus.PENDING, BatchStatus.RUNNING, BatchStatus.PAUSED],
            "can_rollback": published_count > 0
        }
```

#### 步骤 2: 添加 API 端点

**文件**: `src/api/pseo.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from src.core.auth import get_current_admin

router = APIRouter(prefix="/api/v1/pseo", tags=["pseo"])


class BatchControlRequest(BaseModel):
    """批量任务控制请求"""
    action: Optional[str] = "draft"  # For rollback: "draft" or "delete"


@router.post("/batch/{batch_id}/pause")
async def pause_batch(
    batch_id: str,
    admin: dict = Depends(get_current_admin)
):
    """暂停批量任务"""
    from src.pseo.page_factory import BatchJobQueue
    
    queue = BatchJobQueue()
    result = queue.pause_batch(batch_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/batch/{batch_id}/resume")
async def resume_batch(
    batch_id: str,
    admin: dict = Depends(get_current_admin)
):
    """恢复批量任务"""
    from src.pseo.page_factory import BatchJobQueue
    
    queue = BatchJobQueue()
    result = queue.resume_batch(batch_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/batch/{batch_id}/cancel")
async def cancel_batch(
    batch_id: str,
    admin: dict = Depends(get_current_admin)
):
    """取消批量任务"""
    from src.pseo.page_factory import BatchJobQueue
    
    queue = BatchJobQueue()
    result = queue.cancel_batch(batch_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/batch/{batch_id}/rollback")
async def rollback_batch(
    batch_id: str,
    request: BatchControlRequest,
    admin: dict = Depends(get_current_admin)
):
    """回滚批量发布"""
    from src.pseo.page_factory import BatchJobQueue
    from src.integrations.wordpress_client import WordPressClient
    from src.config import settings
    
    queue = BatchJobQueue()
    wp_client = WordPressClient(
        url=settings.wordpress_url,
        username=settings.wordpress_username,
        password=settings.wordpress_password
    )
    
    result = await queue.rollback_batch(
        batch_id,
        wp_client,
        action=request.action
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("message"))
    
    return result


@router.get("/batch/{batch_id}/status")
async def get_batch_status(
    batch_id: str,
    admin: dict = Depends(get_current_admin)
):
    """获取批量任务状态"""
    from src.pseo.page_factory import BatchJobQueue
    
    queue = BatchJobQueue()
    status = queue.get_batch_status(batch_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return status
```

#### 步骤 3: 前端集成 (Admin Panel)

**位置**: `static/admin/` 或 Dashboard

```javascript
// 批量任务控制函数
async function pauseBatch(batchId) {
    const response = await fetch(`/api/v1/pseo/batch/${batchId}/pause`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${getToken()}`,
            'Content-Type': 'application/json'
        }
    });
    
    const result = await response.json();
    if (result.success) {
        alert('Batch paused successfully');
        refreshBatchStatus(batchId);
    } else {
        alert(`Error: ${result.error}`);
    }
}

async function resumeBatch(batchId) {
    // 类似 pauseBatch
}

async function cancelBatch(batchId) {
    if (!confirm('Are you sure you want to cancel this batch?')) {
        return;
    }
    // 类似 pauseBatch
}

async function rollbackBatch(batchId, action = 'draft') {
    if (!confirm(`Are you sure you want to rollback this batch? Action: ${action}`)) {
        return;
    }
    
    const response = await fetch(`/api/v1/pseo/batch/${batchId}/rollback`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${getToken()}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action })
    });
    
    const result = await response.json();
    alert(result.message);
    refreshBatchStatus(batchId);
}
```

---

## 🔧 BUG-005: 索引监控实现方案

### 概述

实现 IndexNow 集成、站点地图提交和收录状态监控功能。

### 实现步骤

#### 步骤 1: IndexNow 客户端

**文件**: `src/integrations/indexnow.py` (新建)

```python
"""
IndexNow API 客户端
支持快速索引通知到 Bing, Google, Yandex 等搜索引擎
"""
import httpx
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class IndexNowClient:
    """
    IndexNow API 客户端
    
    IndexNow 是一个协议，允许网站所有者即时通知搜索引擎
    网站内容的更新，加速索引过程。
    
    支持的搜索引擎:
    - Bing
    - Yandex
    - IndexNow.org (转发到多个引擎)
    """
    
    # IndexNow 端点
    ENDPOINTS = [
        "https://www.bing.com/indexnow",
        "https://api.indexnow.org/indexnow",
        "https://yandex.com/indexnow"
    ]
    
    def __init__(self, api_key: str, host: str):
        """
        初始化 IndexNow 客户端
        
        Args:
            api_key: IndexNow API 密钥 (任意字符串，需要在网站根目录放置同名文件)
            host: 网站主机名 (例如: example.com)
        """
        self.api_key = api_key
        self.host = host
    
    async def submit_url(self, url: str) -> Dict[str, Any]:
        """
        提交单个 URL
        
        Args:
            url: 要提交的 URL
            
        Returns:
            提交结果
        """
        return await self.submit_urls([url])
    
    async def submit_urls(self, urls: List[str]) -> Dict[str, Any]:
        """
        批量提交 URL
        
        Args:
            urls: URL 列表 (最多 10,000 个)
            
        Returns:
            提交结果
        """
        if not urls:
            return {"success": False, "error": "No URLs provided"}
        
        if len(urls) > 10000:
            return {"success": False, "error": "Too many URLs (max 10,000)"}
        
        # 构建请求 payload
        payload = {
            "host": self.host,
            "key": self.api_key,
            "urlList": urls
        }
        
        results = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint in self.ENDPOINTS:
                try:
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers={"Content-Type": "application/json; charset=utf-8"}
                    )
                    
                    results.append({
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "success": response.status_code == 200,
                        "response": response.text if response.status_code != 200 else "OK"
                    })
                    
                    logger.info(f"IndexNow submitted to {endpoint}: {response.status_code}")
                    
                except Exception as e:
                    results.append({
                        "endpoint": endpoint,
                        "success": False,
                        "error": str(e)
                    })
                    logger.error(f"IndexNow submission failed for {endpoint}: {e}")
        
        # 判断整体成功
        success_count = sum(1 for r in results if r.get("success"))
        
        return {
            "success": success_count > 0,
            "submitted_urls": len(urls),
            "endpoints_succeeded": success_count,
            "endpoints_total": len(self.ENDPOINTS),
            "results": results
        }
    
    def generate_key_file_content(self) -> str:
        """
        生成 API 密钥文件内容
        
        需要在网站根目录创建一个与 API 密钥同名的文本文件
        例如: https://example.com/your-api-key.txt
        
        Returns:
            文件内容 (就是 API 密钥本身)
        """
        return self.api_key
```

#### 步骤 2: 站点地图管理器

**文件**: `src/integrations/sitemap_manager.py` (新建)

```python
"""
站点地图管理器
自动生成和提交站点地图
"""
from typing import List, Dict, Any
from datetime import datetime
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)


class SitemapManager:
    """站点地图管理器"""
    
    def __init__(self, site_url: str):
        """
        初始化站点地图管理器
        
        Args:
            site_url: 网站 URL (例如: https://example.com)
        """
        self.site_url = site_url.rstrip('/')
    
    def generate_sitemap_xml(self, urls: List[Dict[str, Any]]) -> str:
        """
        生成站点地图 XML
        
        Args:
            urls: URL 列表，每个包含:
                - loc: URL 地址
                - lastmod: 最后修改时间 (可选)
                - changefreq: 更新频率 (可选)
                - priority: 优先级 (可选)
        
        Returns:
            XML 字符串
        """
        # 创建根元素
        urlset = ET.Element('urlset')
        urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
        
        for url_data in urls:
            url_elem = ET.SubElement(urlset, 'url')
            
            # loc (必需)
            loc = ET.SubElement(url_elem, 'loc')
            loc.text = url_data['loc']
            
            # lastmod (可选)
            if 'lastmod' in url_data:
                lastmod = ET.SubElement(url_elem, 'lastmod')
                if isinstance(url_data['lastmod'], datetime):
                    lastmod.text = url_data['lastmod'].strftime('%Y-%m-%d')
                else:
                    lastmod.text = url_data['lastmod']
            
            # changefreq (可选)
            if 'changefreq' in url_data:
                changefreq = ET.SubElement(url_elem, 'changefreq')
                changefreq.text = url_data['changefreq']
            
            # priority (可选)
            if 'priority' in url_data:
                priority = ET.SubElement(url_elem, 'priority')
                priority.text = str(url_data['priority'])
        
        # 转换为字符串
        xml_str = ET.tostring(urlset, encoding='unicode', method='xml')
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'
    
    async def submit_to_gsc(self, sitemap_url: str, gsc_client) -> Dict[str, Any]:
        """
        提交站点地图到 Google Search Console
        
        Args:
            sitemap_url: 站点地图 URL
            gsc_client: GSC 客户端
            
        Returns:
            提交结果
        """
        try:
            # 使用 GSC API 提交站点地图
            # https://developers.google.com/webmaster-tools/v1/sitemaps/submit
            result = await gsc_client.submit_sitemap(sitemap_url)
            
            return {
                "success": True,
                "sitemap_url": sitemap_url,
                "message": "Sitemap submitted to GSC successfully"
            }
        except Exception as e:
            logger.error(f"Failed to submit sitemap to GSC: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def submit_to_bing(self, sitemap_url: str, api_key: str) -> Dict[str, Any]:
        """
        提交站点地图到 Bing Webmaster Tools
        
        Args:
            sitemap_url: 站点地图 URL
            api_key: Bing Webmaster API 密钥
            
        Returns:
            提交结果
        """
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlbatch?apikey={api_key}",
                    json={
                        "siteUrl": self.site_url,
                        "urlList": [sitemap_url]
                    }
                )
                
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response": response.json()
                }
        except Exception as e:
            logger.error(f"Failed to submit sitemap to Bing: {e}")
            return {
                "success": False,
                "error": str(e)
            }
```

#### 步骤 3: 收录监控

**文件**: `src/integrations/indexing_monitor.py` (新建)

```python
"""
收录监控
追踪页面索引状态
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class IndexingMonitor:
    """收录监控器"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def check_indexing_status(
        self,
        urls: List[str],
        gsc_client
    ) -> Dict[str, Any]:
        """
        检查 URL 收录状态
        
        Args:
            urls: URL 列表
            gsc_client: GSC 客户端
            
        Returns:
            收录状态
        """
        results = {
            "total": len(urls),
            "indexed": 0,
            "not_indexed": 0,
            "details": []
        }
        
        for url in urls:
            try:
                # 使用 GSC URL Inspection API
                inspection = await gsc_client.inspect_url(url)
                
                is_indexed = inspection.get("indexStatusResult", {}).get("verdict") == "PASS"
                
                results["details"].append({
                    "url": url,
                    "indexed": is_indexed,
                    "last_crawl": inspection.get("indexStatusResult", {}).get("lastCrawlTime"),
                    "coverage_state": inspection.get("indexStatusResult", {}).get("coverageState")
                })
                
                if is_indexed:
                    results["indexed"] += 1
                else:
                    results["not_indexed"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to check indexing for {url}: {e}")
                results["details"].append({
                    "url": url,
                    "error": str(e)
                })
        
        results["indexing_rate"] = (results["indexed"] / results["total"] * 100) if results["total"] > 0 else 0
        
        return results
    
    def get_indexing_trend(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取收录趋势
        
        Args:
            days: 天数
            
        Returns:
            趋势数据
        """
        # 从数据库查询历史收录数据
        # 这需要一个专门的表来存储收录历史
        
        # 示例返回
        return {
            "period_days": days,
            "data_points": [
                {"date": "2026-01-01", "indexed": 100, "total": 150},
                {"date": "2026-01-15", "indexed": 120, "total": 160},
                {"date": "2026-01-28", "indexed": 145, "total": 170}
            ],
            "trend": "increasing"
        }
```

#### 步骤 4: API 端点

**文件**: `src/api/indexing.py` (新建)

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from src.core.auth import get_current_admin

router = APIRouter(prefix="/api/v1/indexing", tags=["indexing"])


class IndexNowRequest(BaseModel):
    """IndexNow 提交请求"""
    urls: List[str]


@router.post("/indexnow")
async def submit_to_indexnow(
    request: IndexNowRequest,
    admin: dict = Depends(get_current_admin)
):
    """提交 URL 到 IndexNow"""
    from src.integrations.indexnow import IndexNowClient
    from src.config import settings
    
    client = IndexNowClient(
        api_key=settings.indexnow_api_key,
        host=settings.site_domain
    )
    
    result = await client.submit_urls(request.urls)
    return result


@router.get("/status")
async def get_indexing_status(
    admin: dict = Depends(get_current_admin)
):
    """获取收录状态"""
    from src.integrations.indexing_monitor import IndexingMonitor
    from src.core.database import get_db
    
    db = next(get_db())
    monitor = IndexingMonitor(db)
    
    # 获取最近发布的页面
    # 这里需要从数据库查询
    
    return {
        "total_pages": 1000,
        "indexed_pages": 850,
        "indexing_rate": 85.0,
        "trend": "increasing"
    }
```

---

## 📝 总结

这两个 Bug 的实现方案已经详细规划，包括:

1. **BUG-004**: 完整的队列控制功能
   - 暂停/恢复/取消
   - 回滚功能
   - 状态追踪
   - API 端点
   - 前端集成

2. **BUG-005**: 完整的索引监控
   - IndexNow 集成
   - 站点地图管理
   - 收录状态监控
   - 趋势分析

**下一步**: 按照这些方案逐步实现即可。

---

**文档创建**: 2026-01-28  
**预计实现时间**: 1-2 周
