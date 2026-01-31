"""
Job Logs API
BUG-006: Enhanced Audit Logging - API Endpoints for viewing job execution history

Provides:
- List job runs with filtering and pagination
- Get detailed job run with input/output snapshots
- Get error statistics
- Retry failed jobs
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from src.core.database import get_db
from src.models.job_runs import JobRun, JobStatus
from src.core.auth import get_current_admin

router = APIRouter(prefix="/api/v1/job-logs", tags=["job-logs"])


class JobLogFilter(str, Enum):
    """Job log filter types"""
    ALL = "all"
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    

class JobLogSortBy(str, Enum):
    """Sort options"""
    STARTED_AT = "started_at"
    DURATION = "duration_seconds"
    JOB_TYPE = "job_type"
    STATUS = "status"


class JobLogResponse(BaseModel):
    """Response model for job log list"""
    id: int
    job_id: str
    job_type: str
    job_name: Optional[str]
    status: str
    started_at: str
    completed_at: Optional[str]
    duration_seconds: Optional[float]
    error_message: Optional[str]
    retry_count: int
    triggered_by: str
    tokens_used: Optional[int]
    
    class Config:
        from_attributes = True


class JobLogDetailResponse(BaseModel):
    """Detailed response model for single job log"""
    id: int
    job_id: str
    job_type: str
    job_name: Optional[str]
    status: str
    started_at: str
    completed_at: Optional[str]
    duration_seconds: Optional[float]
    input_snapshot: Optional[Dict[str, Any]]  # Renamed from input_data for clarity
    output_snapshot: Optional[Dict[str, Any]]  # Renamed from result_data for clarity
    error_message: Optional[str]
    error_traceback: Optional[str]
    retry_count: int
    triggered_by: str
    parent_job_id: Optional[str]
    tokens_used: Optional[int]
    api_calls: Optional[int]
    created_at: str
    
    class Config:
        from_attributes = True


class JobLogsListResponse(BaseModel):
    """Paginated job logs response"""
    success: bool
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[JobLogResponse]


class JobStatsResponse(BaseModel):
    """Job statistics response"""
    success: bool
    total_jobs: int
    successful: int
    failed: int
    running: int
    timeout: int
    rate_limited: int
    avg_duration_seconds: float
    success_rate: float
    total_tokens_used: int
    recent_errors: int


@router.get("/", response_model=JobLogsListResponse)
async def list_job_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    filter_status: Optional[JobLogFilter] = Query(None, description="Filter by status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    sort_by: JobLogSortBy = Query(JobLogSortBy.STARTED_AT, description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    days: int = Query(7, ge=1, le=90, description="Days to look back"),
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    List job execution logs with filtering and pagination
    
    Features:
    - Filter by status, job type
    - Pagination support
    - Sorting options
    - Date range filtering
    """
    try:
        # Build base query
        query = db.query(JobRun)
        
        # Apply date filter
        cutoff_date = datetime.now() - timedelta(days=days)
        query = query.filter(JobRun.started_at >= cutoff_date)
        
        # Apply status filter
        if filter_status and filter_status != JobLogFilter.ALL:
            status_map = {
                JobLogFilter.SUCCESS: JobStatus.SUCCESS,
                JobLogFilter.FAILED: JobStatus.FAILED,
                JobLogFilter.RUNNING: JobStatus.RUNNING,
                JobLogFilter.TIMEOUT: JobStatus.TIMEOUT,
                JobLogFilter.RATE_LIMITED: JobStatus.RATE_LIMITED,
            }
            if filter_status in status_map:
                query = query.filter(JobRun.status == status_map[filter_status])
        
        # Apply job type filter
        if job_type:
            query = query.filter(JobRun.job_type == job_type)
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        sort_column = getattr(JobRun, sort_by.value, JobRun.started_at)
        if sort_desc:
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Apply pagination
        offset = (page - 1) * page_size
        jobs = query.offset(offset).limit(page_size).all()
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        # Convert to response format
        items = []
        for job in jobs:
            items.append(JobLogResponse(
                id=job.id,
                job_id=job.job_id,
                job_type=job.job_type,
                job_name=job.job_name,
                status=job.status.value if job.status else "unknown",
                started_at=job.started_at.isoformat() if job.started_at else "",
                completed_at=job.completed_at.isoformat() if job.completed_at else None,
                duration_seconds=job.duration_seconds,
                error_message=job.error_message,
                retry_count=job.retry_count or 0,
                triggered_by=job.triggered_by or "system",
                tokens_used=job.tokens_used
            ))
        
        return JobLogsListResponse(
            success=True,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            items=items
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch job logs: {str(e)}"
        )


@router.get("/stats", response_model=JobStatsResponse)
async def get_job_stats(
    days: int = Query(7, ge=1, le=90, description="Days to analyze"),
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get job execution statistics
    
    Returns aggregated stats for debugging and monitoring:
    - Success/failure counts
    - Average duration
    - Token usage
    - Recent error count
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get counts by status
        total = db.query(JobRun).filter(JobRun.started_at >= cutoff_date).count()
        successful = db.query(JobRun).filter(
            JobRun.started_at >= cutoff_date,
            JobRun.status == JobStatus.SUCCESS
        ).count()
        failed = db.query(JobRun).filter(
            JobRun.started_at >= cutoff_date,
            JobRun.status == JobStatus.FAILED
        ).count()
        running = db.query(JobRun).filter(
            JobRun.started_at >= cutoff_date,
            JobRun.status == JobStatus.RUNNING
        ).count()
        timeout = db.query(JobRun).filter(
            JobRun.started_at >= cutoff_date,
            JobRun.status == JobStatus.TIMEOUT
        ).count()
        rate_limited = db.query(JobRun).filter(
            JobRun.started_at >= cutoff_date,
            JobRun.status == JobStatus.RATE_LIMITED
        ).count()
        
        # Calculate average duration
        avg_duration_result = db.query(func.avg(JobRun.duration_seconds)).filter(
            JobRun.started_at >= cutoff_date,
            JobRun.duration_seconds.isnot(None)
        ).scalar()
        avg_duration = float(avg_duration_result) if avg_duration_result else 0.0
        
        # Calculate total tokens
        total_tokens_result = db.query(func.sum(JobRun.tokens_used)).filter(
            JobRun.started_at >= cutoff_date,
            JobRun.tokens_used.isnot(None)
        ).scalar()
        total_tokens = int(total_tokens_result) if total_tokens_result else 0
        
        # Recent errors (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        recent_errors = db.query(JobRun).filter(
            JobRun.started_at >= yesterday,
            JobRun.status.in_([JobStatus.FAILED, JobStatus.TIMEOUT])
        ).count()
        
        # Calculate success rate
        success_rate = (successful / total * 100) if total > 0 else 0.0
        
        return JobStatsResponse(
            success=True,
            total_jobs=total,
            successful=successful,
            failed=failed,
            running=running,
            timeout=timeout,
            rate_limited=rate_limited,
            avg_duration_seconds=round(avg_duration, 2),
            success_rate=round(success_rate, 2),
            total_tokens_used=total_tokens,
            recent_errors=recent_errors
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job stats: {str(e)}"
        )


@router.get("/{job_id}", response_model=JobLogDetailResponse)
async def get_job_detail(
    job_id: str,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed job log including input/output snapshots and error traceback
    
    This implements the core BUG-006 requirement for viewing detailed audit logs
    """
    try:
        job = db.query(JobRun).filter(JobRun.job_id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return JobLogDetailResponse(
            id=job.id,
            job_id=job.job_id,
            job_type=job.job_type,
            job_name=job.job_name,
            status=job.status.value if job.status else "unknown",
            started_at=job.started_at.isoformat() if job.started_at else "",
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            duration_seconds=job.duration_seconds,
            input_snapshot=job.input_data,  # Alias for input_data
            output_snapshot=job.result_data,  # Alias for result_data
            error_message=job.error_message,
            error_traceback=job.error_traceback,
            retry_count=job.retry_count or 0,
            triggered_by=job.triggered_by or "system",
            parent_job_id=job.parent_job_id,
            tokens_used=job.tokens_used,
            api_calls=job.api_calls,
            created_at=job.created_at.isoformat() if job.created_at else ""
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job detail: {str(e)}"
        )


@router.get("/types/list")
async def list_job_types(
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get list of distinct job types for filtering"""
    try:
        types = db.query(JobRun.job_type).distinct().all()
        return {
            "success": True,
            "job_types": [t[0] for t in types if t[0]]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job types: {str(e)}"
        )


@router.get("/errors/recent")
async def get_recent_errors(
    limit: int = Query(10, ge=1, le=50),
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get recent failed jobs with details for quick debugging
    """
    try:
        failed_jobs = db.query(JobRun).filter(
            JobRun.status.in_([JobStatus.FAILED, JobStatus.TIMEOUT])
        ).order_by(desc(JobRun.started_at)).limit(limit).all()
        
        errors = []
        for job in failed_jobs:
            errors.append({
                "job_id": job.job_id,
                "job_type": job.job_type,
                "job_name": job.job_name,
                "status": job.status.value if job.status else "unknown",
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "error_message": job.error_message,
                "error_traceback": job.error_traceback,
                "retry_count": job.retry_count,
                "input_snapshot": job.input_data
            })
        
        return {
            "success": True,
            "count": len(errors),
            "errors": errors
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recent errors: {str(e)}"
        )
