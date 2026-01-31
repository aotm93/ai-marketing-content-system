from sqlalchemy.orm import Session
from sqlalchemy import inspect
from src.models.config import SystemConfig
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

def load_settings_from_db(db: Session):
    """Load settings from database and update the global settings object"""
    try:
        # SQLAlchemy 2.x compatible way to check if table exists
        inspector = inspect(db.bind)
        if not inspector.has_table("system_config"):
            logger.warning("System config table does not exist yet. Skipping DB config load.")
            return

        configs = db.query(SystemConfig).all()
        
        updated_count = 0
        for config in configs:
            key = config.key.lower()
            if hasattr(settings, key):
                try:
                    # Convert value based on type
                    value = config.value
                    final_value = value
                    
                    if config.data_type == "bool":
                        final_value = str(value).lower() == "true"
                    elif config.data_type == "int":
                        final_value = int(value) if value else 0
                    elif config.data_type == "float":
                        final_value = float(value) if value else 0.0
                    
                    # Only update if value is not None (or handle None properly)
                    if value is not None:
                        # Pydantic validation might trigger here if we are not careful
                        # But we are setting attributes on an existing instance
                        setattr(settings, key, final_value)
                        updated_count += 1
                except Exception as e:
                    logger.error(f"Error setting config {key}: {e}")
                    
        logger.info(f"Loaded {updated_count} settings from database")
    except Exception as e:
        logger.error(f"Failed to load settings from DB: {e}")

def get_config_value(db: Session, key: str):
    """Get a specific config value directly from DB"""
    try:
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config:
            return config.value
    except Exception:
        pass
    return None

def update_config_value(db: Session, key: str, value: str, data_type: str = "string"):
    """Update or create a config value"""
    try:
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config:
            config.value = str(value)
            config.data_type = data_type
        else:
            config = SystemConfig(key=key, value=str(value), data_type=data_type)
            db.add(config)
        
        db.commit()
        # Update run-time settings
        setting_key = key.lower()
        if hasattr(settings, setting_key):
             # Simple type conversion for runtime update
            runtime_val = value
            if data_type == "bool":
                runtime_val = str(value).lower() == "true"
            elif data_type == "int":
                runtime_val = int(value)

            setattr(settings, setting_key, runtime_val)

            # Special handling: Update log level dynamically
            if setting_key == "log_level":
                import logging
                logging.getLogger().setLevel(runtime_val)
                logger.info(f"Log level updated to {runtime_val} (effective immediately)")

        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save config {key}: {e}")
        return False

def init_system_config(db: Session):
    """Initialize system configuration table if needed"""
    # This is a placeholder for any logic needed to ensure config table is ready
    # or to seed initial values if they don't exist
    pass
