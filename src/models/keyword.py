from sqlalchemy import Column, Integer, Text, Enum
import enum
from .base import Base, TimestampMixin


class KeywordStatus(enum.Enum):
    """Keyword status enum"""
    DISCOVERED = "discovered"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SearchIntent(enum.Enum):
    """Search intent enum"""
    INFORMATIONAL = "informational"
    COMMERCIAL = "commercial"
    TRANSACTIONAL = "transactional"
    NAVIGATIONAL = "navigational"


class Keyword(Base, TimestampMixin):
    """Keyword model"""
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True)
    keyword = Column(Text, nullable=False, unique=True)
    search_volume = Column(Integer)
    difficulty = Column(Integer)
    search_intent = Column(Enum(SearchIntent))
    priority_score = Column(Integer)
    status = Column(Enum(KeywordStatus), default=KeywordStatus.DISCOVERED)
