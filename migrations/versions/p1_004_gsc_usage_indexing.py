"""
Alembic migration for Improvements: GSC Usage Tracking and Indexing Status

Revision ID: p1_004_gsc_usage_indexing
Create Date: 2026-02-06

Creates tables:
- gsc_api_usage: GSC API调用记录
- gsc_quota_status: GSC每日配额状态
- indexing_status: 页面索引状态追踪
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'p1_004_gsc_usage_indexing'
down_revision = 'p1_003_index_optimization'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create GSC Usage and Indexing Status tables.
    """
    
    # ===========================================
    # GSC API Usage Table
    # ===========================================
    op.create_table(
        'gsc_api_usage',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        
        # Usage info
        sa.Column('usage_date', sa.Date(), nullable=False),
        sa.Column('call_type', sa.String(50), nullable=False),  # search_analytics, sites_list, etc.
        sa.Column('rows_fetched', sa.Integer(), default=0),
        sa.Column('api_calls', sa.Integer(), default=1),
        
        # Request details
        sa.Column('site_url', sa.String(255), nullable=True),
        sa.Column('date_range_start', sa.Date(), nullable=True),
        sa.Column('date_range_end', sa.Date(), nullable=True),
        
        # Performance metrics
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Integer(), default=1),  # 1 = success, 0 = failure
        sa.Column('error_message', sa.Text(), nullable=True),
        
        # Source tracking
        sa.Column('triggered_by', sa.String(50), server_default='system'),
        sa.Column('job_run_id', sa.String(36), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # GSC API Usage indexes
    op.create_index('ix_gsc_usage_date_type', 'gsc_api_usage', ['usage_date', 'call_type'])
    op.create_index('ix_gsc_usage_site_date', 'gsc_api_usage', ['site_url', 'usage_date'])
    op.create_index('ix_gsc_usage_date', 'gsc_api_usage', ['usage_date'])
    
    # ===========================================
    # GSC Quota Status Table
    # ===========================================
    op.create_table(
        'gsc_quota_status',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        
        # Quota date
        sa.Column('quota_date', sa.Date(), nullable=False, unique=True),
        
        # Quota tracking
        sa.Column('daily_limit', sa.Integer(), default=2000),
        sa.Column('used_today', sa.Integer(), default=0),
        sa.Column('remaining', sa.Integer(), default=2000),
        
        # Usage analysis
        sa.Column('usage_breakdown', sa.Text(), nullable=True),  # JSON: {"search_analytics": 100, ...}
        
        # Status
        sa.Column('status', sa.String(20), server_default='healthy'),  # healthy, warning, critical, exceeded
        sa.Column('last_alert_sent', sa.DateTime(timezone=True), nullable=True),
        sa.Column('projected_usage', sa.Integer(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # GSC Quota Status indexes
    op.create_index('ix_gsc_quota_date', 'gsc_quota_status', ['quota_date'])
    op.create_index('ix_gsc_quota_status', 'gsc_quota_status', ['status'])
    
    # ===========================================
    # Indexing Status Table
    # ===========================================
    op.create_table(
        'indexing_status',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        
        # Page identification
        sa.Column('page_url', sa.String(1024), nullable=False),
        sa.Column('page_slug', sa.String(255), nullable=True),
        sa.Column('post_id', sa.Integer(), nullable=True),  # WordPress post ID
        
        # Submission tracking
        sa.Column('first_submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submission_count', sa.Integer(), default=0),
        sa.Column('submission_methods', sa.Text(), nullable=True),  # JSON: ["indexnow", "sitemap"]
        
        # Indexing status
        sa.Column('is_indexed', sa.Boolean(), nullable=True),  # None = unknown
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('check_count', sa.Integer(), default=0),
        
        # Indexing details
        sa.Column('index_status', sa.String(50), nullable=True),  # indexed, not_indexed, error, pending
        sa.Column('index_details', sa.Text(), nullable=True),  # JSON
        
        # GSC data (if available)
        sa.Column('gsc_discovered_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('gsc_last_crawl_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('gsc_crawl_status', sa.String(50), nullable=True),
        
        # Auto-retry tracking
        sa.Column('auto_retry_count', sa.Integer(), default=0),
        sa.Column('last_auto_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_scheduled_check', sa.DateTime(timezone=True), nullable=True),
        
        # Issue tracking
        sa.Column('issues', sa.Text(), nullable=True),  # JSON array
        sa.Column('issue_severity', sa.String(20), server_default='none'),  # none, low, medium, high
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexing Status indexes
    op.create_index('ix_indexing_status_page_url', 'indexing_status', ['page_url'])
    op.create_index('ix_indexing_status_post_id', 'indexing_status', ['post_id'])
    op.create_index('ix_indexing_status_is_indexed', 'indexing_status', ['is_indexed'])
    op.create_index('ix_indexing_status_next_check', 'indexing_status', ['next_scheduled_check'])
    op.create_index('ix_indexing_status_severity', 'indexing_status', ['issue_severity'])
    op.create_index('ix_indexing_status_url_date', 'indexing_status', ['page_url', 'last_checked_at'])


def downgrade():
    """
    Remove all tables created by this migration.
    """
    
    # Drop Indexing Status
    op.drop_index('ix_indexing_status_url_date', table_name='indexing_status')
    op.drop_index('ix_indexing_status_severity', table_name='indexing_status')
    op.drop_index('ix_indexing_status_next_check', table_name='indexing_status')
    op.drop_index('ix_indexing_status_is_indexed', table_name='indexing_status')
    op.drop_index('ix_indexing_status_post_id', table_name='indexing_status')
    op.drop_index('ix_indexing_status_page_url', table_name='indexing_status')
    op.drop_table('indexing_status')
    
    # Drop GSC Quota Status
    op.drop_index('ix_gsc_quota_status', table_name='gsc_quota_status')
    op.drop_index('ix_gsc_quota_date', table_name='gsc_quota_status')
    op.drop_table('gsc_quota_status')
    
    # Drop GSC API Usage
    op.drop_index('ix_gsc_usage_date', table_name='gsc_api_usage')
    op.drop_index('ix_gsc_usage_site_date', table_name='gsc_api_usage')
    op.drop_index('ix_gsc_usage_date_type', table_name='gsc_api_usage')
    op.drop_table('gsc_api_usage')
