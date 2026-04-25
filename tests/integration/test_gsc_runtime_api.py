import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("PRIMARY_AI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_gsc_runtime_api.db")
os.environ.setdefault("WORDPRESS_URL", "https://example.com")
os.environ.setdefault("WORDPRESS_USERNAME", "tester")
os.environ.setdefault("WORDPRESS_PASSWORD", "tester")
os.environ.setdefault("ADMIN_PASSWORD", "tester")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-secret")

import src.models  # noqa: F401
from src.api.gsc import router as gsc_router
from src.api.opportunities import router as opportunities_router
from src.config import settings
from src.core.auth import get_current_admin
from src.core.database import get_db
from src.models.base import Base


TEST_DB_PATH = Path("test_gsc_runtime_api.sqlite")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH.as_posix()}"


class FakeOpportunityRow:
    def __init__(self, query: str, page: str, impressions: int, clicks: int, ctr: float, position: float):
        self.query = query
        self.page = page
        self.impressions = impressions
        self.clicks = clicks
        self.ctr = ctr
        self.position = position


class FakeGSCClient:
    instances = []

    def __init__(self, site_url, auth_method=None, credentials_path=None, credentials_json=None):
        self.site_url = site_url
        self.auth_method = auth_method
        self.credentials_path = credentials_path
        self.credentials_json = credentials_json
        type(self).instances.append(self)

    def health_check(self):
        return {
            "status": "connected",
            "site_url": self.site_url,
            "permission_level": "siteOwner",
            "accessible_sites": [self.site_url],
        }

    def get_low_hanging_fruits(self, days=28, limit=100):
        return [
            FakeOpportunityRow(
                query="custom bottle supplier",
                page="https://example.com/custom-bottles",
                impressions=640,
                clicks=42,
                ctr=0.022,
                position=7.1,
            )
        ][:limit]


@pytest.fixture()
def app_client(monkeypatch):
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(gsc_router)
    app.include_router(opportunities_router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_current_admin] = lambda: {"username": "admin", "role": "admin"}
    app.dependency_overrides[get_db] = override_get_db

    original_settings = {
        "gsc_enabled": settings.gsc_enabled,
        "gsc_site_url": settings.gsc_site_url,
        "gsc_auth_method": settings.gsc_auth_method,
        "gsc_credentials_json": settings.gsc_credentials_json,
        "gsc_credentials_path": settings.gsc_credentials_path,
        "gsc_opportunity_sync_enabled": settings.gsc_opportunity_sync_enabled,
        "gsc_sync_days_back": settings.gsc_sync_days_back,
    }

    monkeypatch.setattr("src.services.gsc_runtime.GSCClient", FakeGSCClient)

    with TestClient(app) as client:
        yield client

    for key, value in original_settings.items():
        setattr(settings, key, value)

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


def test_gsc_status_returns_503_when_disabled(app_client):
    settings.gsc_enabled = False
    settings.gsc_site_url = "sc-domain:example.com"
    settings.gsc_credentials_path = "C:/tmp/gsc.json"
    settings.gsc_credentials_json = None

    response = app_client.get("/api/v1/gsc/status")

    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "disabled"


def test_gsc_path_credentials_support_materialization_and_idempotency(app_client):
    settings.gsc_enabled = True
    settings.gsc_site_url = "sc-domain:example.com"
    settings.gsc_auth_method = "service_account"
    settings.gsc_credentials_json = None
    settings.gsc_credentials_path = "C:/tmp/gsc-service-account.json"
    settings.gsc_opportunity_sync_enabled = True

    FakeGSCClient.instances.clear()

    status_response = app_client.get("/api/v1/gsc/status")
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["credential_source"] == "path"
    assert FakeGSCClient.instances[-1].credentials_path == "C:/tmp/gsc-service-account.json"

    materialize_response = app_client.post(
        "/api/v1/gsc/materialize-opportunities",
        json={"days": 7, "limit": 20},
    )
    assert materialize_response.status_code == 200
    assert materialize_response.json()["created"] == 1

    list_response = app_client.get("/api/v1/opportunities/")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["opportunities"][0]["type"] == "low_hanging_fruit"
    assert payload["opportunities"][0]["recommended_action_family"] == "ctr_optimize"
    assert payload["opportunities"][0]["engine_mode"] == "gsc_materialized"

    second_response = app_client.post(
        "/api/v1/gsc/materialize-opportunities",
        json={"days": 7, "limit": 20},
    )
    assert second_response.status_code == 200
    assert second_response.json()["updated"] >= 1

    list_response = app_client.get("/api/v1/opportunities/")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1


def test_gsc_dependency_failure_returns_server_error_not_http_200(app_client, monkeypatch):
    class FailingGSCClient:
        def __init__(self, *args, **kwargs):
            raise ValueError("invalid service account payload")

    settings.gsc_enabled = True
    settings.gsc_site_url = "sc-domain:example.com"
    settings.gsc_auth_method = "service_account"
    settings.gsc_credentials_json = "{\"type\": \"service_account\"}"
    settings.gsc_credentials_path = None

    monkeypatch.setattr("src.services.gsc_runtime.GSCClient", FailingGSCClient)

    response = app_client.get("/api/v1/gsc/opportunities")

    assert response.status_code == 500
    assert response.json()["detail"]["error"] == "invalid service account payload"
