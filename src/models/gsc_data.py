"""
GSC Queries Database Model
Implements P1-2: gsc_queries table for storing GSC data

Stores:
- Daily query/page performance metrics
- Historical data for trend analysis
- Aggregated metrics for opportunity scoring
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index, UniqueConstraint, Date
from datetime import datetime
from typing import Dict, Any

from .base import Base, TimestampMixin


class GSCQuery(Base, TimestampMixin):
    """
    Google Search Console query performance data
    
    Stores daily metrics for query/page combinations
    """
    __tablename__ = "gsc_queries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Dimensions
    query_date = Column(Date, nullable=False, index=True)
    query = Column(String(500), nullable=False, index=True)
    page = Column(String(1024), nullable=False, index=True)
    country = Column(String(10), nullable=True)
    device = Column(String(20), nullable=True)  # DESKTOP, MOBILE, TABLET
    
    # Metrics
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)  # Stored as decimal (0.05 = 5%)
    position = Column(Float, default=0.0)
    
    # Sync metadata
    synced_at = Column(DateTime, default=datetime.now)
    site_url = Column(String(255), nullable=True)
    
    # Unique constraint on date + query + page
    __table_args__ = (
        UniqueConstraint('query_date', 'query', 'page', name='uq_gsc_date_query_page'),
        Index('ix_gsc_impressions', 'impressions'),
        Index('ix_gsc_position', 'position'),
        Index('ix_gsc_query_date_range', 'query_date', 'impressions'),
    )
    
    def __repr__(self):
        return f"<GSCQuery(date={self.query_date}, query='{self.query[:30]}...', pos={self.position})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "date": self.query_date.isoformat() if self.query_date else None,
            "query": self.query,
            "page": self.page,
            "country": self.country,
            "device": self.device,
            "clicks": self.clicks,
            "impressions": self.impressions,
            "ctr": round(self.ctr * 100, 2),  # As percentage
            "position": round(self.position, 1)
        }
    
    @property
    def ctr_percent(self) -> float:
        """CTR as percentage"""
        return round(self.ctr * 100, 2)
    
    @property
    def is_opportunity(self) -> bool:
        """Check if this is a low-hanging fruit opportunity"""
        return self.impressions >= 100 and 4 <= self.position <= 20


class GSCPageSummary(Base, TimestampMixin):
    """
    Aggregated GSC metrics per page
    
    Stores rolling summaries for faster opportunity analysis
    """
    __tablename__ = "gsc_page_summaries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Page identification
    page = Column(String(1024), nullable=False, unique=True, index=True)
    
    # Aggregated metrics (typically 28-day rolling average)
    total_clicks = Column(Integer, default=0)
    total_impressions = Column(Integer, default=0)
    avg_ctr = Column(Float, default=0.0)
    avg_position = Column(Float, default=0.0)
    
    # Trend indicators
    clicks_trend = Column(Float, default=0.0)  # Positive = growing
    position_trend = Column(Float, default=0.0)  # Negative = improving
    
    # Top queries for this page
    top_queries = Column(Text, nullable=True)  # JSON array
    
    # Analysis metadata
    query_count = Column(Integer, default=0)  # Number of unique queries
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    last_analyzed = Column(DateTime, default=datetime.now)
    
    # Opportunity scoring
    opportunity_score = Column(Float, default=0.0)  # 0-100
    opportunity_type = Column(String(50), nullable=True)  # low_hanging, declining, new
    
    def __repr__(self):
        return f"<GSCPageSummary(page='{self.page[:50]}...', score={self.opportunity_score})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "page": self.page,
            "total_clicks": self.total_clicks,
            "total_impressions": self.total_impressions,
            "avg_ctr": round(self.avg_ctr * 100, 2),
            "avg_position": round(self.avg_position, 1),
            "clicks_trend": round(self.clicks_trend, 2),
            "position_trend": round(self.position_trend, 2),
            "query_count": self.query_count,
            "opportunity_score": round(self.opportunity_score, 1),
            "opportunity_type": self.opportunity_type
        }


class Opportunity(Base, TimestampMixin):
    """
    SEO Opportunity / Low-Hanging Fruit
    
    Represents actionable optimization opportunities detected from GSC data
    """
    __tablename__ = "opportunities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identification
    opportunity_id = Column(String(36), unique=True, nullable=False, index=True)
    opportunity_type = Column(String(50), nullable=False, index=True)
    # Types: low_hanging_fruit, ctr_optimization, content_refresh, new_content, cannibalization
    
    # Target
    target_query = Column(String(500), nullable=True)
    target_page = Column(String(1024), nullable=True)
    target_post_id = Column(Integer, nullable=True)
    
    # Scoring
    score = Column(Float, default=0.0, index=True)  # 0-100 priority score
    potential_clicks = Column(Integer, default=0)  # Estimated additional clicks
    confidence = Column(Float, default=0.0)  # 0-1 confidence level
    
    # Current metrics (snapshot when opportunity was created)
    current_position = Column(Float, nullable=True)
    current_impressions = Column(Integer, nullable=True)
    current_ctr = Column(Float, nullable=True)
    current_clicks = Column(Integer, nullable=True)
    
    # Recommended action
    action_type = Column(String(50), nullable=True)
    # Actions: optimize_title, optimize_description, add_content, add_faq, add_internal_links
    action_details = Column(Text, nullable=True)  # JSON with specific recommendations
    
    # Status tracking
    status = Column(String(20), default="pending", index=True)
    # Status: pending, in_progress, completed, dismissed
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    
    # Execution
    assigned_to = Column(String(100), nullable=True)  # Agent or user
    executed_at = Column(DateTime, nullable=True)
    execution_job_id = Column(String(36), nullable=True)
    
    # Results (after execution)
    result_status = Column(String(20), nullable=True)
    result_data = Column(Text, nullable=True)  # JSON
    
    def __repr__(self):
        return f"<Opportunity(id={self.opportunity_id}, type={self.opportunity_type}, score={self.score})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "opportunity_id": self.opportunity_id,
            "type": self.opportunity_type,
            "target_query": self.target_query,
            "target_page": self.target_page,
            "score": round(self.score, 1),
            "potential_clicks": self.potential_clicks,
            "current_position": self.current_position,
            "current_impressions": self.current_impressions,
            "action_type": self.action_type,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class TopicCluster(Base, TimestampMixin):
    """
    Topic Cluster / Hub-Spoke Structure
    
    Implements P1-10: TopicMap data structure for internal linking
    """
    __tablename__ = "topic_clusters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Cluster identification
    cluster_id = Column(String(36), unique=True, nullable=False, index=True)
    cluster_name = Column(String(255), nullable=False)
    
    # Hub (pillar) page
    hub_page_id = Column(Integer, nullable=True)  # WordPress post ID
    hub_page_url = Column(String(1024), nullable=True)
    hub_keyword = Column(String(255), nullable=True)
    
    # Cluster metadata
    intent = Column(String(50), nullable=True)  # informational, commercial, transactional
    topic_keywords = Column(Text, nullable=True)  # JSON array of related keywords
    
    # Spoke pages (stored as JSON array of post IDs)
    spoke_page_ids = Column(Text, nullable=True)
    spoke_count = Column(Integer, default=0)
    
    # Health metrics
    total_internal_links = Column(Integer, default=0)
    avg_links_per_spoke = Column(Float, default=0.0)
    orphan_spokes = Column(Integer, default=0)  # Spokes not linked to hub
    
    # Performance (from GSC)
    cluster_impressions = Column(Integer, default=0)
    cluster_clicks = Column(Integer, default=0)
    cluster_avg_position = Column(Float, default=0.0)
    
    # Status
    is_active = Column(Integer, default=1)
    last_analyzed = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<TopicCluster(name='{self.cluster_name}', spokes={self.spoke_count})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cluster_id": self.cluster_id,
            "name": self.cluster_name,
            "hub_page_id": self.hub_page_id,
            "hub_url": self.hub_page_url,
            "hub_keyword": self.hub_keyword,
            "intent": self.intent,
            "spoke_count": self.spoke_count,
            "total_internal_links": self.total_internal_links,
            "is_active": bool(self.is_active)
        }
