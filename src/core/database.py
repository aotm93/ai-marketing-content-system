from pathlib import Path

from sqlalchemy import create_engine
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
