from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from src.config import settings
from src.models.base import Base
import logging

logger = logging.getLogger(__name__)

database_url = make_url(settings.database_url)
connect_args = {}

if database_url.drivername.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    connect_args["connect_timeout"] = 10

# Create engine with driver-aware connection settings.
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args=connect_args,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def infer_migration_baseline(db_engine) -> str | None:
    """
    Infer the last Alembic revision that best matches a legacy schema created
    via Base.metadata.create_all() without alembic_version tracking.
    """
    inspector = inspect(db_engine)

    if inspector.has_table("alembic_version"):
        return None

    has_table = inspector.has_table

    if has_table("email_subscribers") or has_table("email_sequences") or has_table("email_enrollments"):
        return "p3_002_email_tables"

    if has_table("backlink_opportunities"):
        return "p3_001_backlink_opportunities"

    if has_table("gsc_api_usage") or has_table("gsc_quota_status"):
        return "p1_004_gsc_usage_indexing"

    if has_table("content_actions"):
        content_action_columns = {column["name"] for column in inspector.get_columns("content_actions")}
        if {"query", "reason", "metrics_before", "metrics_after"} <= content_action_columns:
            return "p1_002_content_actions"

    if has_table("gsc_queries") or has_table("opportunities") or has_table("topic_clusters"):
        return "p1_001_gsc_opportunities"

    if has_table("job_runs") or has_table("content_actions") or has_table("autopilot_runs"):
        return "p0_001_job_runs"

    return None


def run_db_migrations() -> None:
    """Apply Alembic migrations to the configured database."""
    try:
        from alembic import command
        from alembic.config import Config
    except ImportError as exc:
        raise RuntimeError("Alembic is required to apply database migrations") from exc

    project_root = _project_root()
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(project_root / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    inferred_baseline = infer_migration_baseline(engine)
    if inferred_baseline:
        logger.warning(
            "Alembic version tracking is missing; stamping inferred legacy baseline %s before upgrade",
            inferred_baseline,
        )
        command.stamp(alembic_cfg, inferred_baseline)

    command.upgrade(alembic_cfg, "head")


def get_db():
    """Dependency for getting DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables with retry logic"""
    import time
    
    # Import all models here to ensure they are registered with Base.metadata
    import src.models
    
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logger.info("Applying database migrations")
            run_db_migrations()
            Base.metadata.create_all(bind=engine)
            logger.info("Database schema is up to date")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"DB init attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to initialize database after {max_retries} attempts: {e}")
                raise
