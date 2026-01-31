from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
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
import os

logging.basicConfig(level=settings.log_level)
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
            
            # Register content generation job (actual implementation would go here)
            async def content_generation_job(data):
                """Placeholder for content generation job"""
                logger.info("Content generation job triggered")
                return {"status": "completed", "message": "Content generation placeholder"}
            
            autopilot.register_job("content_generation", content_generation_job)
            
        except Exception as e:
            logger.error(f"Failed to initialize autopilot: {e}")
    
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

