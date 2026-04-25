from sqlalchemy import create_engine

from src.core.database import infer_migration_baseline


def test_infer_migration_baseline_returns_none_when_alembic_version_exists():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")

    assert infer_migration_baseline(engine) is None


def test_infer_migration_baseline_detects_gsc_schema():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE opportunities (id INTEGER PRIMARY KEY, opportunity_id VARCHAR(36))")

    assert infer_migration_baseline(engine) == "p1_001_gsc_opportunities"


def test_infer_migration_baseline_prefers_latest_detectable_legacy_revision():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE job_runs (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql(
            "CREATE TABLE content_actions (id INTEGER PRIMARY KEY, query TEXT, reason TEXT, metrics_before TEXT, metrics_after TEXT)"
        )
        conn.exec_driver_sql("CREATE TABLE email_subscribers (id INTEGER PRIMARY KEY, email TEXT)")

    assert infer_migration_baseline(engine) == "p3_002_email_tables"
