"""
Alembic migration for P1: GSC data and opportunities

Revision ID: p1_001_gsc_opportunities
Create Date: 2026-01-26

Creates tables:
- gsc_queries: GSC performance data
- gsc_page_summaries: Aggregated page metrics
- opportunities: SEO opportunities
- topic_clusters: Topic cluster structure
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers
revision = 'p1_001_gsc_opportunities'
down_revision = 'p0_001_job_runs'
branch_labels = None
depends_on = None


def upgrade():
    # GSC Queries table
    op.create_table(
        'gsc_queries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('query_date', sa.Date(), nullable=False),
        sa.Column('query', sa.String(500), nullable=False),
        sa.Column('page', sa.String(1024), nullable=False),
        sa.Column('country', sa.String(10), nullable=True),
        sa.Column('device', sa.String(20), nullable=True),
        sa.Column('clicks', sa.Integer(), server_default='0'),
        sa.Column('impressions', sa.Integer(), server_default='0'),
        sa.Column('ctr', sa.Float(), server_default='0.0'),
        sa.Column('position', sa.Float(), server_default='0.0'),
        sa.Column('synced_at', sa.DateTime(), nullable=True),
        sa.Column('site_url', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('query_date', 'query', 'page', name='uq_gsc_date_query_page')
    )
    
    op.create_index('ix_gsc_query_date', 'gsc_queries', ['query_date'])
    op.create_index('ix_gsc_query', 'gsc_queries', ['query'])
    op.create_index('ix_gsc_page', 'gsc_queries', ['page'])
    op.create_index('ix_gsc_impressions', 'gsc_queries', ['impressions'])
    op.create_index('ix_gsc_position', 'gsc_queries', ['position'])
    
    # GSC Page Summaries table
    op.create_table(
        'gsc_page_summaries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('page', sa.String(1024), nullable=False, unique=True),
        sa.Column('total_clicks', sa.Integer(), server_default='0'),
        sa.Column('total_impressions', sa.Integer(), server_default='0'),
        sa.Column('avg_ctr', sa.Float(), server_default='0.0'),
        sa.Column('avg_position', sa.Float(), server_default='0.0'),
        sa.Column('clicks_trend', sa.Float(), server_default='0.0'),
        sa.Column('position_trend', sa.Float(), server_default='0.0'),
        sa.Column('top_queries', sa.Text(), nullable=True),
        sa.Column('query_count', sa.Integer(), server_default='0'),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('last_analyzed', sa.DateTime(), nullable=True),
        sa.Column('opportunity_score', sa.Float(), server_default='0.0'),
        sa.Column('opportunity_type', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_gsc_page_summaries_page', 'gsc_page_summaries', ['page'])
    
    # Opportunities table
    op.create_table(
        'opportunities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('opportunity_id', sa.String(36), nullable=False, unique=True),
        sa.Column('opportunity_type', sa.String(50), nullable=False),
        sa.Column('target_query', sa.String(500), nullable=True),
        sa.Column('target_page', sa.String(1024), nullable=True),
        sa.Column('target_post_id', sa.Integer(), nullable=True),
        sa.Column('score', sa.Float(), server_default='0.0'),
        sa.Column('potential_clicks', sa.Integer(), server_default='0'),
        sa.Column('confidence', sa.Float(), server_default='0.0'),
        sa.Column('current_position', sa.Float(), nullable=True),
        sa.Column('current_impressions', sa.Integer(), nullable=True),
        sa.Column('current_ctr', sa.Float(), nullable=True),
        sa.Column('current_clicks', sa.Integer(), nullable=True),
        sa.Column('action_type', sa.String(50), nullable=True),
        sa.Column('action_details', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('priority', sa.String(20), server_default='medium'),
        sa.Column('assigned_to', sa.String(100), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('execution_job_id', sa.String(36), nullable=True),
        sa.Column('result_status', sa.String(20), nullable=True),
        sa.Column('result_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_opportunities_id', 'opportunities', ['opportunity_id'])
    op.create_index('ix_opportunities_type', 'opportunities', ['opportunity_type'])
    op.create_index('ix_opportunities_score', 'opportunities', ['score'])
    op.create_index('ix_opportunities_status', 'opportunities', ['status'])
    
    # Topic Clusters table
    op.create_table(
        'topic_clusters',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cluster_id', sa.String(36), nullable=False, unique=True),
        sa.Column('cluster_name', sa.String(255), nullable=False),
        sa.Column('hub_page_id', sa.Integer(), nullable=True),
        sa.Column('hub_page_url', sa.String(1024), nullable=True),
        sa.Column('hub_keyword', sa.String(255), nullable=True),
        sa.Column('intent', sa.String(50), nullable=True),
        sa.Column('topic_keywords', sa.Text(), nullable=True),
        sa.Column('spoke_page_ids', sa.Text(), nullable=True),
        sa.Column('spoke_count', sa.Integer(), server_default='0'),
        sa.Column('total_internal_links', sa.Integer(), server_default='0'),
        sa.Column('avg_links_per_spoke', sa.Float(), server_default='0.0'),
        sa.Column('orphan_spokes', sa.Integer(), server_default='0'),
        sa.Column('cluster_impressions', sa.Integer(), server_default='0'),
        sa.Column('cluster_clicks', sa.Integer(), server_default='0'),
        sa.Column('cluster_avg_position', sa.Float(), server_default='0.0'),
        sa.Column('is_active', sa.Integer(), server_default='1'),
        sa.Column('last_analyzed', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_topic_clusters_id', 'topic_clusters', ['cluster_id'])


def downgrade():
    op.drop_index('ix_topic_clusters_id', table_name='topic_clusters')
    op.drop_table('topic_clusters')
    
    op.drop_index('ix_opportunities_status', table_name='opportunities')
    op.drop_index('ix_opportunities_score', table_name='opportunities')
    op.drop_index('ix_opportunities_type', table_name='opportunities')
    op.drop_index('ix_opportunities_id', table_name='opportunities')
    op.drop_table('opportunities')
    
    op.drop_index('ix_gsc_page_summaries_page', table_name='gsc_page_summaries')
    op.drop_table('gsc_page_summaries')
    
    op.drop_index('ix_gsc_position', table_name='gsc_queries')
    op.drop_index('ix_gsc_impressions', table_name='gsc_queries')
    op.drop_index('ix_gsc_page', table_name='gsc_queries')
    op.drop_index('ix_gsc_query', table_name='gsc_queries')
    op.drop_index('ix_gsc_query_date', table_name='gsc_queries')
    op.drop_table('gsc_queries')
