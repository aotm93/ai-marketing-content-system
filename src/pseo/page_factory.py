"""
pSEO Page Factory
Implements P2-5, P2-6: Programmatic page generation with quality control

Features:
- Combination generation with filters
- Template-based page creation
- Quality gate integration
- Canonical URL management
- Pagination strategy
- Batch generation
"""

import logging
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from .dimension_model import DimensionModel, PageCombination, CombinationFilter, create_bottle_dimension_model
from .components import PageTemplate
from src.agents.quality_gate import QualityGateAgent
from src.integrations.publisher_adapter import PublisherFactory, PublishableContent
import os
import json
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class FactoryConfig:
    """Configuration for pSEO factory"""
    max_pages_per_batch: int = 100
    enable_quality_gate: bool = True
    min_quality_score: int = 60
    deduplicate: bool = True
    canonical_strategy: str = "primary_dimension"  # primary_dimension, hub_page, self
    pagination_threshold: int = 50  # Create pagination after N items
    auto_publish: bool = False
    default_status: str = "draft"


@dataclass
class GenerationResult:
    """Result of page generation"""
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    generated_pages: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "total_generated": len(self.generated_pages),
            "errors": self.errors,
            "warnings": self.warnings
        }


class pSEOFactory:
    """
    Programmatic SEO Page Factory
    
    Generates pages from dimension combinations with:
    - Quality control
    - Deduplication
    - Canonical management
    - Batch processing
    """
    
    def __init__(
        self,
        dimension_model: DimensionModel,
        template: PageTemplate,
        config: Optional[FactoryConfig] = None
    ):
        self.dimension_model = dimension_model
        self.template = template
        self.config = config or FactoryConfig()
        self.quality_gate = QualityGateAgent() if self.config.enable_quality_gate else None
        self._generated_hashes: set = set()  # For deduplication
    
    async def generate_all_pages(
        self,
        combination_filter: Optional[CombinationFilter] = None,
        max_pages: Optional[int] = None
    ) -> GenerationResult:
        """
        Generate all pages from dimension combinations
        
        Args:
            combination_filter: Optional filter to limit combinations
            max_pages: Maximum number of pages to generate
        """
        logger.info(f"Starting pSEO page generation for model: {self.dimension_model.model_name}")
        
        result = GenerationResult()
        
        # Generate combinations
        combinations = self.dimension_model.generate_all_combinations(max_combinations=max_pages)
        logger.info(f"Generated {len(combinations)} combinations")
        
        # Apply filter if provided
        if combination_filter:
            combinations = combination_filter.filter_combinations(combinations)
            logger.info(f"After filtering: {len(combinations)} combinations")
        
        # Process in batches
        batch_size = self.config.max_pages_per_batch
        for i in range(0, len(combinations), batch_size):
            batch = combinations[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} pages")
            
            batch_result = await self._generate_batch(batch)
            
            # Merge results
            result.success_count += batch_result.success_count
            result.failed_count += batch_result.failed_count
            result.skipped_count += batch_result.skipped_count
            result.generated_pages.extend(batch_result.generated_pages)
            result.errors.extend(batch_result.errors)
            result.warnings.extend(batch_result.warnings)
        
        logger.info(f"Generation complete. Success: {result.success_count}, Failed: {result.failed_count}, Skipped: {result.skipped_count}")
        
        return result
    
    async def _generate_batch(self, combinations: List[PageCombination]) -> GenerationResult:
        """Generate a batch of pages"""
        result = GenerationResult()
        
        # Collect existing content for similarity check
        existing_content = [p["content"] for p in result.generated_pages if "content" in p]
        
        for combo in combinations:
            try:
                page = await self._generate_single_page(combo, existing_content)
                
                if page:
                    result.generated_pages.append(page)
                    result.success_count += 1
                    
                    # Add to existing content for future comparisons
                    if "content" in page:
                        existing_content.append(page["content"])
                else:
                    result.skipped_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to generate page for {combo}: {e}")
                result.failed_count += 1
                result.errors.append(f"Combination {combo}: {str(e)}")
        
        return result
    
    async def _generate_single_page(
        self,
        combination: PageCombination,
        existing_content: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Generate a single page from combination"""
        
        # Generate page data
        page_data = self._build_page_data(combination)
        
        # Render content
        content = self.template.render(page_data)
        
        # Check for duplicates if enabled
        if self.config.deduplicate:
            content_hash = hash(content)
            if content_hash in self._generated_hashes:
                logger.warning(f"Duplicate content detected for {combination}, skipping")
                return None
            self._generated_hashes.add(content_hash)
        
        # Quality gate check
        if self.quality_gate:
            quality_result = await self.quality_gate.execute({
                "type": "full_check",
                "content": content,
                "content_id": combination.get_slug(),
                "existing_content": existing_content,
                "components": [c.component_type.value for c in self.template.components]
            })
            
            report = quality_result.get("report", {})
            
            if not report.get("passed") or report.get("overall_score", 0) < self.config.min_quality_score:
                logger.warning(f"Page failed quality gate: {combination.get_slug()}")
                return None
        
        # Determine canonical URL
        canonical_url = self._determine_canonical(combination)
        
        # Build final page object
        page = {
            "slug": combination.get_slug(),
            "title": self._generate_title(combination),
            "content": content,
            "meta_description": self._generate_meta_description(combination),
            "canonical_url": canonical_url,
            "combination": combination.to_dict(),
            "components": [c.component_id for c in self.template.components],
            "status": self.config.default_status,
            "created_at": datetime.now().isoformat()
        }
        
        return page
    
    def _build_page_data(self, combination: PageCombination) -> Dict[str, Any]:
        """Build data dictionary for template rendering"""
        data = {
            "combination": combination,
            "title_parts": combination.get_title_parts(),
            "slug": combination.get_slug()
        }
        
        # Add individual dimension values
        for dim_type, value in combination.values.items():
            data[dim_type.value] = value.display_name
            data[f"{dim_type.value}_slug"] = value.slug
        
        return data
    
    def _generate_title(self, combination: PageCombination) -> str:
        """Generate page title from combination"""
        parts = combination.get_title_parts()
        
        # Template-based title generation
        # Example: "Plastic 500ml Gym Water Bottle - Premium Quality"
        return " ".join(parts) + " - Premium Quality"
    
    def _generate_meta_description(self, combination: PageCombination) -> str:
        """Generate meta description from combination"""
        parts = combination.get_title_parts()
        
        # Template-based meta description
        return f"High-quality {' '.join(parts)}. Compare specifications, prices, and features. Free consultation available."
    
    def _determine_canonical(self, combination: PageCombination) -> Optional[str]:
        """
        Determine canonical URL based on strategy
        
        Strategies:
        - primary_dimension: Use page with only primary dimension
        - hub_page: Point to hub/category page
        - self: Self-referential (default)
        """
        strategy = self.config.canonical_strategy
        
        if strategy == "self":
            return None  # Self-referential
        
        elif strategy == "hub_page":
            # Would point to category hub
            # Example: "/bottles/" for all bottle variants
            return "/products/"
        
        elif strategy == "primary_dimension":
            # Use the primary (highest priority) dimension as canonical
            if combination.values:
                primary = max(combination.values.items(), key=lambda x: x[1].priority)
                return f"/{primary[1].slug}/"
        
        return None
    
    def estimate_total_pages(self, combination_filter: Optional[CombinationFilter] = None) -> int:
        """Estimate total pages that will be generated"""
        total = self.dimension_model.calculate_total_combinations()
        
        if combination_filter and combination_filter.whitelist:
            return len(combination_filter.whitelist)
        
        # Rough estimate with filters
        # In practice, would need to apply filters to get accurate count
        return total
    
    def get_generation_preview(
        self,
        count: int = 10,
        combination_filter: Optional[CombinationFilter] = None
    ) -> List[Dict[str, Any]]:
        """Get preview of pages that would be generated"""
        combinations = self.dimension_model.generate_all_combinations(max_combinations=count)
        
        if combination_filter:
            combinations = combination_filter.filter_combinations(combinations)
        
        preview = []
        for combo in combinations[:count]:
            preview.append({
                "slug": combo.get_slug(),
                "title": self._generate_title(combo),
                "combination": combo.to_dict()
            })
        
        return preview


class BatchStatus(str, Enum):
    """Batch job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchJobQueue:
    """
    Queue for batch pSEO generation jobs
    Implements P2-7: Publishing queue with pause/resume/rollback
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.jobs: List[Dict[str, Any]] = []
        self.current_job: Optional[Dict[str, Any]] = None
        self.paused: bool = False
        self.redis_client = None
        
        # Track individual batch statuses and published posts for rollback
        self.batch_statuses: Dict[str, BatchStatus] = {}
        self.published_entries: Dict[str, List[int]] = {}  # batch_id -> list of wordpress post_ids
        
        # Initialize Redis if configured
        redis_url = redis_url or os.getenv("REDIS_URL")
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                logger.info(f"BatchJobQueue connected to Redis at {redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Falling back to memory queue.")
        else:
            if not REDIS_AVAILABLE:
                logger.debug("Redis library not installed. Using memory queue.")
            else:
                logger.debug("REDIS_URL not set. Using memory queue.")
    
    def add_job(self, job_config: Dict[str, Any]) -> str:
        """Add a batch generation job to queue"""
        import uuid
        job_id = str(uuid.uuid4())[:8]
        
        job = {
            "job_id": job_id,
            "config": job_config,
            "status": BatchStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "pages_generated": 0,
            "pages_published": 0,
            "errors": []
        }
        
        self.batch_statuses[job_id] = BatchStatus.PENDING
        self.published_entries[job_id] = []
        
        if self.redis_client:
            try:
                self.redis_client.rpush("pseo:batch_queue", json.dumps(job))
                self.redis_client.set(f"pseo:job:{job_id}:status", BatchStatus.PENDING.value)
                logger.info(f"Added batch job {job_id} to Redis queue")
            except Exception as e:
                logger.error(f"Redis error: {e}. Fallback to memory.")
                self.jobs.append(job)
        else:
            self.jobs.append(job)
            logger.info(f"Added batch job {job_id} to memory queue")
        
        return job_id
    
    async def process_queue(self):
        """Process jobs in queue"""
        # This simple processor only handles one job at a time
        while not self.paused:
            job = None
            
            # Fetch job
            if self.redis_client:
                try:
                    job_data = self.redis_client.lpop("pseo:batch_queue")
                    if job_data:
                        job = json.loads(job_data)
                except Exception as e:
                    logger.error(f"Redis fetch error: {e}")
            elif self.jobs:
                job = self.jobs.pop(0)
            
            if not job:
                await asyncio.sleep(2)
                continue

            job_id = job["job_id"]
            self.current_job = job
            self.batch_statuses[job_id] = BatchStatus.PROCESSING
            
            logger.info(f"Processing batch job: {job_id}")
            job["status"] = BatchStatus.PROCESSING.value
            
            if self.redis_client:
                self.redis_client.set(f"pseo:job:{job_id}", json.dumps(job), ex=86400)
                self.redis_client.set(f"pseo:job:{job_id}:status", BatchStatus.PROCESSING.value)
            
            try:
                # 1. Initialize dependencies
                config_data = job["config"]
                if isinstance(config_data, dict):
                    config = FactoryConfig(**{k: v for k, v in config_data.items() if k in FactoryConfig.__annotations__})
                else:
                    config = config_data

                model_name = job.get("model_name", "bottle")
                template_id = job.get("template_id", "default")
                max_pages = job.get("max_pages")
                
                # Check for cancellation before starting work
                if self._check_batch_interrupt(job_id):
                    logger.info(f"Job {job_id} was interrupted before start")
                    continue

                # Factory Setup
                if model_name == "bottle":
                    model = create_bottle_dimension_model()
                else:
                    # In a real app we might load dynamic models
                    model = create_bottle_dimension_model() 
                
                from src.pseo.components import create_default_template
                template = create_default_template(template_id)
                factory = pSEOFactory(model, template, config)
                
                # Publisher Setup
                publisher = PublisherFactory.create("wordpress", {
                    "url": os.getenv("WORDPRESS_URL", "http://localhost:8000"),
                    "username": os.getenv("WORDPRESS_USERNAME", "admin"),
                    "password": os.getenv("WORDPRESS_PASSWORD", "password"),
                    "seo_plugin": "rank_math"
                })
                
                # 2. Generate pages in batches
                combinations = model.generate_all_combinations(max_combinations=max_pages)
                batch_size = config.max_pages_per_batch
                total_combos = len(combinations)
                
                for i in range(0, total_combos, batch_size):
                    # Check for Job-level Pause/Cancel
                    interrupt_action = self._check_batch_interrupt(job_id)
                    while interrupt_action == "pause":
                        logger.info(f"Job {job_id} paused. Waiting...")
                        await asyncio.sleep(5)
                        interrupt_action = self._check_batch_interrupt(job_id)
                        # Global queue pause also affects this loop? 
                        # Ideally, global pause stops 'process_queue' loop at top level.
                        # This 'await asyncio.sleep' allows other tasks to run.
                    
                    if interrupt_action == "cancel":
                        logger.info(f"Job {job_id} cancelled by user")
                        job["status"] = BatchStatus.CANCELLED.value
                        self.batch_statuses[job_id] = BatchStatus.CANCELLED
                        break
                    
                    if self.paused:
                        # Global queue pause -> pause job processing but keep job active
                        while self.paused:
                             await asyncio.sleep(2)
                    
                    # Process Batch
                    batch_combos = combinations[i:i+batch_size]
                    batch_result = await factory._generate_batch(batch_combos)
                    
                    # 3. Publish generated pages
                    current_batch_post_ids = []
                    for page_data in batch_result.generated_pages:
                        try:
                            content = PublishableContent(
                                title=page_data["title"],
                                content=page_data["content"],
                                slug=page_data["slug"],
                                status="draft" if not config.auto_publish else "publish",
                                seo_title=page_data.get("title"),
                                seo_description=page_data.get("meta_description"),
                                focus_keyword=page_data.get("title_parts", [])[0] if page_data.get("title_parts") else None,
                                tags=page_data.get("combination", {}).values()
                            )
                            
                            pub_result = await publisher.publish(content)
                            
                            if pub_result.status == "success":
                                job["pages_published"] += 1
                                if pub_result.post_id:
                                    current_batch_post_ids.append(pub_result.post_id)
                            else:
                                job["errors"].append(f"Failed to publish {content.slug}: {pub_result.error}")
                                
                        except Exception as e:
                            job["errors"].append(f"Publishing error {page_data.get('slug')}: {str(e)}")
                    
                    # Track published IDs for rollback
                    if job_id in self.published_entries:
                        self.published_entries[job_id].extend(current_batch_post_ids)
                    else:
                        self.published_entries[job_id] = current_batch_post_ids
                        
                    job["pages_generated"] += len(batch_result.generated_pages)
                    
                    # Update progress
                    self.current_job = job
                    if self.redis_client:
                        self.redis_client.set(f"pseo:job:{job_id}", json.dumps(job), ex=86400)
                        
                if job["status"] != BatchStatus.CANCELLED.value:
                    job["status"] = BatchStatus.COMPLETED.value
                    self.batch_statuses[job_id] = BatchStatus.COMPLETED
                
            except Exception as e:
                logger.error(f"Job {job_id} failed: {e}")
                job["status"] = BatchStatus.FAILED.value
                self.batch_statuses[job_id] = BatchStatus.FAILED
                job["errors"].append(str(e))
            
            finally:
                if self.redis_client:
                    self.redis_client.set(f"pseo:job:{job_id}", json.dumps(job), ex=86400 * 7)
                    self.redis_client.set(f"pseo:job:{job_id}:status", job["status"])
                        
                self.current_job = None
    
    def _check_batch_interrupt(self, job_id: str) -> Optional[str]:
        """Check if batch should be paused or cancelled"""
        # Check local status
        status = self.batch_statuses.get(job_id)
        
        # Check Redis if available (source of truth for distributed)
        if self.redis_client:
            redis_status = self.redis_client.get(f"pseo:job:{job_id}:status")
            if redis_status:
                status = BatchStatus(redis_status)
                # Sync back to local
                self.batch_statuses[job_id] = status
        
        if status == BatchStatus.PAUSED:
            return "pause"
        if status == BatchStatus.CANCELLED:
            return "cancel"
        return None

    def pause_batch(self, batch_id: str) -> bool:
        """Pause a specific batch job"""
        if batch_id in self.batch_statuses:
            self.batch_statuses[batch_id] = BatchStatus.PAUSED
            if self.redis_client:
                self.redis_client.set(f"pseo:job:{batch_id}:status", BatchStatus.PAUSED.value)
            logger.info(f"Paused batch {batch_id}")
            return True
        return False

    def resume_batch(self, batch_id: str) -> bool:
        """Resume a specific batch job"""
        current = self.batch_statuses.get(batch_id)
        if current == BatchStatus.PAUSED:
            self.batch_statuses[batch_id] = BatchStatus.PROCESSING
            if self.redis_client:
                self.redis_client.set(f"pseo:job:{batch_id}:status", BatchStatus.PROCESSING.value)
            logger.info(f"Resumed batch {batch_id}")
            return True
        return False

    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a specific batch job"""
        self.batch_statuses[batch_id] = BatchStatus.CANCELLED
        if self.redis_client:
            self.redis_client.set(f"pseo:job:{batch_id}:status", BatchStatus.CANCELLED.value)
        
        # Also remove from queue if pending
        if not self.redis_client: # Memory queue removal
            for i, job in enumerate(self.jobs):
                if job["job_id"] == batch_id:
                    self.jobs.pop(i)
                    return True
        return True

    async def rollback_batch(self, batch_id: str, wp_client, action: str = "draft") -> Dict[str, Any]:
        """Rollback published posts for a batch"""
        post_ids = self.published_entries.get(batch_id, [])
        if not post_ids:
             # Try recovering from Redis if not in memory
             if self.redis_client:
                 # TODO: We would need to store published_ids in Redis to make this durable
                 pass 
             return {"success": True, "message": "No posts to rollback", "count": 0}

        success_count = 0
        fail_count = 0
        
        for pid in post_ids:
            try:
                if action == "delete":
                    await wp_client.delete_post(pid)
                else:
                    await wp_client.update_post(pid, {"status": "draft"})
                success_count += 1
            except Exception as e:
                logger.error(f"Rollback failed for post {pid}: {e}")
                fail_count += 1
        
        # Mark batch as rolled back? Or just log it.
        logger.info(f"Rolled back batch {batch_id}: {success_count} success, {fail_count} failed")
        
        return {
            "success": True,
            "processed": len(post_ids),
            "succeeded": success_count,
            "failed": fail_count
        }

    # Global Queue Control
    def pause_queue(self):
        self.paused = True
    
    def resume_queue(self):
        self.paused = False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get overview of queue"""
        # Logic similar to before but includes batch status overview
        pending_count = 0
        if self.redis_client:
             pending_count = self.redis_client.llen("pseo:batch_queue")
        else:
             pending_count = len(self.jobs)
             
        return {
            "paused": self.paused,
            "pending_jobs": pending_count,
            "current_job_id": self.current_job["job_id"] if self.current_job else None,
            "active_batches": {k: v.value for k, v in self.batch_statuses.items()}
        }
