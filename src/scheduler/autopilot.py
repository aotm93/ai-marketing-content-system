"""
Autopilot Scheduler
Implements P0-8: Automated scheduling with APScheduler

Features:
- Cron-based scheduling for content generation
- Interval-based publishing
- Dynamic schedule updates
- Integration with job runner
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None

from .job_runner import JobConfig, JobStatus, get_job_runner

logger = logging.getLogger(__name__)


class AutopilotMode(str, Enum):
    """Autopilot operation modes"""
    STOPPED = "stopped"
    CONSERVATIVE = "conservative"  # Low frequency, high quality checks
    STANDARD = "standard"         # Balanced
    AGGRESSIVE = "aggressive"     # High frequency, faster publishing


@dataclass
class AutopilotConfig:
    """
    Autopilot configuration
    
    Implements P0-13: Autopilot parameters with recommended values
    """
    # Core settings
    enabled: bool = False
    mode: AutopilotMode = AutopilotMode.STANDARD
    
    # Frequency controls (with recommended values)
    publish_interval_minutes: int = 60  # Recommended: 30-120 for standard mode
    max_posts_per_day: int = 5          # Recommended: 3-10 depending on niche
    max_concurrent_agents: int = 2       # Recommended: 1-3 to avoid API limits
    
    # Publishing behavior
    auto_publish: bool = False          # Recommended: False (human review)
    default_status: str = "draft"       # draft, pending, publish
    
    # Quality controls
    require_seo_score: int = 60         # Minimum SEO score (0-100)
    require_word_count: int = 500       # Minimum content word count
    
    # Cost protection
    max_tokens_per_day: int = 100000    # Daily token consumption limit
    pause_on_errors: int = 3            # Pause autopilot after N consecutive errors
    
    # Schedule (cron format)
    active_hours_start: int = 8         # Start hour (0-23)
    active_hours_end: int = 22          # End hour (0-23)
    active_days: str = "mon-fri"        # Days of week: mon-sun or specific
    
    @classmethod
    def from_mode(cls, mode: AutopilotMode) -> "AutopilotConfig":
        """Create config from predefined mode"""
        if mode == AutopilotMode.CONSERVATIVE:
            return cls(
                enabled=True,
                mode=mode,
                publish_interval_minutes=120,
                max_posts_per_day=3,
                max_concurrent_agents=1,
                auto_publish=False,
                require_seo_score=70,
                require_word_count=800
            )
        elif mode == AutopilotMode.AGGRESSIVE:
            return cls(
                enabled=True,
                mode=mode,
                publish_interval_minutes=30,
                max_posts_per_day=15,
                max_concurrent_agents=3,
                auto_publish=True,
                require_seo_score=50,
                require_word_count=300
            )
        else:  # STANDARD
            return cls(
                enabled=True,
                mode=mode,
                publish_interval_minutes=60,
                max_posts_per_day=5,
                max_concurrent_agents=2,
                auto_publish=False,
                require_seo_score=60,
                require_word_count=500
            )
    
    def to_job_config(self) -> JobConfig:
        """Convert to JobConfig for job runner"""
        return JobConfig(
            max_posts_per_day=self.max_posts_per_day,
            publish_interval_minutes=self.publish_interval_minutes,
            max_concurrent_jobs=self.max_concurrent_agents,
            max_tokens_per_day=self.max_tokens_per_day,
            auto_publish=self.auto_publish
        )
    
    def get_recommendations(self) -> Dict[str, str]:
        """Get recommendations for each parameter"""
        return {
            "publish_interval_minutes": "推荐值: 30-120分钟。间隔太短可能触发搜索引擎的内容质量检查。",
            "max_posts_per_day": "推荐值: 3-10篇/天。新站建议从低频开始，逐步增加。",
            "max_concurrent_agents": "推荐值: 1-3。过高可能导致API限流或成本飙升。",
            "auto_publish": "推荐: 关闭。建议人工审核后再发布，确保内容质量。",
            "require_seo_score": "推荐值: 60-80。低于60的内容SEO效果可能不佳。",
            "require_word_count": "推荐值: 500-1500词。太短可能难以获得排名。",
            "max_tokens_per_day": "推荐值: 根据预算设置。GPT-4约$30/100K tokens。",
            "pause_on_errors": "推荐值: 3-5次。连续错误时自动暂停以避免资源浪费。"
        }


class AutopilotScheduler:
    """
    Main Autopilot scheduler
    
    Manages automated content generation and publishing cycles
    """
    
    def __init__(self, config: Optional[AutopilotConfig] = None):
        """
        Initialize Autopilot scheduler
        
        Args:
            config: Autopilot configuration
        """
        if not APSCHEDULER_AVAILABLE:
            logger.warning("APScheduler not installed. Install with: pip install apscheduler")
            self.scheduler = None
        else:
            self.scheduler = AsyncIOScheduler(
                jobstores={"default": MemoryJobStore()},
                job_defaults={"coalesce": True, "max_instances": 1}
            )
        
        self.config = config or AutopilotConfig()
        self.job_runner = get_job_runner()
        self.job_runner.update_config(self.config.to_job_config())
        
        self._consecutive_errors = 0
        self._total_runs = 0
        self._successful_runs = 0
        self._last_run: Optional[datetime] = None
        self._last_error_reset_date: date = date.today()
        self._paused_by_errors: bool = False
        
        # Registered job functions
        self._job_functions: Dict[str, Callable] = {}
        
        logger.info("AutopilotScheduler initialized")
    
    def register_job(self, job_type: str, job_func: Callable):
        """
        Register a job function for scheduled execution
        
        Args:
            job_type: Unique identifier for the job type
            job_func: Async function to execute
        """
        self._job_functions[job_type] = job_func
        logger.info(f"Registered job type: {job_type}")
    
    def update_config(self, config: AutopilotConfig):
        """Update autopilot configuration"""
        self.config = config
        self.job_runner.update_config(config.to_job_config())
        
        # Reschedule if running
        if self.config.enabled and self.scheduler and self.scheduler.running:
            self._reschedule_jobs()
        
        logger.info(f"Autopilot config updated: mode={config.mode}")
    
    def start(self):
        """Start the autopilot scheduler"""
        if not self.scheduler:
            logger.error("Scheduler not available (APScheduler not installed)")
            return
        
        if not self.config.enabled:
            logger.warning("Autopilot is disabled in config")
            return
        
        if self.scheduler.running:
            logger.warning("Scheduler already running")
            return
        
        self._schedule_jobs()
        self.scheduler.start()
        self.job_runner.enable()
        
        logger.info("Autopilot scheduler started")
    
    def stop(self):
        """Stop the autopilot scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.job_runner.disable()
            logger.info("Autopilot scheduler stopped")
    
    def pause(self):
        """Pause the scheduler without shutting down"""
        if self.scheduler:
            self.scheduler.pause()
            logger.info("Autopilot scheduler paused")
    
    def resume(self):
        """Resume a paused scheduler"""
        if self.scheduler:
            self.scheduler.resume()
            logger.info("Autopilot scheduler resumed")
    
    def _schedule_jobs(self):
        """Set up scheduled jobs based on config"""
        if not self.scheduler:
            return
        
        # Clear existing jobs
        self.scheduler.remove_all_jobs()
        
        # Main content generation job (interval-based)
        self.scheduler.add_job(
            self._run_generation_cycle,
            IntervalTrigger(minutes=self.config.publish_interval_minutes),
            id="content_generation",
            name="Content Generation Cycle",
            replace_existing=True
        )
        
        # Daily summary job (once per day)
        self.scheduler.add_job(
            self._run_daily_summary,
            CronTrigger(hour=23, minute=55),
            id="daily_summary",
            name="Daily Summary",
            replace_existing=True
        )
        
        # Cannibalization scan (Weekly, Sunday at 3 AM)
        self.scheduler.add_job(
            self._run_cannibalization_scan,
            CronTrigger(day_of_week='sun', hour=3, minute=0),
            id="cannibalization_scan",
            name="Cannibalization Scan",
            replace_existing=True
        )
        
        logger.info(f"Scheduled jobs: interval={self.config.publish_interval_minutes}min")
    
    def _reschedule_jobs(self):
        """Reschedule jobs with updated config"""
        if not self.scheduler:
            return
        
        # Update interval for content generation
        self.scheduler.reschedule_job(
            "content_generation",
            trigger=IntervalTrigger(minutes=self.config.publish_interval_minutes)
        )
        
        logger.info(f"Jobs rescheduled: interval={self.config.publish_interval_minutes}min")
    
    async def _run_generation_cycle(self):
        """Execute one content generation cycle"""
        self._total_runs += 1
        self._last_run = datetime.now()

        logger.info(f"Starting generation cycle #{self._total_runs}")

        # Check if it's a new day - reset error counter and auto-resume if paused by errors
        today = date.today()
        if today > self._last_error_reset_date:
            logger.info(f"New day detected, resetting error counter (was {self._consecutive_errors})")
            self._consecutive_errors = 0
            self._last_error_reset_date = today

            # Auto-resume if paused by errors
            if self._paused_by_errors:
                logger.info("Auto-resuming scheduler after daily reset")
                self._paused_by_errors = False
                self.resume()

        # Check if within active hours
        current_hour = datetime.now().hour
        if not (self.config.active_hours_start <= current_hour < self.config.active_hours_end):
            logger.info(f"Outside active hours ({self.config.active_hours_start}-{self.config.active_hours_end})")
            return

        # Check consecutive errors threshold
        if self._consecutive_errors >= self.config.pause_on_errors:
            logger.warning(f"Paused due to {self._consecutive_errors} consecutive errors")
            self._paused_by_errors = True
            self.pause()
            return

        try:
            # Get the main generation job
            if "content_generation" in self._job_functions:
                job_func = self._job_functions["content_generation"]
                result = await self.job_runner.run_job(
                    job_type="content_generation",
                    job_func=job_func,
                    job_data={"config": self.config}
                )

                # Only count actual errors, not rate limiting
                if result.status == JobStatus.SUCCESS:
                    self._successful_runs += 1
                    self._consecutive_errors = 0
                elif result.status == JobStatus.RATE_LIMITED:
                    # Rate limiting is expected behavior, not an error
                    logger.debug("Rate limited - not counting as error")
                else:
                    # Real errors: FAILED, TIMEOUT, CANCELLED
                    self._consecutive_errors += 1

        except Exception as e:
            logger.error(f"Generation cycle failed: {e}")
            self._consecutive_errors += 1
    
    async def _run_daily_summary(self):
        """Generate daily performance summary"""
        logger.info("Generating daily summary")
        
        summary = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_runs": self._total_runs,
            "successful_runs": self._successful_runs,
            "success_rate": (self._successful_runs / self._total_runs * 100) if self._total_runs > 0 else 0,
            "rate_limiter_status": self.job_runner.get_status()["rate_limiter"],
            "consecutive_errors": self._consecutive_errors
        }
        
        logger.info(f"Daily summary: {summary}")
        
        # Reset daily counters
        self._total_runs = 0
        self._successful_runs = 0
        
        return summary
    
    async def _run_cannibalization_scan(self):
        """Execute cannibalization detection scan"""
        logger.info("Starting scheduled cannibalization scan")
        
        try:
            # Get the job function
            if "cannibalization_analysis" in self._job_functions:
                job_func = self._job_functions["cannibalization_analysis"]
                await self.job_runner.run_job(
                    job_type="cannibalization_analysis",
                    job_func=job_func,
                    job_data={"min_impressions": 50}
                )
            else:
                logger.warning("Cannibalization analysis job not registered")
                    
        except Exception as e:
            logger.error(f"Scheduled cannibalization scan failed: {e}")
    
    async def run_once(self, job_type: str = "content_generation", job_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run a job immediately (bypasses schedule)
        
        Implements P0-9: "立即运行一次" API
        
        Args:
            job_type: Type of job to run
            job_data: Optional data for the job
            
        Returns:
            Job execution result
        """
        if job_type not in self._job_functions:
            return {
                "status": "error",
                "message": f"Unknown job type: {job_type}",
                "available_jobs": list(self._job_functions.keys())
            }
        
        job_func = self._job_functions[job_type]
        result = await self.job_runner.run_now(
            job_type=job_type,
            job_func=job_func,
            job_data=job_data or {"config": self.config}
        )
        
        return result.to_dict()
    
    def get_status(self) -> Dict[str, Any]:
        """Get autopilot status"""
        return {
            "enabled": self.config.enabled,
            "mode": self.config.mode.value,
            "scheduler_running": self.scheduler.running if self.scheduler else False,
            "total_runs_today": self._total_runs,
            "successful_runs_today": self._successful_runs,
            "consecutive_errors": self._consecutive_errors,
            "paused_by_errors": self._paused_by_errors,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "last_error_reset_date": self._last_error_reset_date.isoformat(),
            "registered_jobs": list(self._job_functions.keys()),
            "job_runner_status": self.job_runner.get_status(),
            "config": {
                "publish_interval_minutes": self.config.publish_interval_minutes,
                "max_posts_per_day": self.config.max_posts_per_day,
                "auto_publish": self.config.auto_publish,
                "active_hours": f"{self.config.active_hours_start}:00-{self.config.active_hours_end}:00"
            }
        }
    
    def get_next_run_time(self) -> Optional[datetime]:
        """Get next scheduled run time"""
        if not self.scheduler or not self.scheduler.running:
            return None
        
        job = self.scheduler.get_job("content_generation")
        if job:
            return job.next_run_time
        return None


# Global autopilot instance
_autopilot: Optional[AutopilotScheduler] = None


def get_autopilot() -> AutopilotScheduler:
    """Get or create global autopilot instance"""
    global _autopilot
    if _autopilot is None:
        _autopilot = AutopilotScheduler()
    return _autopilot


def configure_autopilot(config: AutopilotConfig) -> AutopilotScheduler:
    """Configure the global autopilot"""
    global _autopilot
    _autopilot = AutopilotScheduler(config)
    return _autopilot
