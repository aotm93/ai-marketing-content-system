import os

os.environ.setdefault("PRIMARY_AI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_gsc_opportunity_sync.db")
os.environ.setdefault("WORDPRESS_URL", "https://example.com")
os.environ.setdefault("WORDPRESS_USERNAME", "tester")
os.environ.setdefault("WORDPRESS_PASSWORD", "tester")
os.environ.setdefault("ADMIN_PASSWORD", "tester")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-secret")

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.models  # noqa: F401
from src.config import settings
from src.models.base import Base
from src.models.gsc_data import Opportunity
from src.services import gsc_opportunity_sync


class _FakeDateTime:
    last_tz = None

    @classmethod
    def now(cls, tz=None):
        cls.last_tz = tz
        return datetime(2026, 4, 25, 12, 0, tzinfo=tz)


class _DummyClient:
    site_url = "sc-domain:example.com"


class _DiscoveryFallbackClient:
    site_url = "sc-domain:example.com"

    def get_low_hanging_fruits(self, days=28, limit=100):
        return []

    def get_search_analytics(self, start_date, end_date, dimensions=None, row_limit=25000):
        return [
            SimpleNamespace(
                query="wholesale oil bottles with dropper",
                page="https://example.com/collections/oil-bottles",
                impressions=31,
                clicks=0,
                ctr=0.0,
                position=101.3,
            )
        ]


TEST_DB_PATH = Path("test_gsc_opportunity_sync_materialize.sqlite")


def test_materialize_gsc_opportunities_uses_timezone_utc_when_now_missing(monkeypatch):
    original_enabled = settings.gsc_opportunity_sync_enabled
    settings.gsc_opportunity_sync_enabled = False

    monkeypatch.setattr(
        gsc_opportunity_sync,
        "inspect_gsc_schema",
        lambda db: {"opportunity_materialization_ready": True},
    )
    monkeypatch.setattr(gsc_opportunity_sync, "datetime", _FakeDateTime)

    try:
        result = gsc_opportunity_sync.materialize_gsc_opportunities(
            db=object(),
            client=_DummyClient(),
        )
    finally:
        settings.gsc_opportunity_sync_enabled = original_enabled

    assert result["status"] == "disabled"
    assert _FakeDateTime.last_tz is timezone.utc


def test_materialize_gsc_opportunities_falls_back_to_discovery_candidates():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    engine = create_engine(
        f"sqlite:///{TEST_DB_PATH.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    original_enabled = settings.gsc_opportunity_sync_enabled
    settings.gsc_opportunity_sync_enabled = True

    db = SessionLocal()
    try:
        result = gsc_opportunity_sync.materialize_gsc_opportunities(
            db=db,
            client=_DiscoveryFallbackClient(),
            days=28,
            limit=20,
            now=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
        )

        opportunity = db.query(Opportunity).one()
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
        settings.gsc_opportunity_sync_enabled = original_enabled

    assert result["status"] == "success"
    assert result["materialization_strategy"] == "discovery_fallback"
    assert result["created"] == 1
    assert result["live_opportunity_count"] == 1
    assert opportunity.opportunity_type == "new_page"
    assert opportunity.action_type == "generate"
    assert opportunity.recommended_action_family == "new_content"
    assert opportunity.engine_mode == "gsc_discovery_fallback"
    assert opportunity.fallback_reason == "no_low_hanging_fruits"
