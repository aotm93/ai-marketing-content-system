"""
Alembic migration for backlink opportunities table

Revision ID: p3_001_backlink_opportunities
Create Date: 2026-02-11

Creates table:
- backlink_opportunities: Stores backlink opportunities discovered via DataForSEO API
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers
revision = 'p3_001_backlink_opportunities'
down_revision = 'p1_004_gsc_usage_indexing'  # Previous migration
branch_labels = None
depends_on = None


def upgrade():
    # Backlink Opportunities table
    op.create_table(
        'backlink_opportunities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('target_url', sa.String(1024), nullable=False),
        sa.Column('target_domain', sa.String(255), nullable=False),
        sa.Column('opportunity_type', sa.Enum('UNLINKED_MENTION', 'RESOURCE_PAGE', 'BROKEN_LINK', 
                                               'COMPETITOR_BACKLINK', 'GUEST_POST', name='opportunitytype'), 
                  nullable=False),
        sa.Column('domain_authority', sa.Integer(), nullable=True),
        sa.Column('page_authority', sa.Integer(), nullable=True),
        sa.Column('traffic_estimate', sa.Integer(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_name', sa.String(255), nullable=True),
        sa.Column('outreach_status', sa.Enum('DISCOVERED', 'DRAFTED', 'SENT', 'REPLIED', 
                                              'ACCEPTED', 'DECLINED', 'NO_RESPONSE', name='outreachstatus'), 
                  nullable=False, server_default='DISCOVERED'),
        sa.Column('brand_mention', sa.String(1024), nullable=True),
        sa.Column('anchor_text_suggestion', sa.String(512), nullable=True),
        sa.Column('suggested_link_url', sa.String(1024), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_backlink_target_domain', 'backlink_opportunities', ['target_domain'])
    op.create_index('ix_backlink_status', 'backlink_opportunities', ['outreach_status'])
    op.create_index('ix_backlink_relevance', 'backlink_opportunities', ['relevance_score'])
    op.create_index('ix_backlink_unique', 'backlink_opportunities', ['target_url', 'opportunity_type'], unique=True)


def downgrade():
    # Drop indexes
    op.drop_index('ix_backlink_unique', table_name='backlink_opportunities')
    op.drop_index('ix_backlink_relevance', table_name='backlink_opportunities')
    op.drop_index('ix_backlink_status', table_name='backlink_opportunities')
    op.drop_index('ix_backlink_target_domain', table_name='backlink_opportunities')
    
    # Drop table
    op.drop_table('backlink_opportunities')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS opportunitytype")
    op.execute("DROP TYPE IF EXISTS outreachstatus")
