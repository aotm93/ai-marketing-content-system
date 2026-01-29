"""
pSEO API Endpoints
Provides API for programmatic SEO page generation and management
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.pseo import (
    pSEOFactory,
    FactoryConfig,
    create_bottle_dimension_model
)
from src.pseo.page_factory import BatchJobQueue
from src.pseo.components import create_default_template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pseo", tags=["pSEO"])

# Global batch queue
batch_queue = BatchJobQueue()


class GenerationRequest(BaseModel):
    """Request for page generation"""
    model_name: str
    template_id: str
    max_pages: Optional[int] = None
    enable_quality_gate: bool = True
    min_quality_score: int = 60
    auto_publish: bool = False


class PreviewRequest(BaseModel):
    """Request for generation preview"""
    model_name: str
    count: int = 10


@router.post("/generate")
async def generate_pages(request: GenerationRequest, background_tasks: BackgroundTasks):
    """
    Generate pSEO pages
    
    Can run in foreground (small batches) or background (large batches)
    """
    try:
        # Load or create dimension model
        if request.model_name == "bottle":
            dimension_model = create_bottle_dimension_model()
        else:
            raise HTTPException(status_code=404, detail=f"Model '{request.model_name}' not found")
        
        # Create template
        template = create_default_template(request.template_id)
        
        # Configure factory
        config = FactoryConfig(
            enable_quality_gate=request.enable_quality_gate,
            min_quality_score=request.min_quality_score,
            auto_publish=request.auto_publish
        )
        
        factory = pSEOFactory(dimension_model, template, config)
        
        # Small batch: generate immediately
        if request.max_pages and request.max_pages <= 100:
            result = await factory.generate_all_pages(max_pages=request.max_pages)
            
            return {
                "status": "completed",
                "result": result.to_dict()
            }
        
        # Large batch: queue for background processing
        else:
            job_id = batch_queue.add_job({
                "model_name": request.model_name,
                "template_id": request.template_id,
                "max_pages": request.max_pages,
                "config": config
            })
            
            # Start background processing
            background_tasks.add_task(batch_queue.process_queue)
            
            return {
                "status": "queued",
                "job_id": job_id,
                "message": "Large batch queued for background processing"
            }
    
    except Exception as e:
        logger.error(f"Page generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview")
async def preview_pages(model_name: str, count: int = 10):
    """Get preview of pages that would be generated"""
    try:
        # Load dimension model
        if model_name == "bottle":
            dimension_model = create_bottle_dimension_model()
        else:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
        
        # Create factory with default template
        template = create_default_template("default")
        factory = pSEOFactory(dimension_model, template)
        
        # Generate preview
        preview = factory.get_generation_preview(count=count)
        
        return {
            "status": "success",
            "model_name": model_name,
            "preview_count": len(preview),
            "total_combinations": dimension_model.calculate_total_combinations(),
            "preview": preview
        }
    
    except Exception as e:
        logger.error(f"Preview generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models():
    """List available dimension models"""
    return {
        "status": "success",
        "models": [
            {
                "name": "bottle",
                "description": "Bottle manufacturing pSEO",
                "dimensions": ["material", "capacity", "scene", "industry"]
            }
        ]
    }


@router.get("/queue/status")
async def get_queue_status():
    """Get batch queue status"""
    return {
        "status": "success",
        "queue": batch_queue.get_queue_status()
    }


@router.post("/queue/pause")
async def pause_queue():
    """Pause batch processing"""
    batch_queue.pause_queue()
    return {
        "status": "success",
        "message": "Queue paused"
    }


@router.post("/queue/resume")
async def resume_queue(background_tasks: BackgroundTasks):
    """Resume batch processing"""
    batch_queue.resume_queue()
    background_tasks.add_task(batch_queue.process_queue)
    return {
        "status": "success",
        "message": "Queue resumed"
    }


@router.delete("/queue/job/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a pending job"""
    success = batch_queue.cancel_job(job_id)
    
    if success:
        return {
            "status": "success",
            "message": f"Job {job_id} cancelled"
        }
    else:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


class BatchControlRequest(BaseModel):
    """Batch job control request"""
    action: Optional[str] = "draft"  # For rollback: "draft" or "delete"


@router.post("/batch/{batch_id}/pause")
async def pause_batch(batch_id: str):
    """Pause specific batch job"""
    success = batch_queue.pause_batch(batch_id)
    if success:
        return {"status": "success", "message": f"Batch {batch_id} paused"}
    raise HTTPException(status_code=404, detail="Batch not found")


@router.post("/batch/{batch_id}/resume")
async def resume_batch(batch_id: str):
    """Resume specific batch job"""
    success = batch_queue.resume_batch(batch_id)
    if success:
        return {"status": "success", "message": f"Batch {batch_id} resumed"}
    raise HTTPException(status_code=404, detail="Batch not found")


@router.delete("/batch/{batch_id}/cancel")
async def cancel_batch_endpoint(batch_id: str):
    """Cancel specific batch job"""
    success = batch_queue.cancel_batch(batch_id)
    if success:
        return {"status": "success", "message": f"Batch {batch_id} cancelled"}
    raise HTTPException(status_code=404, detail="Batch not found")


@router.post("/batch/{batch_id}/rollback")
async def rollback_batch_endpoint(batch_id: str, request: BatchControlRequest):
    """Rollback published posts for a batch"""
    from src.integrations.wordpress_client import WordPressClient
    from src.config import settings
    import os
    
    # Assuming config is loaded, if not fall back to env or defaults
    # settings object might not be fully initialized depending on app lifecycle, so we check safely
    wp_url = getattr(settings, "wordpress_url", None) or os.getenv("WORDPRESS_URL")
    wp_user = getattr(settings, "wordpress_username", None) or os.getenv("WORDPRESS_USERNAME")
    wp_pass = getattr(settings, "wordpress_password", None) or os.getenv("WORDPRESS_PASSWORD")
    
    if not wp_url:
        raise HTTPException(status_code=500, detail="WordPress configuration missing")

    wp_client = WordPressClient(url=wp_url, username=wp_user, password=wp_pass)
    
    result = await batch_queue.rollback_batch(batch_id, wp_client, action=request.action)
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result.get("message", "Rollback failed"))



