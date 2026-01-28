"""
Alembic migration for P0 upgrade: Job runs and autopilot tables

Revision ID: p0_001_job_runs
Create Date: 2026-01-26

Creates tables:
- job_runs: Job execution audit records
- content_actions: Content modification history
- autopilot_runs: Daily autopilot statistics
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers
revision = 'p0_001_job_runs'
down_revision = None  # Set to previous migration if exists
branch_labels = None
depends_on = None


def upgrade():
    # Job Runs table - stores every job execution
    op.create_table(
        'job_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.String(36), nullable=False),
        sa.Column('job_type', sa.String(100), nullable=False),
        sa.Column('job_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('result_data', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('api_calls', sa.Integer(), nullable=True),
        sa.Column('triggered_by', sa.String(50), server_default='scheduler'),
        sa.Column('parent_job_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for job_runs
    op.create_index('ix_job_runs_job_id', 'job_runs', ['job_id'], unique=True)
    op.create_index('ix_job_runs_job_type', 'job_runs', ['job_type'])
    op.create_index('ix_job_runs_status', 'job_runs', ['status'])
    op.create_index('ix_job_runs_started_at', 'job_runs', ['started_at'])
    
    # Content Actions table - tracks content modifications
    op.create_table(
        'content_actions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('action_id', sa.String(36), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=True),
        sa.Column('post_url', sa.String(512), nullable=True),
        sa.Column('post_title', sa.String(255), nullable=True),
        sa.Column('before_snapshot', sa.JSON(), nullable=True),
        sa.Column('after_snapshot', sa.JSON(), nullable=True),
        sa.Column('changes_summary', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), server_default='completed'),
        sa.Column('job_run_id', sa.Integer(), nullable=True),
        sa.Column('triggered_by', sa.String(50), server_default='system'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for content_actions
    op.create_index('ix_content_actions_action_id', 'content_actions', ['action_id'], unique=True)
    op.create_index('ix_content_actions_action_type', 'content_actions', ['action_type'])
    op.create_index('ix_content_actions_post_id', 'content_actions', ['post_id'])
    
    # Autopilot Runs table - daily statistics
    op.create_table(
        'autopilot_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_date', sa.DateTime(), nullable=False),
        sa.Column('total_jobs', sa.Integer(), server_default='0'),
        sa.Column('successful_jobs', sa.Integer(), server_default='0'),
        sa.Column('failed_jobs', sa.Integer(), server_default='0'),
        sa.Column('rate_limited_jobs', sa.Integer(), server_default='0'),
        sa.Column('posts_created', sa.Integer(), server_default='0'),
        sa.Column('posts_published', sa.Integer(), server_default='0'),
        sa.Column('posts_updated', sa.Integer(), server_default='0'),
        sa.Column('total_tokens_used', sa.Integer(), server_default='0'),
        sa.Column('total_api_calls', sa.Integer(), server_default='0'),
        sa.Column('estimated_cost_usd', sa.Float(), server_default='0.0'),
        sa.Column('config_snapshot', sa.JSON(), nullable=True),
        sa.Column('error_count', sa.Integer(), server_default='0'),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for autopilot_runs
    op.create_index('ix_autopilot_runs_run_date', 'autopilot_runs', ['run_date'], unique=True)


def downgrade():
    op.drop_index('ix_autopilot_runs_run_date', table_name='autopilot_runs')
    op.drop_table('autopilot_runs')
    
    op.drop_index('ix_content_actions_post_id', table_name='content_actions')
    op.drop_index('ix_content_actions_action_type', table_name='content_actions')
    op.drop_index('ix_content_actions_action_id', table_name='content_actions')
    op.drop_table('content_actions')
    
    op.drop_index('ix_job_runs_started_at', table_name='job_runs')
    op.drop_index('ix_job_runs_status', table_name='job_runs')
    op.drop_index('ix_job_runs_job_type', table_name='job_runs')
    op.drop_index('ix_job_runs_job_id', table_name='job_runs')
    op.drop_table('job_runs')
