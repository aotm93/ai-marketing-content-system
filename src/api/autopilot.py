"""
Autopilot API Endpoints
Implements P0-9, P0-11: Autopilot control and monitoring APIs

Provides:
- Start/stop/pause autopilot
- Configuration management
- Job execution history
- Manual job trigger ("立即运行一次")
- SEO integration self-check
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from src.core.auth import get_current_admin
from src.scheduler import AutopilotConfig, get_job_runner
from src.scheduler.autopilot import AutopilotMode, get_autopilot, configure_autopilot
from src.integrations import WordPressClient, WordPressAdapter
from src.config import settings

router = APIRouter(prefix="/api/v1/autopilot", tags=["autopilot"])


# ==================== Request/Response Models ====================

class AutopilotModeRequest(BaseModel):
    """Request to set autopilot mode"""
    mode: str = Field(..., description="Mode: conservative, standard, aggressive")


class AutopilotConfigRequest(BaseModel):
    """Full autopilot configuration"""
    enabled: bool = True
    mode: str = "standard"
    publish_interval_minutes: int = Field(60, ge=10, le=1440)
    max_posts_per_day: int = Field(5, ge=1, le=50)
    max_concurrent_agents: int = Field(2, ge=1, le=10)
    auto_publish: bool = False
    default_status: str = "draft"
    require_seo_score: int = Field(60, ge=0, le=100)
    require_word_count: int = Field(500, ge=100, le=5000)
    max_tokens_per_day: int = Field(100000, ge=1000)
    pause_on_errors: int = Field(3, ge=1, le=10)
    active_hours_start: int = Field(8, ge=0, le=23)
    active_hours_end: int = Field(22, ge=0, le=23)


class RunJobRequest(BaseModel):
    """Request to run a job immediately"""
    job_type: str = "content_generation"
    job_data: Optional[Dict[str, Any]] = None


class SEOCheckRequest(BaseModel):
    """Request DSL self-check"""
    post_id: Optional[int] = Field(None, description="Optional post ID to test with")


class AutopilotResponse(BaseModel):
    """Standard autopilot response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class JobHistoryResponse(BaseModel):
    """Job history response"""
    total: int
    jobs: List[Dict[str, Any]]


# ==================== Configuration Recommendations ====================

PARAM_RECOMMENDATIONS = {
    "publish_interval_minutes": {
        "default": 60,
        "range": "10-1440",
        "description": "内容发布间隔（分钟）",
        "recommendation": "推荐30-120分钟。太频繁可能触发搜索引擎质量审核。"
    },
    "max_posts_per_day": {
        "default": 5,
        "range": "1-50",
        "description": "每日最大发布数量",
        "recommendation": "新站推荐3-5篇/天，成熟站可提高到10-15篇。"
    },
    "max_concurrent_agents": {
        "default": 2,
        "range": "1-10",
        "description": "最大并发Agent数",
        "recommendation": "推荐1-3。过高可能导致API限流和成本飙升。"
    },
    "auto_publish": {
        "default": False,
        "description": "是否自动发布",
        "recommendation": "建议关闭，人工审核后再发布以确保质量。"
    },
    "require_seo_score": {
        "default": 60,
        "range": "0-100",
        "description": "最低SEO分数要求",
        "recommendation": "推荐60-80分。低于60的内容排名效果可能不佳。"
    },
    "require_word_count": {
        "default": 500,
        "range": "100-5000",
        "description": "最低内容字数",
        "recommendation": "推荐500-1500词。太短难以获得好排名。"
    },
    "max_tokens_per_day": {
        "default": 100000,
        "description": "每日Token消耗上限",
        "recommendation": "根据预算设置。GPT-4约$30/100K tokens。"
    },
    "pause_on_errors": {
        "default": 3,
        "range": "1-10",
        "description": "连续错误暂停阈值",
        "recommendation": "推荐3-5次。避免持续失败浪费资源。"
    }
}


# ==================== Endpoints ====================

@router.get("/status", response_model=AutopilotResponse)
async def get_autopilot_status(admin: dict = Depends(get_current_admin)):
    """
    Get current autopilot status
    
    Returns:
    - Running state
    - Current configuration
    - Statistics
    - Next scheduled run
    """
    autopilot = get_autopilot()
    status_data = autopilot.get_status()
    
    next_run = autopilot.get_next_run_time()
    if next_run:
        status_data["next_run_at"] = next_run.isoformat()
    
    return AutopilotResponse(
        success=True,
        message="Autopilot status retrieved",
        data=status_data
    )


@router.post("/start", response_model=AutopilotResponse)
async def start_autopilot(admin: dict = Depends(get_current_admin)):
    """Start the autopilot scheduler"""
    autopilot = get_autopilot()
    
    if not autopilot.config.enabled:
        return AutopilotResponse(
            success=False,
            message="Autopilot is disabled in configuration. Enable it first."
        )
    
    try:
        autopilot.start()
        return AutopilotResponse(
            success=True,
            message="Autopilot started successfully",
            data=autopilot.get_status()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start autopilot: {str(e)}"
        )


@router.post("/stop", response_model=AutopilotResponse)
async def stop_autopilot(admin: dict = Depends(get_current_admin)):
    """Stop the autopilot scheduler"""
    autopilot = get_autopilot()
    
    try:
        autopilot.stop()
        return AutopilotResponse(
            success=True,
            message="Autopilot stopped",
            data=autopilot.get_status()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop autopilot: {str(e)}"
        )


@router.post("/pause", response_model=AutopilotResponse)
async def pause_autopilot(admin: dict = Depends(get_current_admin)):
    """Pause the autopilot (can be resumed)"""
    autopilot = get_autopilot()
    autopilot.pause()
    
    return AutopilotResponse(
        success=True,
        message="Autopilot paused",
        data=autopilot.get_status()
    )


@router.post("/resume", response_model=AutopilotResponse)
async def resume_autopilot(admin: dict = Depends(get_current_admin)):
    """Resume a paused autopilot"""
    autopilot = get_autopilot()
    autopilot.resume()
    
    return AutopilotResponse(
        success=True,
        message="Autopilot resumed",
        data=autopilot.get_status()
    )


@router.post("/set-mode", response_model=AutopilotResponse)
async def set_autopilot_mode(
    request: AutopilotModeRequest,
    admin: dict = Depends(get_current_admin)
):
    """
    Set autopilot mode (simple mode)
    
    Modes:
    - conservative: Low frequency, high quality checks
    - standard: Balanced (recommended)
    - aggressive: High frequency, faster publishing
    """
    try:
        mode = AutopilotMode(request.mode)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode. Choose from: conservative, standard, aggressive"
        )
    
    config = AutopilotConfig.from_mode(mode)
    autopilot = configure_autopilot(config)
    
    return AutopilotResponse(
        success=True,
        message=f"Autopilot mode set to: {mode.value}",
        data={
            "mode": mode.value,
            "config": autopilot.get_status()["config"]
        }
    )


@router.get("/config", response_model=AutopilotResponse)
async def get_autopilot_config(admin: dict = Depends(get_current_admin)):
    """Get current autopilot configuration with recommendations"""
    autopilot = get_autopilot()
    config = autopilot.config
    
    return AutopilotResponse(
        success=True,
        message="Configuration retrieved",
        data={
            "current": {
                "enabled": config.enabled,
                "mode": config.mode.value,
                "publish_interval_minutes": config.publish_interval_minutes,
                "max_posts_per_day": config.max_posts_per_day,
                "max_concurrent_agents": config.max_concurrent_agents,
                "auto_publish": config.auto_publish,
                "default_status": config.default_status,
                "require_seo_score": config.require_seo_score,
                "require_word_count": config.require_word_count,
                "max_tokens_per_day": config.max_tokens_per_day,
                "pause_on_errors": config.pause_on_errors,
                "active_hours_start": config.active_hours_start,
                "active_hours_end": config.active_hours_end
            },
            "recommendations": PARAM_RECOMMENDATIONS
        }
    )


@router.put("/config", response_model=AutopilotResponse)
async def update_autopilot_config(
    request: AutopilotConfigRequest,
    admin: dict = Depends(get_current_admin)
):
    """Update autopilot configuration (expert mode)"""
    try:
        mode = AutopilotMode(request.mode)
    except ValueError:
        mode = AutopilotMode.STANDARD
    
    config = AutopilotConfig(
        enabled=request.enabled,
        mode=mode,
        publish_interval_minutes=request.publish_interval_minutes,
        max_posts_per_day=request.max_posts_per_day,
        max_concurrent_agents=request.max_concurrent_agents,
        auto_publish=request.auto_publish,
        default_status=request.default_status,
        require_seo_score=request.require_seo_score,
        require_word_count=request.require_word_count,
        max_tokens_per_day=request.max_tokens_per_day,
        pause_on_errors=request.pause_on_errors,
        active_hours_start=request.active_hours_start,
        active_hours_end=request.active_hours_end
    )
    
    autopilot = get_autopilot()
    autopilot.update_config(config)
    
    return AutopilotResponse(
        success=True,
        message="Configuration updated",
        data=autopilot.get_status()
    )


@router.post("/run-now", response_model=AutopilotResponse)
async def run_job_now(
    request: RunJobRequest,
    background_tasks: BackgroundTasks,
    admin: dict = Depends(get_current_admin)
):
    """
    Run a job immediately (P0-9: "立即运行一次")
    
    Bypasses rate limiting and scheduling.
    Useful for testing and manual content generation.
    """
    autopilot = get_autopilot()
    
    try:
        result = await autopilot.run_once(
            job_type=request.job_type,
            job_data=request.job_data
        )
        
        return AutopilotResponse(
            success=result.get("status") == "success",
            message=f"Job executed: {result.get('status')}",
            data=result
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job execution failed: {str(e)}"
        )


@router.get("/history", response_model=JobHistoryResponse)
async def get_job_history(
    limit: int = 20,
    status_filter: Optional[str] = None,
    admin: dict = Depends(get_current_admin)
):
    """
    Get job execution history (P0-11)
    
    Args:
        limit: Number of records to return (max 100)
        status_filter: Filter by status (success, failed, timeout)
    """
    job_runner = get_job_runner()
    history = job_runner.get_history(limit=min(limit, 100))
    
    if status_filter:
        history = [j for j in history if j.get("status") == status_filter]
    
    return JobHistoryResponse(
        total=len(history),
        jobs=history
    )


@router.get("/failed-jobs")
async def get_failed_jobs(
    limit: int = 10,
    admin: dict = Depends(get_current_admin)
):
    """Get recent failed jobs for analysis/retry"""
    job_runner = get_job_runner()
    failed = job_runner.get_failed_jobs(limit=limit)
    
    return {
        "total": len(failed),
        "jobs": failed
    }


@router.post("/retry-job/{job_id}")
async def retry_failed_job(
    job_id: str,
    admin: dict = Depends(get_current_admin)
):
    """
    Retry a failed job
    
    Retrieves the failed job from history and re-executes it.
    Useful for retrying jobs that failed due to transient errors.
    """
    from src.scheduler.jobs import JOB_REGISTRY
    
    job_runner = get_job_runner()
    
    # Find the failed job in history
    failed_jobs = job_runner.get_failed_jobs(limit=50)
    target_job = None
    
    for job in failed_jobs:
        if job.get("job_id") == job_id:
            target_job = job
            break
    
    if not target_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found in failed jobs history"
        )
    
    job_type = target_job.get("job_type")
    
    # Get the job function from registry
    if job_type not in JOB_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job type '{job_type}' not found in registry"
        )
    
    job_func = JOB_REGISTRY[job_type]
    
    # Get original job data if available, otherwise use empty config
    original_data = target_job.get("result_data", {}).get("original_data", {})
    if not original_data:
        original_data = {"config": {}}
    
    try:
        # Execute the job immediately (bypassing rate limit for retry)
        result = await job_runner.run_now(
            job_type=job_type,
            job_func=job_func,
            job_data=original_data
        )
        
        return {
            "success": result.status.value == "success",
            "message": f"Job {job_id} retry {'succeeded' if result.status.value == 'success' else 'failed'}",
            "job_id": job_id,
            "new_job_id": result.job_id,
            "result": result.to_dict()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retry execution failed: {str(e)}"
        )


# ==================== SEO Integration Check ====================

@router.post("/seo-check", response_model=AutopilotResponse)
async def seo_integration_check(
    request: SEOCheckRequest,
    admin: dict = Depends(get_current_admin)
):
    """
    SEO integration self-check (P0-5)
    
    Tests:
    - WordPress connection
    - Authentication
    - Rank Math meta writing
    - Rank Math meta reading
    """
    try:
        # Create adapter with current settings
        adapter = WordPressAdapter(
            base_url=settings.wordpress_url,
            username=settings.wordpress_username,
            password=settings.wordpress_password,
            seo_plugin=getattr(settings, 'seo_plugin', 'rank_math')
        )
        
        health = await adapter.health_check()
        
        return AutopilotResponse(
            success=health.get("wordpress", {}).get("status") == "connected",
            message="SEO integration check completed",
            data=health
        )
        
    except Exception as e:
        return AutopilotResponse(
            success=False,
            message=f"SEO check failed: {str(e)}",
            data={"error": str(e)}
        )


@router.get("/wordpress-health")
async def wordpress_health_check(admin: dict = Depends(get_current_admin)):
    """Quick WordPress connection health check"""
    try:
        client = WordPressClient(
            base_url=settings.wordpress_url,
            username=settings.wordpress_username,
            password=settings.wordpress_password
        )
        
        health = await client.health_check()
        
        return {
            "success": health.get("status") == "connected",
            "data": health
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
