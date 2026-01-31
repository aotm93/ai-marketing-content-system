"""
Alembic migration for BUG-011: Database Index Optimization

Revision ID: p1_003_index_optimization
Create Date: 2026-01-31

Adds performance indexes for:
- gsc_queries: Composite indexes for common query patterns
- job_runs: Composite indexes for filtering and sorting
- opportunities: Additional indexes for dashboard queries
- content_actions: Temporal and composite indexes

This migration optimizes query performance for:
1. GSC data analysis (date range + position/impressions filtering)
2. Job monitoring (status + time range queries)
3. Opportunity prioritization (status + score sorting)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'p1_003_index_optimization'
down_revision = 'p1_002_content_actions'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add performance optimization indexes.
    Uses IF NOT EXISTS pattern for safety.
    """
    
    # ===========================================
    # GSC Queries Table - Composite Indexes
    # ===========================================
    
    # For queries filtering by date range and sorting by position (opportunity detection)
    # Example: SELECT * FROM gsc_queries WHERE query_date BETWEEN ? AND ? AND position BETWEEN 4 AND 20
    op.create_index(
        'ix_gsc_date_position',
        'gsc_queries',
        ['query_date', 'position'],
        if_not_exists=True
    )
    
    # For queries filtering by date and query text (keyword tracking)
    # Example: SELECT * FROM gsc_queries WHERE query_date >= ? AND query LIKE ?
    op.create_index(
        'ix_gsc_date_query',
        'gsc_queries',
        ['query_date', 'query'],
        if_not_exists=True
    )
    
    # For opportunity scoring: high impressions + low position = opportunity
    # Example: SELECT * FROM gsc_queries WHERE impressions > 100 AND position > 3 ORDER BY impressions DESC
    op.create_index(
        'ix_gsc_impressions_position',
        'gsc_queries',
        ['impressions', 'position'],
        if_not_exists=True
    )
    
    # For page-level aggregation with clicks data
    # Example: SELECT page, SUM(clicks) FROM gsc_queries WHERE query_date >= ? GROUP BY page
    op.create_index(
        'ix_gsc_page_clicks',
        'gsc_queries',
        ['page', 'clicks'],
        if_not_exists=True
    )
    
    # For CTR analysis (filtering by CTR range)
    op.create_index(
        'ix_gsc_ctr',
        'gsc_queries',
        ['ctr'],
        if_not_exists=True
    )
    
    # ===========================================
    # Job Runs Table - Composite Indexes
    # ===========================================
    
    # For filtering by status and time range (common dashboard query)
    # Example: SELECT * FROM job_runs WHERE status = 'failed' AND started_at >= ?
    op.create_index(
        'ix_job_runs_status_started',
        'job_runs',
        ['status', 'started_at'],
        if_not_exists=True
    )
    
    # For filtering by job type and status (job monitoring)
    # Example: SELECT * FROM job_runs WHERE job_type = ? AND status = ?
    op.create_index(
        'ix_job_runs_type_status',
        'job_runs',
        ['job_type', 'status'],
        if_not_exists=True
    )
    
    # For triggered_by filtering with time range
    # Example: SELECT * FROM job_runs WHERE triggered_by = 'autopilot' AND started_at >= ?
    op.create_index(
        'ix_job_runs_triggered_started',
        'job_runs',
        ['triggered_by', 'started_at'],
        if_not_exists=True
    )
    
    # For parent job relationship queries
    op.create_index(
        'ix_job_runs_parent_id',
        'job_runs',
        ['parent_job_id'],
        if_not_exists=True
    )
    
    # For retry analysis
    op.create_index(
        'ix_job_runs_retry_count',
        'job_runs',
        ['retry_count'],
        if_not_exists=True
    )
    
    # ===========================================
    # Opportunities Table - Performance Indexes
    # ===========================================
    
    # For status + priority filtering (dashboard prioritization)
    # Example: SELECT * FROM opportunities WHERE status = 'pending' ORDER BY score DESC
    op.create_index(
        'ix_opportunities_status_score',
        'opportunities',
        ['status', 'score'],
        if_not_exists=True
    )
    
    # For type + status filtering
    op.create_index(
        'ix_opportunities_type_status',
        'opportunities',
        ['opportunity_type', 'status'],
        if_not_exists=True
    )
    
    # For page-based lookups
    op.create_index(
        'ix_opportunities_target_page',
        'opportunities',
        ['target_page'],
        if_not_exists=True
    )
    
    # For post_id based lookups
    op.create_index(
        'ix_opportunities_post_id',
        'opportunities',
        ['target_post_id'],
        if_not_exists=True
    )
    
    # ===========================================
    # Topic Clusters Table - Performance Indexes
    # ===========================================
    
    # For active cluster filtering
    op.create_index(
        'ix_topic_clusters_active',
        'topic_clusters',
        ['is_active'],
        if_not_exists=True
    )
    
    # For hub page lookups
    op.create_index(
        'ix_topic_clusters_hub_page',
        'topic_clusters',
        ['hub_page_id'],
        if_not_exists=True
    )
    
    # ===========================================
    # GSC Page Summaries - Performance Indexes
    # ===========================================
    
    # For opportunity score sorting
    op.create_index(
        'ix_gsc_summaries_score',
        'gsc_page_summaries',
        ['opportunity_score'],
        if_not_exists=True
    )
    
    # For type + score filtering
    op.create_index(
        'ix_gsc_summaries_type_score',
        'gsc_page_summaries',
        ['opportunity_type', 'opportunity_score'],
        if_not_exists=True
    )


def downgrade():
    """
    Remove all indexes created by this migration.
    """
    
    # GSC Page Summaries
    op.drop_index('ix_gsc_summaries_type_score', table_name='gsc_page_summaries')
    op.drop_index('ix_gsc_summaries_score', table_name='gsc_page_summaries')
    
    # Topic Clusters
    op.drop_index('ix_topic_clusters_hub_page', table_name='topic_clusters')
    op.drop_index('ix_topic_clusters_active', table_name='topic_clusters')
    
    # Opportunities
    op.drop_index('ix_opportunities_post_id', table_name='opportunities')
    op.drop_index('ix_opportunities_target_page', table_name='opportunities')
    op.drop_index('ix_opportunities_type_status', table_name='opportunities')
    op.drop_index('ix_opportunities_status_score', table_name='opportunities')
    
    # Job Runs
    op.drop_index('ix_job_runs_retry_count', table_name='job_runs')
    op.drop_index('ix_job_runs_parent_id', table_name='job_runs')
    op.drop_index('ix_job_runs_triggered_started', table_name='job_runs')
    op.drop_index('ix_job_runs_type_status', table_name='job_runs')
    op.drop_index('ix_job_runs_status_started', table_name='job_runs')
    
    # GSC Queries
    op.drop_index('ix_gsc_ctr', table_name='gsc_queries')
    op.drop_index('ix_gsc_page_clicks', table_name='gsc_queries')
    op.drop_index('ix_gsc_impressions_position', table_name='gsc_queries')
    op.drop_index('ix_gsc_date_query', table_name='gsc_queries')
    op.drop_index('ix_gsc_date_position', table_name='gsc_queries')
