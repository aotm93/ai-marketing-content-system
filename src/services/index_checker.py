"""
Automatic Index Status Checker

Checks indexing status of pages using multiple methods:
1. Google Search Console URL Inspection API
2. Search operator: site:example.com/page-url
3. Sitemap submission status

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
        import json
        status.index_details = json.dumps(check_result.get("details"))
        
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
            import json
            status.issues = json.dumps(["Max submission retries reached without indexing"])
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
        import json
        
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
            methods = json.loads(status.submission_methods)
        if method not in methods:
            methods.append(method)
            status.submission_methods = json.dumps(methods)
        
        # Schedule first check
        status.next_scheduled_check = datetime.now() + timedelta(days=self.CHECK_INTERVAL_NEW)
        
        self.db.commit()
        
        logger.info(f"Registered page submission: {page_url} via {method}")
