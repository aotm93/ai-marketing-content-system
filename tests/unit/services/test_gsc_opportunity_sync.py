import os

os.environ.setdefault("PRIMARY_AI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_gsc_opportunity_sync.db")
os.environ.setdefault("WORDPRESS_URL", "https://example.com")
os.environ.setdefault("WORDPRESS_USERNAME", "tester")
os.environ.setdefault("WORDPRESS_PASSWORD", "tester")
os.environ.setdefault("ADMIN_PASSWORD", "tester")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-secret")

from datetime import datetime, timezone

from src.config import settings
from src.services import gsc_opportunity_sync


class _FakeDateTime:
    last_tz = None

    @classmethod
    def now(cls, tz=None):
        cls.last_tz = tz
        return datetime(2026, 4, 25, 12, 0, tzinfo=tz)


class _DummyClient:
    site_url = "sc-domain:example.com"


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
