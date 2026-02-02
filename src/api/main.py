from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
from src.config import settings
from src.api.admin import router as admin_router
from src.api.autopilot import router as autopilot_router
from src.api.conversion import router as conversion_router
from src.api.pseo import router as pseo_router
from src.api.gsc import router as gsc_router
from src.api.indexing import router as indexing_router
from src.api.opportunities import router as opportunities_router
from src.api.topic_map import router as topic_map_router
from src.api.quality_gate import router as quality_gate_router
from src.api.cannibalization import router as cannibalization_router
from src.api.job_logs import router as job_logs_router
from src.config.utils import load_settings_from_db, init_system_config
from src.core.database import SessionLocal

# ...


# Routers moved to after app init

import logging
from logging.handlers import RotatingFileHandler
import os

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure log format
log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)

# File handler with rotation (10MB per file, keep 5 backups)
file_handler = RotatingFileHandler(
    'logs/app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(log_format)

# Configure root logger
logging.basicConfig(
    level=settings.log_level,
    handlers=[console_handler, file_handler]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown"""
    # Startup
    logger.info("Starting AI Marketing Content System...")
    
    # Security Warning for default credentials
    if settings.environment == "production":
        if settings.admin_password == "admin123":
            logger.warning("⚠️  SECURITY WARNING: Using default admin password in production! Set ADMIN_PASSWORD env var.")
        if "dev-secret" in settings.admin_session_secret:
            logger.warning("⚠️  SECURITY WARNING: Using default session secret in production! Set ADMIN_SESSION_SECRET env var.")
    
    # Initialize DB (P3)
    try:
        from src.core.database import init_db
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"DB Init Warning: {e}")

    # Load Dynamic System Config
    try:
        db = SessionLocal()
        try:
            init_system_config(db)
            load_settings_from_db(db)
            logger.info("System configuration loaded from database")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to load system config: {e}")

    
    # Initialize autopilot if enabled
    if settings.autopilot_enabled:
        try:
            from src.scheduler.autopilot import configure_autopilot, AutopilotConfig, AutopilotMode
            
            mode = AutopilotMode(settings.autopilot_mode) if settings.autopilot_mode in ["conservative", "standard", "aggressive"] else AutopilotMode.STANDARD
            
            config = AutopilotConfig(
                enabled=settings.autopilot_enabled,
                mode=mode,
                publish_interval_minutes=int(settings.publish_interval_minutes),
                max_posts_per_day=int(settings.max_posts_per_day),
                max_concurrent_agents=int(settings.max_concurrent_jobs),
                auto_publish=settings.auto_publish,
                require_seo_score=int(settings.require_seo_score),
                require_word_count=int(settings.require_word_count),
                max_tokens_per_day=int(settings.max_tokens_per_day) if settings.max_tokens_per_day else 100000,
                pause_on_errors=int(settings.pause_on_consecutive_errors),
                active_hours_start=int(settings.active_hours_start),
                active_hours_end=int(settings.active_hours_end)
            )
            
            autopilot = configure_autopilot(config)
            logger.info(f"Autopilot configured: mode={mode.value}, enabled={settings.autopilot_enabled}")
            
            # Register all jobs (content generation, SEO, refresh, etc.)
            from src.scheduler.jobs import register_all_jobs
            register_all_jobs(autopilot)

            # Start the scheduler automatically
            autopilot.start()
            logger.info("Autopilot scheduler started automatically")

        except Exception as e:
            logger.error(f"Failed to initialize autopilot: {e}")

    # Initialize website analysis cache on startup
    try:
        from src.scheduler.jobs import _website_profile_cache, analyze_website_now

        # Check if cache is empty (first deployment)
        if _website_profile_cache["profile"] is None:
            logger.info("🔍 First deployment detected - triggering initial website analysis...")
            try:
                # Use await instead of asyncio.run() since we're already in async context
                # Add 60 second timeout to prevent startup hanging
                profile = await asyncio.wait_for(
                    analyze_website_now(),
                    timeout=60.0
                )
                if profile:
                    logger.info(f"✅ Initial website analysis complete: {len(profile.product_categories)} categories found")
                else:
                    logger.warning("⚠️ Initial website analysis failed - will use fallback keywords")
            except asyncio.TimeoutError:
                logger.warning("⚠️ Website analysis timed out (60s) - will use fallback keywords")
        else:
            logger.info("Website analysis cache already populated")
    except Exception as e:
        logger.warning(f"Failed to initialize website analysis: {e}")

    logger.info("System startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Marketing Content System...")
    
    # Stop autopilot if running
    try:
        from src.scheduler.autopilot import get_autopilot
        autopilot = get_autopilot()
        autopilot.stop()
    except Exception as e:
        logger.warning(f"Error stopping autopilot: {e}")
    
    logger.info("System shutdown complete")


app = FastAPI(
    title="AI Marketing Content System",
    description="Autonomous multi-agent system for generating marketing content and SEO autopilot",
    version="2.0.0",
    lifespan=lifespan
)

# Include Routers
app.include_router(admin_router)
app.include_router(autopilot_router)
app.include_router(conversion_router)
app.include_router(pseo_router)
app.include_router(gsc_router)
app.include_router(indexing_router)
app.include_router(opportunities_router)
app.include_router(topic_map_router)
app.include_router(quality_gate_router)
app.include_router(cannibalization_router)
app.include_router(job_logs_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Mount static files for admin interface
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "static")
if os.path.exists(static_path):
    admin_static = os.path.join(static_path, "admin")
    if os.path.exists(admin_static):
        app.mount("/admin", StaticFiles(directory=admin_static, html=True), name="admin")

# Mount static files for dashboard (Next.js export)
dashboard_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "out")
if os.path.exists(dashboard_path):
    app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Marketing Content System API",
        "version": "2.0.0",
        "status": "running",
        "features": {
            "dashboard": "/dashboard",
            "admin_panel": "/admin",
            "autopilot_api": "/api/v1/autopilot",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from src.scheduler.autopilot import get_autopilot
    
    autopilot_status = "not_initialized"
    try:
        autopilot = get_autopilot()
        status = autopilot.get_status()
        autopilot_status = "running" if status.get("scheduler_running") else "stopped"
    except:
        pass
    
    return {
        "status": "healthy",
        "autopilot": autopilot_status,
        "environment": settings.environment
    }

