import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("PRIMARY_AI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_opportunities_schema_guard.db")
os.environ.setdefault("WORDPRESS_URL", "https://example.com")
os.environ.setdefault("WORDPRESS_USERNAME", "tester")
os.environ.setdefault("WORDPRESS_PASSWORD", "tester")
os.environ.setdefault("ADMIN_PASSWORD", "tester")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-secret")

from src.api.opportunities import router as opportunities_router
from src.core.auth import get_current_admin
from src.core.database import get_db


TEST_DB_PATH = Path("test_opportunities_schema_guard.sqlite")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH.as_posix()}"

LEGACY_OPPORTUNITIES_SQL = """
CREATE TABLE opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id VARCHAR(36) NOT NULL,
    opportunity_type VARCHAR(50) NOT NULL,
    target_query VARCHAR(500),
    target_page VARCHAR(1024),
    target_post_id INTEGER,
    score FLOAT DEFAULT 0.0,
    potential_clicks INTEGER DEFAULT 0,
    confidence FLOAT DEFAULT 0.0,
    current_position FLOAT,
    current_impressions INTEGER,
    current_ctr FLOAT,
    current_clicks INTEGER,
    action_type VARCHAR(50),
    action_details TEXT,
    status VARCHAR(20),
    priority VARCHAR(20),
    assigned_to VARCHAR(100),
    executed_at DATETIME,
    execution_job_id VARCHAR(36),
    result_status VARCHAR(20),
    result_data TEXT,
    created_at DATETIME,
    updated_at DATETIME
)
"""


@pytest.fixture()
def legacy_app_client():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    with engine.begin() as connection:
        connection.exec_driver_sql(LEGACY_OPPORTUNITIES_SQL)

    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    app = FastAPI()
    app.include_router(opportunities_router)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_current_admin] = lambda: {"username": "admin", "role": "admin"}
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


def test_list_opportunities_returns_409_for_legacy_schema(legacy_app_client):
    response = legacy_app_client.get("/api/v1/opportunities/")

    assert response.status_code == 409

    detail = response.json()["detail"]
    assert detail["reason"] == "opportunity_schema_not_ready"
    assert detail["schema"]["status"] == "degraded"
    assert detail["schema"]["opportunity_materialization_ready"] is False
    assert "cluster_id" in detail["schema"]["missing_columns"]["opportunities"]
