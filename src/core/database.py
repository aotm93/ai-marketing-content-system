
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.config import settings
from src.models.base import Base

# Create engine
engine = create_engine(settings.database_url)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency for getting DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    # Import all models here to ensure they are registered with Base.metadata
    import src.models.conversion  # P3 Models
    import src.models.gsc_data    # P4 Models
    import src.models.config      # Config Model
    # import src.models.content # P1/P2 Models if they exist (not created yet or used elsewhere)
    
    Base.metadata.create_all(bind=engine)
