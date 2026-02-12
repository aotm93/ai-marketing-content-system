"""
Alembic migration for email tables

Revision ID: p3_002_email_tables
Create Date: 2026-02-11

Creates tables:
- email_subscribers: Stores email subscribers
- email_sequences: Stores email sequence definitions
- email_sequence_steps: Stores steps within sequences
- email_enrollments: Tracks subscriber enrollment in sequences
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers
revision = 'p3_002_email_tables'
down_revision = 'p3_001_backlink_opportunities'  # Previous migration
branch_labels = None
depends_on = None


def upgrade():
    # Email Subscribers table
    op.create_table(
        'email_subscribers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(255), nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('subscribed_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('unsubscribed_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_email_subscriber_email', 'email_subscribers', ['email'])
    op.create_index('ix_email_subscriber_active', 'email_subscribers', ['is_active'])
    
    # Email Sequences table
    op.create_table(
        'email_sequences',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Email Sequence Steps table
    op.create_table(
        'email_sequence_steps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sequence_id', sa.Integer(), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('html_body', sa.Text(), nullable=False),
        sa.Column('delay_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['sequence_id'], ['email_sequences.id'], ondelete='CASCADE')
    )
    
    # Email Enrollments table
    op.create_table(
        'email_enrollments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('subscriber_id', sa.Integer(), nullable=False),
        sa.Column('sequence_id', sa.Integer(), nullable=False),
        sa.Column('current_step', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.Enum('ACTIVE', 'COMPLETED', 'CANCELLED', name='enrollmentstatus'), 
                  nullable=False, server_default='ACTIVE'),
        sa.Column('enrolled_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_step_sent_at', sa.DateTime(), nullable=True),
        sa.Column('next_step_due_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subscriber_id'], ['email_subscribers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sequence_id'], ['email_sequences.id'], ondelete='CASCADE')
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table('email_enrollments')
    op.drop_table('email_sequence_steps')
    op.drop_table('email_sequences')
    op.drop_index('ix_email_subscriber_active', table_name='email_subscribers')
    op.drop_index('ix_email_subscriber_email', table_name='email_subscribers')
    op.drop_table('email_subscribers')
    
    # Drop enum type
    op.execute("DROP TYPE IF EXISTS enrollmentstatus")
