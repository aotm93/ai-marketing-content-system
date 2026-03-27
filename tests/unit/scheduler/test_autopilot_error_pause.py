from datetime import date, timedelta

import pytest

from src.scheduler.autopilot import AutopilotConfig, AutopilotScheduler
from src.scheduler.job_runner import JobRunner


def build_scheduler(monkeypatch) -> AutopilotScheduler:
    config = AutopilotConfig(
        enabled=True,
        publish_interval_minutes=60,
        pause_on_errors=3,
        active_hours_start=0,
        active_hours_end=24,
    )
    scheduler = AutopilotScheduler(config)
    scheduler.job_runner = JobRunner(config.to_job_config())

    async def noop_persist(_result):
        return None

    monkeypatch.setattr(scheduler.job_runner, "_persist_job_result", noop_persist)
    return scheduler


@pytest.mark.asyncio
async def test_auto_pause_does_not_globally_pause_scheduler(monkeypatch):
    scheduler = build_scheduler(monkeypatch)
    scheduler._consecutive_errors = scheduler.config.pause_on_errors

    job_calls = []

    async def mock_job(_ctx):
        job_calls.append("ran")
        return {"status": "success"}

    scheduler.register_job("content_generation", mock_job)

    def fail_pause():
        raise AssertionError("auto-pause should not call APScheduler.pause()")

    monkeypatch.setattr(scheduler, "pause", fail_pause)

    await scheduler._run_generation_cycle()

    assert scheduler._paused_by_errors is True
    assert scheduler._consecutive_errors == scheduler.config.pause_on_errors
    assert job_calls == []


@pytest.mark.asyncio
async def test_auto_pause_resets_on_new_day_and_runs_job(monkeypatch):
    scheduler = build_scheduler(monkeypatch)
    scheduler._consecutive_errors = scheduler.config.pause_on_errors
    scheduler._paused_by_errors = True
    scheduler._last_error_reset_date = date.today() - timedelta(days=1)

    job_calls = []

    async def mock_job(_ctx):
        job_calls.append("ran")
        return {"status": "success"}

    scheduler.register_job("content_generation", mock_job)

    await scheduler._run_generation_cycle()

    assert scheduler._paused_by_errors is False
    assert scheduler._consecutive_errors == 0
    assert scheduler._successful_runs == 1
    assert job_calls == ["ran"]
