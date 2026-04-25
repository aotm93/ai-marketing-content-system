import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("PRIMARY_AI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_gsc_priority_admin_api.db")
os.environ.setdefault("WORDPRESS_URL", "https://example.com")
os.environ.setdefault("WORDPRESS_USERNAME", "tester")
os.environ.setdefault("WORDPRESS_PASSWORD", "tester")
os.environ.setdefault("ADMIN_PASSWORD", "tester")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-secret")

import src.models  # noqa: F401
from src.api.admin import router as admin_router
from src.api.opportunities import router as opportunities_router
from src.core.auth import get_current_admin
from src.core.database import get_db
from src.models.base import Base
from src.models.gsc_data import Opportunity


TEST_DB_PATH = Path("test_gsc_priority_admin_api.sqlite")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH.as_posix()}"


@pytest.fixture()
def app_client():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(admin_router)
    app.include_router(opportunities_router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_current_admin] = lambda: {"username": "admin", "role": "admin"}
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client, TestingSessionLocal

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


def test_admin_config_normalizes_priority_steering_inputs(app_client):
    client, _ = app_client

    response = client.put(
        "/api/v1/admin/config",
        json={"config_key": "GSC_ENABLED", "config_value": "True"},
    )
    assert response.status_code == 200

    response = client.put(
        "/api/v1/admin/config",
        json={
            "config_key": "REFERENCE_KEYWORDS",
            "config_value": "custom bottles\n\nCustom Bottles\nquote request\n",
        },
    )
    assert response.status_code == 200

    response = client.put(
        "/api/v1/admin/config",
        json={"config_key": "CLUSTER_ENGINE_SHADOW_ENABLED", "config_value": "True"},
    )
    assert response.status_code == 200

    response = client.get("/api/v1/admin/config")
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["gsc_enabled"] == "True"
    assert "gsc_opportunity_sync_enabled" in data
    assert data["reference_keywords"] == "custom bottles\nquote request"
    assert data["cluster_engine_shadow_enabled"] == "True"


def test_opportunities_api_returns_cluster_priority_fields(app_client):
    client, session_factory = app_client
    db = session_factory()
    try:
        db.add(
            Opportunity(
                opportunity_id="cluster_123",
                opportunity_type="cluster_priority",
                target_query="custom bottle supplier",
                target_page="https://example.com/custom-bottles",
                score=82.5,
                confidence=0.81,
                current_impressions=1200,
                current_clicks=88,
                current_ctr=0.031,
                current_position=6.8,
                potential_clicks=140,
                status="pending",
                priority="high",
                cluster_id="cluster-123",
                cluster_name="Custom Bottle Supplier Cluster",
                cluster_version="v1",
                decision_unit_type="cluster",
                recommended_action_family="ctr_optimize",
                recommended_action_confidence=0.81,
                score_breakdown_json=json.dumps({"demand": 0.72, "admin_steering_modifier": 0.08}),
                steering_matches_json=json.dumps({"reference_keywords": ["custom bottles"]}),
                support_role="primary",
                target_asset_type="category",
                engine_mode="shadow",
                engine_version="v1",
                fallback_reason=None,
                shadow_rank=1,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/opportunities/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1

    opportunity = payload["opportunities"][0]
    assert opportunity["type"] == "cluster_priority"
    assert opportunity["cluster_id"] == "cluster-123"
    assert opportunity["cluster_name"] == "Custom Bottle Supplier Cluster"
    assert opportunity["recommended_action_family"] == "ctr_optimize"
    assert opportunity["score_breakdown"]["demand"] == 0.72
    assert opportunity["steering_matches"]["reference_keywords"] == ["custom bottles"]
    assert opportunity["engine_mode"] == "shadow"


def test_execute_generate_opportunity_runs_real_job_and_persists_result(app_client, monkeypatch):
    client, session_factory = app_client
    db = session_factory()
    try:
        db.add(
            Opportunity(
                opportunity_id="cluster_generate_123",
                opportunity_type="new_page",
                target_query="custom bottle supplier",
                target_page="https://example.com/custom-bottles",
                score=82.5,
                confidence=0.81,
                current_impressions=1200,
                current_clicks=88,
                current_ctr=0.031,
                current_position=6.8,
                potential_clicks=140,
                status="pending",
                priority="high",
            )
        )
        db.commit()
    finally:
        db.close()

    async def fake_run_opportunity_job(job_type, job_data):
        assert job_type == "content_generation"
        assert job_data["target_keyword"] == "custom bottle supplier"
        return SimpleNamespace(
            job_id="job-real-123",
            status=SimpleNamespace(value="success"),
            to_dict=lambda: {
                "job_id": "job-real-123",
                "job_type": "content_generation",
                "status": "success",
                "result_data": {"wordpress_post_id": 321},
            },
        )

    monkeypatch.setattr("src.api.opportunities._run_opportunity_job", fake_run_opportunity_job)

    response = client.post(
        "/api/v1/opportunities/cluster_generate_123/execute",
        json={"action": "generate", "params": {}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-real-123"
    assert payload["result"]["status"] == "success"

    db = session_factory()
    try:
        opportunity = db.query(Opportunity).filter(Opportunity.opportunity_id == "cluster_generate_123").first()
        assert opportunity is not None
        assert opportunity.status == "completed"
        assert opportunity.execution_job_id == "job-real-123"
        assert opportunity.result_status == "success"
        assert json.loads(opportunity.result_data)["job_id"] == "job-real-123"
    finally:
        db.close()
