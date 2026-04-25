"""Add cluster-priority shadow fields for demand-first GSC orchestration."""

from alembic import op
import sqlalchemy as sa


revision = "p1_005_gsc_priority_shadow"
down_revision = "p3_002_email_tables"
branch_labels = None
depends_on = None


def upgrade():
    opportunity_columns = [
        sa.Column("cluster_id", sa.String(length=64), nullable=True),
        sa.Column("cluster_name", sa.String(length=255), nullable=True),
        sa.Column("cluster_version", sa.String(length=32), nullable=True),
        sa.Column("decision_unit_type", sa.String(length=50), nullable=True),
        sa.Column("recommended_action_family", sa.String(length=50), nullable=True),
        sa.Column("recommended_action_confidence", sa.Float(), server_default="0.0"),
        sa.Column("score_breakdown_json", sa.Text(), nullable=True),
        sa.Column("steering_matches_json", sa.Text(), nullable=True),
        sa.Column("decision_trace_json", sa.Text(), nullable=True),
        sa.Column("support_role", sa.String(length=30), nullable=True),
        sa.Column("target_asset_type", sa.String(length=50), nullable=True),
        sa.Column("engine_mode", sa.String(length=20), nullable=True),
        sa.Column("engine_version", sa.String(length=32), nullable=True),
        sa.Column("fallback_reason", sa.Text(), nullable=True),
        sa.Column("decision_window_key", sa.String(length=128), nullable=True),
        sa.Column("shadow_rank", sa.Integer(), nullable=True),
    ]
    for column in opportunity_columns:
        op.add_column("opportunities", column)

    op.create_index("ix_opportunities_cluster_id", "opportunities", ["cluster_id"])
    op.create_index("ix_opportunities_recommended_action_family", "opportunities", ["recommended_action_family"])
    op.create_index("ix_opportunities_engine_mode", "opportunities", ["engine_mode"])
    op.create_index("ix_opportunities_decision_window_key", "opportunities", ["decision_window_key"])

    topic_cluster_columns = [
        sa.Column("cluster_version", sa.String(length=32), nullable=True),
        sa.Column("canonical_topic", sa.String(length=255), nullable=True),
        sa.Column("intent_band", sa.String(length=50), nullable=True),
        sa.Column("member_count", sa.Integer(), server_default="0"),
        sa.Column("business_intent_score", sa.Float(), server_default="0.0"),
        sa.Column("conversion_proximity_score", sa.Float(), server_default="0.0"),
        sa.Column("support_coverage_score", sa.Float(), server_default="0.0"),
        sa.Column("demand_freshness_hours", sa.Float(), server_default="0.0"),
        sa.Column("last_gsc_sync_at", sa.DateTime(), nullable=True),
        sa.Column("cluster_members_json", sa.Text(), nullable=True),
    ]
    for column in topic_cluster_columns:
        op.add_column("topic_clusters", column)

    content_action_columns = [
        sa.Column("cluster_id", sa.String(length=64), nullable=True),
        sa.Column("decision_window_key", sa.String(length=128), nullable=True),
        sa.Column("decision_snapshot", sa.JSON(), nullable=True),
    ]
    for column in content_action_columns:
        op.add_column("content_actions", column)

    op.create_index("ix_content_actions_cluster_id", "content_actions", ["cluster_id"])
    op.create_index("ix_content_actions_decision_window_key", "content_actions", ["decision_window_key"])


def downgrade():
    op.drop_index("ix_content_actions_decision_window_key", table_name="content_actions")
    op.drop_index("ix_content_actions_cluster_id", table_name="content_actions")
    op.drop_column("content_actions", "decision_snapshot")
    op.drop_column("content_actions", "decision_window_key")
    op.drop_column("content_actions", "cluster_id")

    op.drop_column("topic_clusters", "cluster_members_json")
    op.drop_column("topic_clusters", "last_gsc_sync_at")
    op.drop_column("topic_clusters", "demand_freshness_hours")
    op.drop_column("topic_clusters", "support_coverage_score")
    op.drop_column("topic_clusters", "conversion_proximity_score")
    op.drop_column("topic_clusters", "business_intent_score")
    op.drop_column("topic_clusters", "member_count")
    op.drop_column("topic_clusters", "intent_band")
    op.drop_column("topic_clusters", "canonical_topic")
    op.drop_column("topic_clusters", "cluster_version")

    op.drop_index("ix_opportunities_decision_window_key", table_name="opportunities")
    op.drop_index("ix_opportunities_engine_mode", table_name="opportunities")
    op.drop_index("ix_opportunities_recommended_action_family", table_name="opportunities")
    op.drop_index("ix_opportunities_cluster_id", table_name="opportunities")
    op.drop_column("opportunities", "shadow_rank")
    op.drop_column("opportunities", "decision_window_key")
    op.drop_column("opportunities", "fallback_reason")
    op.drop_column("opportunities", "engine_version")
    op.drop_column("opportunities", "engine_mode")
    op.drop_column("opportunities", "target_asset_type")
    op.drop_column("opportunities", "support_role")
    op.drop_column("opportunities", "decision_trace_json")
    op.drop_column("opportunities", "steering_matches_json")
    op.drop_column("opportunities", "score_breakdown_json")
    op.drop_column("opportunities", "recommended_action_confidence")
    op.drop_column("opportunities", "recommended_action_family")
    op.drop_column("opportunities", "decision_unit_type")
    op.drop_column("opportunities", "cluster_version")
    op.drop_column("opportunities", "cluster_name")
    op.drop_column("opportunities", "cluster_id")
