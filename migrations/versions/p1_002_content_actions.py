"""
Alembic migration for P1: Content Actions table

Revision ID: p1_002_content_actions
Create Date: 2026-01-28

Creates table:
- content_actions: 记录内容变更历史，支持回滚
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'p1_002_content_actions'
down_revision = 'p1_001_gsc_opportunities'
branch_labels = None
depends_on = None


def upgrade():
    # Content Actions table
    op.create_table(
        'content_actions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('action_id', sa.String(36), nullable=False, unique=True),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=True),
        sa.Column('post_url', sa.String(512), nullable=True),
        sa.Column('post_title', sa.String(255), nullable=True),
        
        # Related query
        sa.Column('query', sa.String(255), nullable=True),
        
        # 变更快照 (JSON)
        sa.Column('before_snapshot', sa.Text(), nullable=True),
        sa.Column('after_snapshot', sa.Text(), nullable=True),
        sa.Column('changes_summary', sa.Text(), nullable=True),
        
        # 变更原因和指标
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('metrics_before', sa.Text(), nullable=True),
        sa.Column('metrics_after', sa.Text(), nullable=True),
        
        # 状态
        sa.Column('status', sa.String(20), server_default='active'),
        
        # 回滚信息
        sa.Column('rollback_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rollback_by', sa.String(100), nullable=True),
        
        # Related job
        sa.Column('job_run_id', sa.Integer(), nullable=True),
        
        # User tracking
        sa.Column('triggered_by', sa.String(50), server_default='system'),
        sa.Column('applied_by', sa.String(100), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('ix_content_actions_id', 'content_actions', ['id'])
    op.create_index('ix_content_actions_action_id', 'content_actions', ['action_id'])
    op.create_index('ix_content_actions_action_type', 'content_actions', ['action_type'])
    op.create_index('ix_content_actions_post_id', 'content_actions', ['post_id'])
    op.create_index('ix_content_actions_query', 'content_actions', ['query'])
    op.create_index('ix_content_actions_status', 'content_actions', ['status'])
    op.create_index('ix_content_actions_created_at', 'content_actions', ['created_at'])
    
    # 复合索引
    op.create_index('ix_content_actions_post_type', 'content_actions', ['post_id', 'action_type'])


def downgrade():
    op.drop_index('ix_content_actions_post_type', table_name='content_actions')
    op.drop_index('ix_content_actions_created_at', table_name='content_actions')
    op.drop_index('ix_content_actions_status', table_name='content_actions')
    op.drop_index('ix_content_actions_query', table_name='content_actions')
    op.drop_index('ix_content_actions_post_id', table_name='content_actions')
    op.drop_index('ix_content_actions_action_type', table_name='content_actions')
    op.drop_index('ix_content_actions_action_id', table_name='content_actions')
    op.drop_index('ix_content_actions_id', table_name='content_actions')
    op.drop_table('content_actions')
