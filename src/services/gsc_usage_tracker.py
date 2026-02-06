"""
GSC API Usage Tracking Service

Monitors and manages GSC API quota consumption
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.gsc_data import GSCApiUsage, GSCQuotaStatus

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
        
        # Update breakdown by type
        breakdown = self.get_usage_by_type(days=1)
        import json
        quota.usage_breakdown = json.dumps(breakdown)
        
        # Update status
        quota.update_status()
        
        self.db.commit()
        
        # Check if alert needed
        if quota.status in ["warning", "critical", "exceeded"]:
            if not quota.last_alert_sent or \
               (datetime.now() - quota.last_alert_sent) >= timedelta(hours=1):
                self._send_quota_alert(quota)
    
    def _send_quota_alert(self, quota: GSCQuotaStatus):
        """Send quota alert notification"""
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
        
        import json
        return {
            "date": quota.quota_date.isoformat(),
            "daily_limit": quota.daily_limit,
            "used_today": quota.used_today,
            "remaining": quota.remaining,
            "usage_percentage": quota.usage_percentage,
            "status": quota.status,
            "breakdown": json.loads(quota.usage_breakdown) if quota.usage_breakdown else {}
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
        from_date = date.today() - timedelta(days=days)
        
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
                "api_calls": r.total_calls or 0,
                "rows_fetched": r.total_rows or 0,
                "avg_response_time_ms": round(r.avg_response_time, 2) if r.avg_response_time else 0
            }
            for r in results
        ]
    
    def get_usage_by_type(self, days: int = 7) -> Dict[str, int]:
        """Get usage breakdown by call type"""
        from_date = date.today() - timedelta(days=days)
        
        results = self.db.query(
            GSCApiUsage.call_type,
            func.sum(GSCApiUsage.api_calls).label('total_calls')
        ).filter(
            GSCApiUsage.usage_date >= from_date
        ).group_by(
            GSCApiUsage.call_type
        ).all()
        
        return {r.call_type: r.total_calls or 0 for r in results}
