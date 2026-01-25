from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum
from .base import Base, TimestampMixin


class ContentStatus(enum.Enum):
    """Content status enum"""
    DRAFT = "draft"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    PUBLISHED = "published"
    FAILED = "failed"


class ContentType(enum.Enum):
    """Content type enum"""
    BLOG_POST = "blog_post"
    GUIDE = "guide"
    COMPARISON = "comparison"
    CASE_STUDY = "case_study"


class Content(Base, TimestampMixin):
    """Content model"""
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True)
    keyword_id = Column(Integer, ForeignKey("keywords.id"))
    title = Column(String(500), nullable=False)
    content_type = Column(Enum(ContentType))
    body = Column(Text)
    meta_description = Column(String(300))
    status = Column(Enum(ContentStatus), default=ContentStatus.DRAFT)
    wordpress_post_id = Column(Integer)
