"""Tests for rotation history helpers in scheduler jobs."""

from types import SimpleNamespace

from src.scheduler.jobs import (
    ROTATION_HISTORY_LIMIT,
    _collapse_content_candidate_clusters,
    _content_candidate_cluster_key,
    _dedupe_rotation_history,
)


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

    def test_cluster_key_prefers_route_target_over_raw_keyword(self):
        candidate = SimpleNamespace(
            keyword="30ml PET spray bottle wholesale",
            page_type="wholesale_faq",
            route_target_url=None,
            route_target_name="Spray Bottles",
            primary_taxonomy_url=None,
            primary_taxonomy_name=None,
            semantic_group="product_30ml-pet-spray-bottle",
            category="Spray Bottles",
        )

        assert _content_candidate_cluster_key(candidate) == "wholesale_faq|Spray Bottles"

    def test_collapse_content_candidates_keeps_highest_ranked_cluster_member(self):
        candidates = [
            SimpleNamespace(
                keyword="spray bottles wholesale",
                page_type="wholesale_faq",
                route_target_url=None,
                route_target_name="Spray Bottles",
                primary_taxonomy_url=None,
                primary_taxonomy_name=None,
                semantic_group="catalog_spray-bottles",
                category="Spray Bottles",
            ),
            SimpleNamespace(
                keyword="spray bottles supplier",
                page_type="wholesale_faq",
                route_target_url=None,
                route_target_name="Spray Bottles",
                primary_taxonomy_url=None,
                primary_taxonomy_name=None,
                semantic_group="catalog_ops_spray-bottles",
                category="Spray Bottles",
            ),
            SimpleNamespace(
                keyword="foam bottles wholesale",
                page_type="wholesale_faq",
                route_target_url=None,
                route_target_name="Foam Bottles",
                primary_taxonomy_url=None,
                primary_taxonomy_name=None,
                semantic_group="catalog_foam-bottles",
                category="Foam Bottles",
            ),
        ]

        collapsed = _collapse_content_candidate_clusters(candidates)

        assert [candidate.keyword for candidate in collapsed] == [
            "spray bottles wholesale",
            "foam bottles wholesale",
        ]
