"""
Job Runs Model
Implements P0-10: Database model for job execution auditing

Records every job execution with:
- Input parameters
- Output/result
- Errors and stack traces
- Timing information
- Retry count
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum as SQLEnum, Float
from enum import Enum
from typing import Dict, Any, Optional

from .base import Base, TimestampMixin


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    CANCELLED = "cancelled"


class JobRun(Base, TimestampMixin):
    """
    Job execution audit record
    
    Stores complete history of all job executions for:
    - Debugging failed jobs
    - Performance analysis
    - Usage tracking
    - Compliance/auditing
    """
    __tablename__ = "job_runs"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Job identification
    job_id = Column(String(36), unique=True, nullable=False, index=True)
    job_type = Column(String(100), nullable=False, index=True)
    job_name = Column(String(255), nullable=True)
    
    # Execution status  
    status = Column(
        SQLEnum(JobStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=JobStatus.PENDING,
        index=True
    )
    
    # Timing
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Input/Output
    input_data = Column(JSON, nullable=True)
    result_data = Column(JSON, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Resource usage
    tokens_used = Column(Integer, nullable=True)
    api_calls = Column(Integer, nullable=True)
    
    # Metadata
    triggered_by = Column(String(50), default="scheduler")  # scheduler, manual, api
    parent_job_id = Column(String(36), nullable=True)  # For chained jobs
    
    def __repr__(self):
        return f"<JobRun(id={self.id}, job_id={self.job_id}, type={self.job_type}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "job_type": self.job_type,
            "job_name": self.job_name,
            "status": self.status.value if self.status else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "tokens_used": self.tokens_used,
            "triggered_by": self.triggered_by,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_job_result(cls, result, input_data: Optional[Dict] = None, triggered_by: str = "scheduler") -> "JobRun":
        """Create JobRun from a JobResult object"""
        return cls(
            job_id=result.job_id,
            job_type=result.job_type,
            status=JobStatus(result.status.value),
            started_at=result.started_at,
            completed_at=result.completed_at,
            duration_seconds=result.duration_seconds,
            input_data=input_data,
            result_data=result.result_data,
            error_message=result.error_message,
            error_traceback=result.error_traceback,
            retry_count=result.retry_count,
            triggered_by=triggered_by
        )


class ContentAction(Base, TimestampMixin):
    """
    Content modification history
    
    Tracks all automated content changes for:
    - Before/after comparison
    - Rollback capability
    - Change auditing
    - Performance analysis (metrics before/after)
    
    Enhanced for P1: Content Refresh and CTR Optimization
    """
    __tablename__ = "content_actions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Action identification
    action_id = Column(String(36), unique=True, nullable=False, index=True)
    action_type = Column(String(50), nullable=False, index=True)  # refresh, ctr_optimize, title_update, create, update, delete, publish, seo_update
    
    # Target content
    post_id = Column(Integer, nullable=True, index=True)
    post_url = Column(String(512), nullable=True)
    post_title = Column(String(255), nullable=True)
    
    # Related query (for SEO optimizations)
    query = Column(String(255), nullable=True, index=True)  # The search query this optimization targets
    
    # Change details
    before_snapshot = Column(JSON, nullable=True)  # {title, description, content_excerpt, meta}
    after_snapshot = Column(JSON, nullable=True)   # {title, description, content_excerpt, meta}
    changes_summary = Column(Text, nullable=True)
    
    # Reason for change
    reason = Column(Text, nullable=True)  # Why this change was made (e.g., "Low CTR optimization", "Position 8-20 refresh")
    
    # Performance metrics (for analysis)
    metrics_before = Column(JSON, nullable=True)  # {position, ctr, impressions, clicks, date}
    metrics_after = Column(JSON, nullable=True)   # {position, ctr, impressions, clicks, date} - populated after time
    
    # Status
    status = Column(String(20), default="active", index=True)  # active, completed, failed, rolled_back, superseded
    
    # Rollback information
    rollback_at = Column(DateTime, nullable=True)
    rollback_by = Column(String(100), nullable=True)
    
    # Related job
    job_run_id = Column(Integer, nullable=True)
    
    # User tracking
    triggered_by = Column(String(50), default="system")  # system, manual, autopilot
    applied_by = Column(String(100), nullable=True)  # User or agent name
    
    def __repr__(self):
        return f"<ContentAction(id={self.id}, type={self.action_type}, post_id={self.post_id}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "post_id": self.post_id,
            "post_title": self.post_title,
            "query": self.query,
            "reason": self.reason,
            "changes_summary": self.changes_summary,
            "status": self.status,
            "metrics_before": self.metrics_before,
            "metrics_after": self.metrics_after,
            "rollback_at": self.rollback_at.isoformat() if self.rollback_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "triggered_by": self.triggered_by
        }
    
    def can_rollback(self) -> bool:
        """Check if this action can be rolled back"""
        return self.status == "active" and self.before_snapshot is not None
    
    def calculate_impact(self) -> Optional[Dict[str, Any]]:
        """Calculate the impact of this change based on metrics"""
        if not self.metrics_before or not self.metrics_after:
            return None
        
        before = self.metrics_before
        after = self.metrics_after
        
        return {
            "position_change": after.get("position", 0) - before.get("position", 0),
            "ctr_change": after.get("ctr", 0) - before.get("ctr", 0),
            "clicks_change": after.get("clicks", 0) - before.get("clicks", 0),
            "impressions_change": after.get("impressions", 0) - before.get("impressions", 0),
            "improvement_percentage": ((after.get("clicks", 0) - before.get("clicks", 0)) / before.get("clicks", 1)) * 100 if before.get("clicks", 0) > 0 else 0
        }


class AutopilotRun(Base, TimestampMixin):
    """
    Autopilot daily run summary
    
    Aggregated statistics for each autopilot run day
    """
    __tablename__ = "autopilot_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Date tracking
    run_date = Column(DateTime, nullable=False, unique=True, index=True)
    
    # Execution stats
    total_jobs = Column(Integer, default=0)
    successful_jobs = Column(Integer, default=0)
    failed_jobs = Column(Integer, default=0)
    rate_limited_jobs = Column(Integer, default=0)
    
    # Content stats
    posts_created = Column(Integer, default=0)
    posts_published = Column(Integer, default=0)
    posts_updated = Column(Integer, default=0)
    
    # Resource usage
    total_tokens_used = Column(Integer, default=0)
    total_api_calls = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    
    # Configuration snapshot
    config_snapshot = Column(JSON, nullable=True)
    
    # Errors
    error_count = Column(Integer, default=0)
    error_summary = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<AutopilotRun(date={self.run_date}, jobs={self.total_jobs}, success={self.successful_jobs})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_date": self.run_date.isoformat() if self.run_date else None,
            "total_jobs": self.total_jobs,
            "successful_jobs": self.successful_jobs,
            "failed_jobs": self.failed_jobs,
            "posts_created": self.posts_created,
            "posts_published": self.posts_published,
            "total_tokens_used": self.total_tokens_used,
            "estimated_cost_usd": self.estimated_cost_usd
        }
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_jobs == 0:
            return 0.0
        return (self.successful_jobs / self.total_jobs) * 100
