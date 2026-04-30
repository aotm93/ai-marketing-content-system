import pytest

from src.scheduler.job_runner import JobConfig, JobRunner, JobStatus


@pytest.mark.asyncio
async def test_returned_failed_status_is_treated_as_job_failure(monkeypatch):
    runner = JobRunner(
        JobConfig(
            max_posts_per_day=1,
            publish_interval_minutes=60,
            max_retries=0,
            retry_base_delay_seconds=0,
        )
    )

    async def noop_persist(_result):
        return None

    async def job_returns_failure(_data):
        return {"status": "failed", "error": "publishing failed"}

    monkeypatch.setattr(runner, "_persist_job_result", noop_persist)

    result = await runner.run_job("content_generation", job_returns_failure, {})

    assert result.status == JobStatus.FAILED
    assert result.error_message == "publishing failed"
    assert runner.rate_limiter.daily_count == 0
    assert runner.rate_limiter.last_execution is None


@pytest.mark.asyncio
async def test_returned_error_status_retries_before_failing(monkeypatch):
    runner = JobRunner(
        JobConfig(
            max_posts_per_day=1,
            publish_interval_minutes=60,
            max_retries=1,
            retry_base_delay_seconds=0,
            retry_max_delay_seconds=0,
        )
    )
    calls = []

    async def noop_persist(_result):
        return None

    async def job_returns_error(_data):
        calls.append("attempt")
        return {"status": "error", "message": "content generation error"}

    monkeypatch.setattr(runner, "_persist_job_result", noop_persist)

    result = await runner.run_job("content_generation", job_returns_error, {})

    assert calls == ["attempt", "attempt"]
    assert result.status == JobStatus.FAILED
    assert result.error_message == "content generation error"
    assert result.retry_count == 1
    assert runner.rate_limiter.daily_count == 0