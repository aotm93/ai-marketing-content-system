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
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from .dimension_model import DimensionModel, PageCombination, CombinationFilter
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
            "config": job_config, # Note: job_config must be serializable
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "pages_generated": 0,
            "pages_published": 0,
            "errors": []
        }
        
        if self.redis_client:
            try:
                self.redis_client.rpush("pseo:batch_queue", json.dumps(job))
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
        while not self.paused:
            job = None
            
            # Fetch job
            if self.redis_client:
                # Non-blocking pop for async loop compatibility
                # In production, use blocking pop with timeout or separate worker
                try:
                    job_data = self.redis_client.lpop("pseo:batch_queue")
                    if job_data:
                        job = json.loads(job_data)
                except Exception as e:
                    logger.error(f"Redis fetch error: {e}")
            elif self.jobs:
                job = self.jobs.pop(0)
            
            if not job:
                # No jobs, wait and check again
                await asyncio.sleep(2)
                continue

            self.current_job = job
            
            logger.info(f"Processing batch job: {job['job_id']}")
            job["status"] = "processing"
            
            # Update status in Redis (optional persistence for running jobs)
            if self.redis_client:
                # Store current job in a separate key for monitoring
                self.redis_client.set(f"pseo:job:{job['job_id']}", json.dumps(job), ex=86400)
            
            try:
                # 1. Initialize dependencies
                # Handle nested config object from JSON deserialization
                config_data = job["config"]
                if isinstance(config_data, dict):
                    # Reconstruct FactoryConfig object if it was serialized as dict
                    config = FactoryConfig(**{k: v for k, v in config_data.items() if k in FactoryConfig.__annotations__})
                else:
                    config = config_data # Assuming it's already an object if from memory

                model_name = job.get("model_name", "bottle") # Default for safety
                template_id = job.get("template_id", "default")
                max_pages = job.get("max_pages")
                
                # Reconstruct Factory (Simplified for MVP - direct instantiation)
                # In prod, use a ModelFactory and TemplateRepository
                if model_name == "bottle":
                    model = create_bottle_dimension_model()
                else:
                    raise ValueError(f"Unknown model: {model_name}")
                
                # Create default template
                from src.pseo.components import create_default_template
                template = create_default_template(template_id)
                
                factory = pSEOFactory(model, template, config)
                
                # Initialize Publisher (WordPress)
                # Using env vars - in prod, load from secure vault
                publisher = PublisherFactory.create("wordpress", {
                    "url": os.getenv("WORDPRESS_URL", "http://localhost:8000"),
                    "username": os.getenv("WORDPRESS_USERNAME", "admin"),
                    "password": os.getenv("WORDPRESS_PASSWORD", "password"),
                    "seo_plugin": "rank_math"
                })
                
                # Health check
                health = await publisher.health_check()
                if health.get("status") == "error":
                     raise ConnectionError(f"Publisher connection failed: {health}")

                # 2. Generate pages in batches
                # Reuse the factory logic but intercept results for publishing
                combinations = model.generate_all_combinations(max_combinations=max_pages)
                
                batch_size = config.max_pages_per_batch
                total_combos = len(combinations)
                logger.info(f" Job {job['job_id']}: Generating {total_combos} pages in batches of {batch_size}")

                for i in range(0, total_combos, batch_size):
                    if self.paused:
                        # Re-queue remaining work? For now, just stop.
                        logger.info("Queue paused, stopping job processing")
                        # Push job back to front? Or just break. 
                        # Breaking means job is "partial". Let's handle simple pause.
                        break

                    batch_combos = combinations[i:i+batch_size]
                    batch_result = await factory._generate_batch(batch_combos)
                    
                    # 3. Publish generated pages
                    for page_data in batch_result.generated_pages:
                        try:
                            # Map to PublishableContent
                            content = PublishableContent(
                                title=page_data["title"],
                                content=page_data["content"],
                                slug=page_data["slug"],
                                status="draft" if not config.auto_publish else "publish",
                                # SEO Meta
                                seo_title=page_data.get("title"),
                                seo_description=page_data.get("meta_description"),
                                focus_keyword=page_data.get("title_parts", [])[0] if page_data.get("title_parts") else None,
                                # Taxonomy (using dimension values as tags)
                                tags=page_data.get("combination", {}).values()
                            )
                            
                            pub_result = await publisher.publish(content)
                            
                            if pub_result.status == "success":
                                job["pages_published"] += 1
                                logger.info(f"Published: {content.slug}")
                            else:
                                error_msg = f"Failed to publish {content.slug}: {pub_result.error}"
                                logger.error(error_msg)
                                job["errors"].append(error_msg)
                                
                        except Exception as e:
                            logger.error(f"Publishing error for {page_data.get('slug')}: {e}")
                            job["errors"].append(str(e))
                            
                    job["pages_generated"] += len(batch_result.generated_pages)
                    
                    # Update progress (in memory)
                    self.current_job = job 
                    
                job["status"] = "completed"
                logger.info(f"Job {job['job_id']} completed. Generated: {job['pages_generated']}, Published: {job['pages_published']}")
                
            except Exception as e:
                logger.error(f"Job {job['job_id']} failed: {e}")
                job["status"] = "failed"
                job["errors"].append(str(e))
            
            finally:
                # Cleanup / Final Status Update
                if self.redis_client:
                    try:
                        # Update final status in Redis
                        self.redis_client.set(f"pseo:job:{job['job_id']}", json.dumps(job), ex=86400 * 7) # Keep 7 days
                    except Exception as e:
                        logger.error(f"Failed to update job status in Redis: {e}")
                        
                self.current_job = None
    
    def pause_queue(self):
        """Pause queue processing"""
        self.paused = True
        logger.info("Batch queue paused")
    
    def resume_queue(self):
        """Resume queue processing"""
        self.paused = False
        logger.info("Batch queue resumed")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        pending_count = 0
        pending_jobs = []
        
        if self.redis_client:
            try:
                pending_count = self.redis_client.llen("pseo:batch_queue")
                # Peek first 5 jobs
                jobs_data = self.redis_client.lrange("pseo:batch_queue", 0, 4)
                pending_jobs = [json.loads(j)["job_id"] for j in jobs_data]
            except Exception:
                pass
        else:
            pending_count = len(self.jobs)
            pending_jobs = [j["job_id"] for j in self.jobs]
            
        return {
            "total_jobs": pending_count,
            "current_job": self.current_job["job_id"] if self.current_job else None,
            "paused": self.paused,
            "pending_jobs": pending_jobs,
            "persistence": "redis" if self.redis_client else "memory"
        }
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        for i, job in enumerate(self.jobs):
            if job["job_id"] == job_id:
                removed = self.jobs.pop(i)
                logger.info(f"Cancelled job: {job_id}")
                return True
        return False
