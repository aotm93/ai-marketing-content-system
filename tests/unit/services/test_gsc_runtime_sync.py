import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("PRIMARY_AI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_gsc_runtime_sync.db")
os.environ.setdefault("WORDPRESS_URL", "https://example.com")
os.environ.setdefault("WORDPRESS_USERNAME", "tester")
os.environ.setdefault("WORDPRESS_PASSWORD", "tester")
os.environ.setdefault("ADMIN_PASSWORD", "tester")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-secret")

from src.config import settings
from src.services.gsc_runtime import inspect_gsc_schema, resolve_gsc_runtime


def test_resolve_gsc_runtime_supports_path_credentials(monkeypatch):
    original = {
        "gsc_enabled": settings.gsc_enabled,
        "gsc_site_url": settings.gsc_site_url,
        "gsc_auth_method": settings.gsc_auth_method,
        "gsc_credentials_json": settings.gsc_credentials_json,
        "gsc_credentials_path": settings.gsc_credentials_path,
    }

    settings.gsc_enabled = True
    settings.gsc_site_url = "sc-domain:example.com"
    settings.gsc_auth_method = "service_account"
    settings.gsc_credentials_json = None
    settings.gsc_credentials_path = "C:/tmp/gsc.json"

    try:
        runtime = resolve_gsc_runtime()
        assert runtime.configured is True
        assert runtime.credential_source == "path"
    finally:
        for key, value in original.items():
            setattr(settings, key, value)


def test_resolve_gsc_runtime_prefers_json_credentials_when_present():
    original = {
        "gsc_enabled": settings.gsc_enabled,
        "gsc_site_url": settings.gsc_site_url,
        "gsc_auth_method": settings.gsc_auth_method,
        "gsc_credentials_json": settings.gsc_credentials_json,
        "gsc_credentials_path": settings.gsc_credentials_path,
    }

    settings.gsc_enabled = True
    settings.gsc_site_url = "sc-domain:example.com"
    settings.gsc_auth_method = "service_account"
    settings.gsc_credentials_json = "{\"type\":\"service_account\"}"
    settings.gsc_credentials_path = "C:/tmp/gsc.json"

    try:
        runtime = resolve_gsc_runtime()
        assert runtime.configured is True
        assert runtime.credential_source == "json"
    finally:
        for key, value in original.items():
            setattr(settings, key, value)


def test_inspect_gsc_schema_reports_degraded_materialization_when_columns_missing():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE opportunities (id INTEGER PRIMARY KEY, opportunity_id VARCHAR(36), opportunity_type VARCHAR(50), target_query TEXT, target_page TEXT)"))
        connection.execute(text("CREATE TABLE gsc_queries (id INTEGER PRIMARY KEY)"))

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        schema = inspect_gsc_schema(db)
    finally:
        db.close()
        engine.dispose()

    assert schema["status"] == "degraded"
    assert schema["opportunity_materialization_ready"] is False
    assert "engine_mode" in schema["missing_columns"]["opportunities"]
