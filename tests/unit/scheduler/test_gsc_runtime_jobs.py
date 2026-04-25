import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("PRIMARY_AI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_gsc_runtime_jobs.db")
os.environ.setdefault("WORDPRESS_URL", "https://example.com")
os.environ.setdefault("WORDPRESS_USERNAME", "tester")
os.environ.setdefault("WORDPRESS_PASSWORD", "tester")
os.environ.setdefault("ADMIN_PASSWORD", "tester")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-secret")

from src.scheduler import jobs


class FakeReport:
    total_issues = 0
    issues_by_severity = {"critical": 0, "high": 0}
    health_score = 100
    summary = "ok"
    top_priorities = []


class FakeDetector:
    async def analyze(self, gsc_data, min_impressions=20):
        assert len(gsc_data) == 1
        return FakeReport()


class FakeClient:
    def get_search_analytics(self, start_date, end_date, dimensions, row_limit):
        row = {"query": "custom bottle supplier", "page": "https://example.com/custom-bottles", "impressions": 400, "clicks": 30, "ctr": 2.5, "position": 7.0}
        return [SimpleNamespace(to_dict=lambda row=row: row)]


@pytest.mark.asyncio
async def test_cannibalization_job_uses_shared_gsc_runtime_helper(monkeypatch):
    helper_calls = {"count": 0}

    def fake_get_gsc_client_or_none():
        helper_calls["count"] += 1
        return FakeClient()

    monkeypatch.setattr(jobs, "get_gsc_client_or_none", fake_get_gsc_client_or_none)

    import src.services.cannibalization as cannibalization

    monkeypatch.setattr(cannibalization, "CannibalizationDetector", FakeDetector)

    result = await jobs.cannibalization_analysis_job({"min_impressions": 20})

    assert helper_calls["count"] == 1
    assert result["status"] == "success"
