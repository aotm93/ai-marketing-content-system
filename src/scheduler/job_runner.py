"""
Job Runner
Implements P0-7: Unified job execution with rate limiting, concurrency control, and retry logic

Features:
- Rate limiting (posts per day, interval between posts)
- Concurrency control (max parallel jobs)
- Exponential backoff retry on failure
- Timeout handling
- Job auditing/logging
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
import traceback
import uuid

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    CANCELLED = "cancelled"


@dataclass
class JobConfig:
    """
    Job execution configuration (P0-13 parameters)
    
    These parameters can be configured via admin panel
    """
    # Frequency controls
    max_posts_per_day: int = 10
    publish_interval_minutes: int = 30
    
    # Concurrency
    max_concurrent_jobs: int = 3
    
    # Timeout
    job_timeout_seconds: int = 600  # 10 minutes
    
    # Retry with exponential backoff
    max_retries: int = 3
    retry_base_delay_seconds: int = 30
    retry_max_delay_seconds: int = 300
    
    # Cost control
    max_tokens_per_day: Optional[int] = None
    
    # Operation modes
    auto_publish: bool = False  # If False, create as draft
    require_review: bool = True  # If True, pause for manual review


@dataclass
class JobResult:
    """Result of a job execution"""
    job_id: str
    job_type: str
    status: JobStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    result_data: Dict[str, Any] = field(default_factory=dict)
    input_data: Dict[str, Any] = field(default_factory=dict)  # BUG-006: Added input snapshot
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    retry_count: int = 0
    tokens_used: Optional[int] = None  # BUG-006: Track token usage
    triggered_by: str = "scheduler"  # BUG-006: Track trigger source
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "retry_count": self.retry_count
        }


class RateLimiter:
    """
    Rate limiter for controlling job execution frequency
    """
    
    def __init__(self, max_per_day: int, interval_minutes: int):
        self.max_per_day = max_per_day
        self.interval_minutes = interval_minutes
        self.daily_count = 0
        self.last_execution: Optional[datetime] = None
        self.day_start: datetime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    def reset_if_new_day(self):
        """Reset daily counter if it's a new day"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if today > self.day_start:
            self.daily_count = 0
            self.day_start = today
            logger.info("Rate limiter: New day started, counters reset")
    
    def can_execute(self) -> tuple[bool, Optional[str]]:
        """
        Check if execution is allowed
        
        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
        """
        self.reset_if_new_day()
        
        # Check daily limit
        if self.daily_count >= self.max_per_day:
            return False, f"Daily limit reached ({self.max_per_day} posts/day)"
        
        # Check interval
        if self.last_execution:
            elapsed = (datetime.now() - self.last_execution).total_seconds() / 60
            if elapsed < self.interval_minutes:
                wait_time = self.interval_minutes - elapsed
                return False, f"Interval not met. Wait {wait_time:.1f} more minutes"
        
        return True, None
    
    def record_execution(self):
        """Record that an execution occurred"""
        self.daily_count += 1
        self.last_execution = datetime.now()
        logger.info(f"Rate limiter: Execution recorded ({self.daily_count}/{self.max_per_day} today)")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status"""
        self.reset_if_new_day()
        return {
            "daily_count": self.daily_count,
            "daily_limit": self.max_per_day,
            "remaining_today": self.max_per_day - self.daily_count,
            "interval_minutes": self.interval_minutes,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "next_allowed_at": (
                (self.last_execution + timedelta(minutes=self.interval_minutes)).isoformat()
                if self.last_execution else None
            )
        }


class JobRunner:
    """
    Unified job execution engine
    
    Manages:
    - Job execution with rate limiting
    - Concurrency control via semaphore
    - Retry logic with exponential backoff
    - Timeout handling
    - Result auditing
    """
    
    def __init__(self, config: Optional[JobConfig] = None):
        """
        Initialize job runner
        
        Args:
            config: Job configuration, uses defaults if not provided
        """
        self.config = config or JobConfig()
        self.rate_limiter = RateLimiter(
            max_per_day=self.config.max_posts_per_day,
            interval_minutes=self.config.publish_interval_minutes
        )
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent_jobs)
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self.job_history: List[JobResult] = []
        self._enabled = True
        
        logger.info(f"JobRunner initialized with config: {self.config}")
    
    def update_config(self, config: JobConfig):
        """Update runner configuration"""
        self.config = config
        self.rate_limiter = RateLimiter(
            max_per_day=config.max_posts_per_day,
            interval_minutes=config.publish_interval_minutes
        )
        self.semaphore = asyncio.Semaphore(config.max_concurrent_jobs)
        logger.info("JobRunner configuration updated")
    
    async def run_job(
        self,
        job_type: str,
        job_func: Callable,
        job_data: Dict[str, Any],
        skip_rate_limit: bool = False
    ) -> JobResult:
        """
        Execute a job with full management
        
        Args:
            job_type: Type of job (e.g., "content_generation", "publishing")
            job_func: Async function to execute
            job_data: Data to pass to job function
            skip_rate_limit: If True, bypass rate limiting (for manual triggers)
            
        Returns:
            JobResult with execution details
        """
        job_id = str(uuid.uuid4())[:8]
        started_at = datetime.now()
        
        logger.info(f"[{job_id}] Starting job: {job_type}")
        
        # Check if runner is enabled
        if not self._enabled:
            return JobResult(
                job_id=job_id,
                job_type=job_type,
                status=JobStatus.CANCELLED,
                started_at=started_at,
                completed_at=datetime.now(),
                error_message="JobRunner is disabled"
            )
        
        # Check rate limit
        if not skip_rate_limit:
            can_run, reason = self.rate_limiter.can_execute()
            if not can_run:
                logger.warning(f"[{job_id}] Rate limited: {reason}")
                return JobResult(
                    job_id=job_id,
                    job_type=job_type,
                    status=JobStatus.RATE_LIMITED,
                    started_at=started_at,
                    completed_at=datetime.now(),
                    error_message=reason
                )
        
        # Execute with concurrency control
        result = await self._execute_with_retry(job_id, job_type, job_func, job_data, started_at)
        
        # BUG-006: Set input data for audit logging
        result.input_data = job_data
        result.triggered_by = "manual" if skip_rate_limit else "scheduler"
        
        # Record execution if successful
        if result.status == JobStatus.SUCCESS and not skip_rate_limit:
            self.rate_limiter.record_execution()
        
        # Store in history
        self.job_history.append(result)
        
        # Keep only last 100 results in memory
        if len(self.job_history) > 100:
            self.job_history = self.job_history[-100:]
        
        # BUG-006: Persist to database for audit logging
        await self._persist_job_result(result)
        
        return result
    
    async def _execute_with_retry(
        self,
        job_id: str,
        job_type: str,
        job_func: Callable,
        job_data: Dict[str, Any],
        started_at: datetime
    ) -> JobResult:
        """Execute job with retry logic"""
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.max_retries:
            try:
                async with self.semaphore:
                    # Execute with timeout
                    result_data = await asyncio.wait_for(
                        job_func(job_data),
                        timeout=self.config.job_timeout_seconds
                    )
                    
                    completed_at = datetime.now()
                    duration = (completed_at - started_at).total_seconds()
                    
                    logger.info(f"[{job_id}] Job completed successfully in {duration:.2f}s")
                    
                    return JobResult(
                        job_id=job_id,
                        job_type=job_type,
                        status=JobStatus.SUCCESS,
                        started_at=started_at,
                        completed_at=completed_at,
                        duration_seconds=duration,
                        result_data=result_data if isinstance(result_data, dict) else {"result": result_data},
                        retry_count=retry_count
                    )
                    
            except asyncio.TimeoutError:
                logger.error(f"[{job_id}] Job timed out after {self.config.job_timeout_seconds}s")
                return JobResult(
                    job_id=job_id,
                    job_type=job_type,
                    status=JobStatus.TIMEOUT,
                    started_at=started_at,
                    completed_at=datetime.now(),
                    duration_seconds=self.config.job_timeout_seconds,
                    error_message=f"Job timed out after {self.config.job_timeout_seconds} seconds",
                    retry_count=retry_count
                )
                
            except Exception as e:
                last_error = e
                retry_count += 1
                
                if retry_count <= self.config.max_retries:
                    # Calculate backoff delay
                    delay = min(
                        self.config.retry_base_delay_seconds * (2 ** (retry_count - 1)),
                        self.config.retry_max_delay_seconds
                    )
                    logger.warning(
                        f"[{job_id}] Job failed (attempt {retry_count}/{self.config.max_retries}), "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[{job_id}] Job failed after {retry_count} attempts: {e}")
        
        # All retries exhausted
        return JobResult(
            job_id=job_id,
            job_type=job_type,
            status=JobStatus.FAILED,
            started_at=started_at,
            completed_at=datetime.now(),
            error_message=str(last_error),
            error_traceback=traceback.format_exc(),
            retry_count=retry_count - 1
        )
    
    async def run_now(
        self,
        job_type: str,
        job_func: Callable,
        job_data: Dict[str, Any]
    ) -> JobResult:
        """
        Immediately run a job, bypassing rate limits
        
        This implements P0-9: "立即运行一次" API
        """
        return await self.run_job(job_type, job_func, job_data, skip_rate_limit=True)
    
    def enable(self):
        """Enable the job runner"""
        self._enabled = True
        logger.info("JobRunner enabled")
    
    def disable(self):
        """Disable the job runner"""
        self._enabled = False
        logger.info("JobRunner disabled")
    
    def is_enabled(self) -> bool:
        """Check if runner is enabled"""
        return self._enabled
    
    def get_status(self) -> Dict[str, Any]:
        """Get current runner status"""
        return {
            "enabled": self._enabled,
            "rate_limiter": self.rate_limiter.get_status(),
            "running_jobs": len(self.running_jobs),
            "max_concurrent": self.config.max_concurrent_jobs,
            "history_count": len(self.job_history),
            "config": {
                "max_posts_per_day": self.config.max_posts_per_day,
                "publish_interval_minutes": self.config.publish_interval_minutes,
                "max_concurrent_jobs": self.config.max_concurrent_jobs,
                "job_timeout_seconds": self.config.job_timeout_seconds,
                "max_retries": self.config.max_retries
            }
        }

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent job execution history"""
        return [job.to_dict() for job in self.job_history[-limit:]]
    
    def get_failed_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent failed jobs for retry"""
        failed = [
            job.to_dict() for job in self.job_history 
            if job.status in (JobStatus.FAILED, JobStatus.TIMEOUT)
        ]
        return failed[-limit:]
    
    async def _persist_job_result(self, result: JobResult):
        """
        BUG-006: Persist job result to database for audit logging
        
        Saves:
        - Input snapshot (job_data)
        - Output snapshot (result_data)
        - Error traceback
        - Retry count
        - Token usage
        """
        try:
            from src.core.database import SessionLocal
            from src.models.job_runs import JobRun, JobStatus as DBJobStatus
            
            db = SessionLocal()
            try:
                # Sanitize data to ensure JSON serialization
                import json

                def sanitize_for_json(data):
                    """Convert data to JSON-serializable format"""
                    if data is None:
                        return None
                    try:
                        # Try to serialize directly
                        json.dumps(data)
                        return data
                    except (TypeError, ValueError):
                        # If it fails, convert to string representation
                        if isinstance(data, dict):
                            return {k: sanitize_for_json(v) for k, v in data.items()}
                        elif isinstance(data, (list, tuple)):
                            return [sanitize_for_json(item) for item in data]
                        else:
                            return str(data)

                job_run = JobRun(
                    job_id=result.job_id,
                    job_type=result.job_type,
                    status=DBJobStatus(result.status.value),
                    started_at=result.started_at,
                    completed_at=result.completed_at,
                    duration_seconds=result.duration_seconds,
                    input_data=sanitize_for_json(result.input_data),
                    result_data=sanitize_for_json(result.result_data),
                    error_message=result.error_message,
                    error_traceback=result.error_traceback,
                    retry_count=result.retry_count,
                    tokens_used=result.tokens_used,
                    triggered_by=result.triggered_by
                )
                
                db.add(job_run)
                db.commit()
                
                logger.debug(f"[{result.job_id}] Job result persisted to database")
                
            except Exception as e:
                db.rollback()
                logger.warning(f"[{result.job_id}] Failed to persist job result: {e}")
            finally:
                db.close()
                
        except ImportError:
            # Database not available, skip persistence
            logger.debug(f"[{result.job_id}] Database not available, skipping persistence")


# Global job runner instance
_job_runner: Optional[JobRunner] = None


def get_job_runner() -> JobRunner:
    """Get or create global job runner instance"""
    global _job_runner
    if _job_runner is None:
        _job_runner = JobRunner()
    return _job_runner


def configure_job_runner(config: JobConfig) -> JobRunner:
    """Configure the global job runner"""
    global _job_runner
    _job_runner = JobRunner(config)
    return _job_runner
