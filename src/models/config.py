from sqlalchemy import Column, String, Text, Boolean, DateTime
from datetime import datetime
from src.models.base import Base

class SystemConfig(Base):
    """
    System Configuration model
    Stores configuration dynamically in the database
    """
    __tablename__ = "system_config"

    key = Column(String(100), primary_key=True, index=True)
    value = Column(Text, nullable=True)  # Stored as string, type conversion handled by app
    data_type = Column(String(20), default="string")  # string, int, bool, json
    description = Column(String(255), nullable=True)
    is_secret = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<SystemConfig {self.key}={self.value}>"
