"""Tests for rotation history helpers in scheduler jobs."""

from src.scheduler.jobs import ROTATION_HISTORY_LIMIT, _dedupe_rotation_history


class TestJobsRotationHistory:
    """Validate restart-safe rotation history ordering."""

    def test_keeps_most_recent_duplicate_at_tail(self):
        history = ["alpha", "beta", "alpha", "gamma"]

        assert _dedupe_rotation_history(history) == ["beta", "alpha", "gamma"]

    def test_enforces_limit_after_refreshing_duplicate(self):
        history = [f"item{i}" for i in range(ROTATION_HISTORY_LIMIT)] + ["item0"]

        deduped = _dedupe_rotation_history(history)

        assert len(deduped) == ROTATION_HISTORY_LIMIT
        assert deduped[0] == "item1"
        assert deduped[-1] == "item0"
