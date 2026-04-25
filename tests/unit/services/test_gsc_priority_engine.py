import os
from datetime import datetime

os.environ.setdefault("PRIMARY_AI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///test_gsc_priority_engine.db")
os.environ.setdefault("WORDPRESS_URL", "https://example.com")
os.environ.setdefault("WORDPRESS_USERNAME", "tester")
os.environ.setdefault("WORDPRESS_PASSWORD", "tester")
os.environ.setdefault("ADMIN_PASSWORD", "tester")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-secret")

from src.services.gsc_priority_engine import EngineFlags, GSCPriorityEngine, SteeringConfig


def make_engine(steering=None, now=None):
    def resolve_context(query, page):
        query_lower = query.lower()
        if "custom" in query_lower or "supplier" in query_lower or "quote" in query_lower:
            return {
                "page_type": "category",
                "primary_taxonomy_type": "category",
                "primary_taxonomy_url": "https://example.com/custom-bottles",
                "target_category_url": "https://example.com/custom-bottles",
                "supporting_products": [{"name": "500ml Bottle"}],
            }
        if "glass" in query_lower:
            return {"page_type": "article"}
        return {}

    def publishability(query, context):
        if "science" in query.lower():
            return {"publishable": False, "score": 0.2, "reason": "support_only"}
        return {"publishable": True, "score": 0.8, "reason": None}

    return GSCPriorityEngine(
        site_url="sc-domain:example.com",
        steering=steering or SteeringConfig(),
        flags=EngineFlags(
            shadow_enabled=True,
            authoritative_enabled=False,
            kill_switch_enabled=False,
            action_ctr_authoritative_enabled=False,
            action_refresh_authoritative_enabled=False,
            action_internal_link_authoritative_enabled=False,
            action_new_content_authoritative_enabled=False,
            action_backlink_authoritative_enabled=False,
        ),
        context_resolver=resolve_context,
        publishability_checker=publishability,
        now=now or datetime(2026, 4, 25, 4, 0, 0),
    )


def test_cluster_assembly_attaches_support_queries_and_keeps_identity_stable():
    engine = make_engine()
    rows = [
        {"query": "custom bottle supplier", "page": "https://example.com/custom-bottles", "impressions": 420, "clicks": 35, "ctr": 0.03, "position": 7.0},
        {"query": "custom bottle quote", "page": "https://example.com/custom-bottles", "impressions": 380, "clicks": 30, "ctr": 0.028, "position": 8.2},
        {"query": "how to choose custom bottle size", "page": "https://example.com/custom-bottles", "impressions": 250, "clicks": 18, "ctr": 0.025, "position": 9.1},
        {"query": "science of glass bottles", "page": "https://example.com/glass-bottle-science", "impressions": 2200, "clicks": 120, "ctr": 0.055, "position": 3.2},
    ]

    clusters = engine.assemble_clusters(rows)
    assert len(clusters) == 2

    primary_cluster = max(clusters, key=lambda cluster: len(cluster.members))
    assert len(primary_cluster.members) == 3
    assert any(member.support_role == "support" for member in primary_cluster.members)

    reversed_clusters = engine.assemble_clusters(list(reversed(rows)))
    assert sorted(cluster.cluster_id for cluster in clusters) == sorted(cluster.cluster_id for cluster in reversed_clusters)


def test_commercial_cluster_outranks_generic_information_and_steering_is_capped():
    steering = SteeringConfig(
        reference_keywords=[
            "custom bottle supplier",
            "custom bottle quote",
            "custom bottle wholesale",
            "custom bottle manufacturer",
            "custom bottle bulk order",
        ]
    )
    engine = make_engine(steering=steering)
    rows = [
        {"query": "custom bottle supplier", "page": "https://example.com/custom-bottles", "impressions": 480, "clicks": 42, "ctr": 0.02, "position": 7.5},
        {"query": "custom bottle quote", "page": "https://example.com/custom-bottles", "impressions": 310, "clicks": 25, "ctr": 0.018, "position": 8.4},
        {"query": "science of glass bottles", "page": "https://example.com/glass-bottle-science", "impressions": 6400, "clicks": 150, "ctr": 0.06, "position": 3.0},
    ]

    shadow_run = engine.build_shadow_run(rows, used_keywords=set())
    top_decision = shadow_run["top_decision"]

    assert top_decision["canonical_topic"] == "custom bottle supplier"
    assert abs(top_decision["score_breakdown"]["admin_steering_modifier"]) <= 0.12
    assert shadow_run["metrics"]["trace_completeness"] == 1.0


def test_negative_keyword_blocks_primary_targeting_and_recommendation():
    steering = SteeringConfig(negative_keywords=["science of glass bottles"])
    engine = make_engine(steering=steering)
    rows = [
        {"query": "science of glass bottles", "page": "https://example.com/glass-bottle-science", "impressions": 3000, "clicks": 160, "ctr": 0.05, "position": 4.0},
    ]

    shadow_run = engine.build_shadow_run(rows, used_keywords=set())
    top_decision = shadow_run["top_decision"]

    assert top_decision["fallback_reason"] == "negative_keyword_conflict"
    assert top_decision["confidence"] < 0.60


def test_demand_monotonicity_and_decision_window_idempotency():
    engine = make_engine(now=datetime(2026, 4, 25, 6, 0, 0))
    low_cluster = engine.assemble_clusters([
        {"query": "custom bottle supplier", "page": "https://example.com/custom-bottles", "impressions": 200, "clicks": 18, "ctr": 0.02, "position": 7.0},
    ])[0]
    high_cluster = engine.assemble_clusters([
        {"query": "custom bottle supplier", "page": "https://example.com/custom-bottles", "impressions": 900, "clicks": 80, "ctr": 0.02, "position": 7.0},
    ])[0]

    low_decision = engine._build_cluster_decision(low_cluster, used_keywords=set(), max_impressions=900, max_clicks=80)
    high_decision = engine._build_cluster_decision(high_cluster, used_keywords=set(), max_impressions=900, max_clicks=80)

    assert high_decision.score_breakdown["demand"] >= low_decision.score_breakdown["demand"]
    assert high_decision.final_score >= low_decision.final_score
    assert low_decision.decision_window_key.startswith(f"{low_cluster.cluster_id}:")
    assert high_decision.decision_window_key.startswith(f"{high_cluster.cluster_id}:")
    assert low_decision.decision_window_key.endswith(":20260425")
    assert high_decision.decision_window_key.endswith(":20260425")


def test_shadow_gate_evaluation_requires_all_numeric_thresholds():
    engine = make_engine()

    passing = engine.evaluate_shadow_success_gates({
        "business_value_precision_improvement": 0.25,
        "execution_failure_rate_delta": 0.01,
        "duplicate_incident_delta": 0.03,
        "decision_trace_completeness": 0.995,
        "steering_cap_violations": 0.0,
    })
    assert passing.passed is True
    assert passing.shadow_extension_days == 0

    failing = engine.evaluate_shadow_success_gates({
        "business_value_precision_improvement": 0.15,
        "execution_failure_rate_delta": 0.03,
        "duplicate_incident_delta": 0.06,
        "decision_trace_completeness": 0.90,
        "steering_cap_violations": 1.0,
    })
    assert failing.passed is False
    assert failing.shadow_extension_days == 7
