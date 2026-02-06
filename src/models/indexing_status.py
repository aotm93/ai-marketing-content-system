"""
Page Indexing Status Model

Tracks submission and indexing status for each page
Implements automatic index monitoring and retry logic
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index
from datetime import datetime
from typing import Dict, Any

from .base import Base, TimestampMixin


class IndexingStatus(Base, TimestampMixin):
    """
    Page indexing status tracking
    
    Tracks submission and indexing status for each page
    """
    __tablename__ = "indexing_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Page identification
    page_url = Column(String(1024), nullable=False, index=True)
    page_slug = Column(String(255), nullable=True)
    post_id = Column(Integer, nullable=True, index=True)  # WordPress post ID
    
    # Submission tracking
    first_submitted_at = Column(DateTime, nullable=True)
    last_submitted_at = Column(DateTime, nullable=True)
    submission_count = Column(Integer, default=0)
    submission_methods = Column(Text, nullable=True)  # JSON: ["indexnow", "sitemap"]
    
    # Indexing status
    is_indexed = Column(Boolean, nullable=True)  # None = unknown, True/False = checked
    last_checked_at = Column(DateTime, nullable=True)
    check_count = Column(Integer, default=0)
    
    # Indexing details (when checked)
    index_status = Column(String(50), nullable=True)  # indexed, not_indexed, error, pending
    index_details = Column(Text, nullable=True)  # JSON with check results
    
    # Google Search Console data (if available)
    gsc_discovered_date = Column(DateTime, nullable=True)
    gsc_last_crawl_date = Column(DateTime, nullable=True)
    gsc_crawl_status = Column(String(50), nullable=True)  # success, error, redirect
    
    # Auto-retry tracking
    auto_retry_count = Column(Integer, default=0)
    last_auto_retry_at = Column(DateTime, nullable=True)
    next_scheduled_check = Column(DateTime, nullable=True)
    
    # Issue tracking
    issues = Column(Text, nullable=True)  # JSON array of issues
    issue_severity = Column(String(20), default="none")  # none, low, medium, high
    
    __table_args__ = (
        Index('ix_indexing_status_post_id', 'post_id'),
        Index('ix_indexing_status_is_indexed', 'is_indexed'),
        Index('ix_indexing_status_next_check', 'next_scheduled_check'),
        Index('ix_indexing_status_url_date', 'page_url', 'last_checked_at'),
    )
    
    def __repr__(self):
        return f"<IndexingStatus(url='{self.page_url[:50]}...', indexed={self.is_indexed})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        import json
        return {
            "id": self.id,
            "page_url": self.page_url,
            "page_slug": self.page_slug,
            "post_id": self.post_id,
            "submission_count": self.submission_count,
            "is_indexed": self.is_indexed,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "check_count": self.check_count,
            "index_status": self.index_status,
            "auto_retry_count": self.auto_retry_count,
            "issue_severity": self.issue_severity,
            "issues": json.loads(self.issues) if self.issues else [],
            "next_scheduled_check": self.next_scheduled_check.isoformat() if self.next_scheduled_check else None,
        }
