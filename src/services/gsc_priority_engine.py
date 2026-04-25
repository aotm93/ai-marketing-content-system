"""Cluster-priority sidecar for demand-first GSC decisioning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha1
import json
import math
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from src.config import settings
from src.config.utils import normalize_multiline_entries


EXPECTED_CTR = {
    1: 0.32,
    2: 0.17,
    3: 0.11,
    4: 0.08,
    5: 0.07,
    6: 0.05,
    7: 0.04,
    8: 0.03,
    9: 0.025,
    10: 0.02,
}

COMMERCIAL_TERMS = {
    "buy",
    "supplier",
    "suppliers",
    "manufacturer",
    "manufacturers",
    "factory",
    "quote",
    "quotes",
    "pricing",
    "price",
    "cost",
    "wholesale",
    "bulk",
    "custom",
    "customized",
    "order",
    "vendor",
    "vendors",
    "solution",
    "solutions",
    "exporter",
    "exporters",
    "oem",
    "moq",
}

SUPPORT_TERMS = {
    "what",
    "why",
    "how",
    "guide",
    "guides",
    "tutorial",
    "tutorials",
    "science",
    "explained",
    "meaning",
    "definition",
    "learn",
    "knowledge",
    "tips",
    "faq",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "best",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "vs",
    "with",
}

DEFAULT_CLUSTER_VERSION = "v1"


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def safe_json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def tokenize(text: str) -> List[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if token not in STOPWORDS and len(token) > 1
    ]


def text_similarity(left: Sequence[str], right: Sequence[str]) -> float:
    if not left or not right:
        return 0.0

    left_set = set(left)
    right_set = set(right)
    overlap = len(left_set & right_set)
    return overlap / max(len(left_set), len(right_set), 1)


def normalize_page(page: str) -> str:
    if not page:
        return ""

    parsed = urlparse(page)
    path = (parsed.path or "").rstrip("/")
    return f"{parsed.netloc.lower()}{path.lower()}"


def expected_ctr_for_position(position: float) -> float:
    normalized_position = max(1, min(10, int(round(position or 10))))
    return EXPECTED_CTR.get(normalized_position, 0.02)


@dataclass
class SteeringConfig:
    reference_keywords: List[str] = field(default_factory=list)
    negative_keywords: List[str] = field(default_factory=list)
    commercial_priority_terms: List[str] = field(default_factory=list)
    priority_target_pages: List[str] = field(default_factory=list)

    @classmethod
    def from_settings(cls) -> "SteeringConfig":
        return cls(
            reference_keywords=normalize_multiline_entries(settings.reference_keywords, max_entries=200),
            negative_keywords=normalize_multiline_entries(settings.negative_keywords, max_entries=200),
            commercial_priority_terms=normalize_multiline_entries(settings.commercial_priority_terms, max_entries=100),
            priority_target_pages=normalize_multiline_entries(settings.priority_target_pages, max_entries=100),
        )


@dataclass
class EngineFlags:
    shadow_enabled: bool
    authoritative_enabled: bool
    kill_switch_enabled: bool
    action_ctr_authoritative_enabled: bool
    action_refresh_authoritative_enabled: bool
    action_internal_link_authoritative_enabled: bool
    action_new_content_authoritative_enabled: bool
    action_backlink_authoritative_enabled: bool

    @classmethod
    def from_settings(cls) -> "EngineFlags":
        return cls(
            shadow_enabled=settings.cluster_engine_shadow_enabled,
            authoritative_enabled=settings.cluster_engine_authoritative_enabled,
            kill_switch_enabled=settings.cluster_engine_kill_switch_enabled,
            action_ctr_authoritative_enabled=settings.action_ctr_authoritative_enabled,
            action_refresh_authoritative_enabled=settings.action_refresh_authoritative_enabled,
            action_internal_link_authoritative_enabled=settings.action_internal_link_authoritative_enabled,
            action_new_content_authoritative_enabled=settings.action_new_content_authoritative_enabled,
            action_backlink_authoritative_enabled=settings.action_backlink_authoritative_enabled,
        )

    def action_authority_enabled(self, action_family: str) -> bool:
        if self.kill_switch_enabled or not self.authoritative_enabled:
            return False

        mapping = {
            "ctr_optimize": self.action_ctr_authoritative_enabled,
            "page_refresh": self.action_refresh_authoritative_enabled,
            "internal_link_push": self.action_internal_link_authoritative_enabled,
            "supporting_content_create": self.action_new_content_authoritative_enabled,
            "backlink_support": self.action_backlink_authoritative_enabled,
        }
        return bool(mapping.get(action_family, False))


@dataclass
class ClusterMember:
    query: str
    page: str
    clicks: int
    impressions: int
    ctr: float
    position: float
    intent_band: str
    support_role: str
    catalog_context: Dict[str, Any]
    publishability: Dict[str, Any]

    @property
    def query_tokens(self) -> List[str]:
        return tokenize(self.query)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "page": self.page,
            "clicks": self.clicks,
            "impressions": self.impressions,
            "ctr": round(self.ctr, 4),
            "position": round(self.position, 3),
            "intent_band": self.intent_band,
            "support_role": self.support_role,
            "catalog_context": self.catalog_context,
            "publishability": self.publishability,
        }


@dataclass
class DemandCluster:
    cluster_id: str
    cluster_version: str
    canonical_topic: str
    primary_target_page: str
    intent_band: str
    members: List[ClusterMember]
    primary_member: ClusterMember

    @property
    def cluster_name(self) -> str:
        return self.canonical_topic

    @property
    def avg_ctr(self) -> float:
        return sum(member.ctr for member in self.members) / max(len(self.members), 1)

    @property
    def avg_position(self) -> float:
        return sum(member.position for member in self.members) / max(len(self.members), 1)

    @property
    def total_clicks(self) -> int:
        return sum(member.clicks for member in self.members)

    @property
    def total_impressions(self) -> int:
        return sum(member.impressions for member in self.members)

    @property
    def unique_pages(self) -> List[str]:
        seen = []
        for member in self.members:
            page = member.page
            if page and page not in seen:
                seen.append(page)
        return seen

    def to_member_summary(self) -> List[Dict[str, Any]]:
        return [member.to_dict() for member in self.members]


@dataclass
class ClusterDecision:
    cluster: DemandCluster
    final_score: float
    score_breakdown: Dict[str, float]
    steering_matches: Dict[str, Any]
    selected_action_family: str
    selected_action_score: float
    action_scores: Dict[str, float]
    confidence: float
    fallback_reason: Optional[str]
    decision_window_key: str
    authoritative_eligible: bool
    authoritative_enabled: bool

    @property
    def trace_complete(self) -> bool:
        required = [
            self.cluster.cluster_id,
            self.cluster.cluster_version,
            self.cluster.members,
            self.score_breakdown,
            self.selected_action_family,
        ]
        return all(required)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster.cluster_id,
            "cluster_version": self.cluster.cluster_version,
            "cluster_name": self.cluster.cluster_name,
            "canonical_topic": self.cluster.canonical_topic,
            "primary_target_page": self.cluster.primary_target_page,
            "intent_band": self.cluster.intent_band,
            "member_count": len(self.cluster.members),
            "members": self.cluster.to_member_summary(),
            "score": round(self.final_score, 4),
            "score_breakdown": {key: round(value, 4) for key, value in self.score_breakdown.items()},
            "selected_action_family": self.selected_action_family,
            "selected_action_score": round(self.selected_action_score, 4),
            "action_scores": {key: round(value, 4) for key, value in self.action_scores.items()},
            "confidence": round(self.confidence, 4),
            "fallback_reason": self.fallback_reason,
            "decision_window_key": self.decision_window_key,
            "steering_matches": self.steering_matches,
            "authoritative_eligible": self.authoritative_eligible,
            "authoritative_enabled": self.authoritative_enabled,
            "trace_complete": self.trace_complete,
        }


@dataclass
class ShadowGateEvaluation:
    passed: bool
    shadow_extension_days: int
    criteria: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "shadow_extension_days": self.shadow_extension_days,
            "criteria": self.criteria,
        }


class GSCPriorityEngine:
    """Build cluster-level priority decisions without replacing the baseline path."""

    def __init__(
        self,
        site_url: Optional[str],
        steering: Optional[SteeringConfig] = None,
        flags: Optional[EngineFlags] = None,
        cluster_version: str = DEFAULT_CLUSTER_VERSION,
        max_members_per_cluster: int = 25,
        now: Optional[datetime] = None,
        context_resolver: Optional[Callable[[str, str], Dict[str, Any]]] = None,
        publishability_checker: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
    ):
        self.site_url = site_url or "unknown-site"
        self.steering = steering or SteeringConfig.from_settings()
        self.flags = flags or EngineFlags.from_settings()
        self.cluster_version = cluster_version
        self.max_members_per_cluster = max_members_per_cluster
        self.now = now or datetime.utcnow()
        self.context_resolver = context_resolver or (lambda query, page: {})
        self.publishability_checker = publishability_checker or (
            lambda query, context: {"publishable": True, "score": 0.5, "reason": None}
        )

    def build_shadow_run(
        self,
        gsc_rows: Iterable[Any],
        used_keywords: Optional[set[str]] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        clusters = self.assemble_clusters(gsc_rows)
        if not clusters:
            return {
                "decisions": [],
                "top_decision": None,
                "best_supporting_content_candidate": None,
                "metrics": {
                    "cluster_count": 0,
                    "fallback_rate": 1.0,
                    "trace_completeness": 1.0,
                    "median_confidence": 0.0,
                },
            }

        decisions = self.rank_clusters(clusters, used_keywords=used_keywords or set(), limit=limit)
        content_candidate = next(
            (decision for decision in decisions if decision.selected_action_family == "supporting_content_create"),
            None,
        )
        confidences = sorted(decision.confidence for decision in decisions)
        median_confidence = confidences[len(confidences) // 2] if confidences else 0.0
        fallback_count = sum(1 for decision in decisions if decision.fallback_reason)
        trace_complete_count = sum(1 for decision in decisions if decision.trace_complete)

        return {
            "decisions": [decision.to_dict() for decision in decisions],
            "top_decision": decisions[0].to_dict() if decisions else None,
            "best_supporting_content_candidate": content_candidate.to_dict() if content_candidate else None,
            "metrics": {
                "cluster_count": len(clusters),
                "fallback_rate": round(fallback_count / max(len(decisions), 1), 4),
                "trace_completeness": round(trace_complete_count / max(len(decisions), 1), 4),
                "median_confidence": round(median_confidence, 4),
            },
        }

    def assemble_clusters(self, gsc_rows: Iterable[Any]) -> List[DemandCluster]:
        members = []
        for row in gsc_rows:
            normalized = self._normalize_gsc_row(row)
            if not normalized["query"] or not normalized["page"]:
                continue

            catalog_context = dict(self.context_resolver(normalized["query"], normalized["page"]) or {})
            publishability = dict(self.publishability_checker(normalized["query"], catalog_context) or {})
            intent_band = self._classify_intent_band(normalized["query"], catalog_context)
            support_role = self._classify_support_role(normalized["query"], intent_band)
            members.append(
                ClusterMember(
                    query=normalized["query"],
                    page=normalized["page"],
                    clicks=normalized["clicks"],
                    impressions=normalized["impressions"],
                    ctr=normalized["ctr"],
                    position=normalized["position"],
                    intent_band=intent_band,
                    support_role=support_role,
                    catalog_context=catalog_context,
                    publishability=publishability,
                )
            )

        sorted_members = sorted(
            members,
            key=lambda member: (member.impressions, member.clicks, -member.position),
            reverse=True,
        )

        clusters: List[DemandCluster] = []
        for member in sorted_members:
            matched_cluster = self._find_cluster_match(clusters, member)
            if matched_cluster and len(matched_cluster.members) < self.max_members_per_cluster:
                matched_cluster.members.append(member)
                matched_cluster.primary_member = self._choose_primary_member(matched_cluster.members)
                matched_cluster.canonical_topic = matched_cluster.primary_member.query
                if not matched_cluster.primary_target_page:
                    matched_cluster.primary_target_page = matched_cluster.primary_member.page
                if matched_cluster.intent_band == "support-only" and member.intent_band != "support-only":
                    matched_cluster.intent_band = member.intent_band
                continue

            cluster_id = self._make_cluster_id(
                canonical_topic=member.query,
                primary_target_page=member.page,
                intent_band=member.intent_band,
            )
            clusters.append(
                DemandCluster(
                    cluster_id=cluster_id,
                    cluster_version=self.cluster_version,
                    canonical_topic=member.query,
                    primary_target_page=member.page,
                    intent_band=member.intent_band,
                    members=[member],
                    primary_member=member,
                )
            )

        return clusters

    def rank_clusters(
        self,
        clusters: Sequence[DemandCluster],
        used_keywords: set[str],
        limit: int = 20,
    ) -> List[ClusterDecision]:
        max_impressions = max((cluster.total_impressions for cluster in clusters), default=1)
        max_clicks = max((cluster.total_clicks for cluster in clusters), default=1)

        decisions = [
            self._build_cluster_decision(
                cluster,
                used_keywords=used_keywords,
                max_impressions=max_impressions,
                max_clicks=max_clicks,
            )
            for cluster in clusters
        ]

        decisions.sort(
            key=lambda decision: (
                decision.final_score,
                decision.score_breakdown.get("conversion_proximity", 0.0),
                decision.score_breakdown.get("demand", 0.0),
                -decision.score_breakdown.get("cannibalization_penalty", 0.0),
                -self._action_operational_risk(decision.selected_action_family),
            ),
            reverse=True,
        )
        return decisions[:limit]

    def persist_shadow_decisions(self, db: Session, decisions: Sequence[Dict[str, Any] | ClusterDecision]) -> None:
        from src.models.gsc_data import Opportunity, TopicCluster

        for rank, raw_decision in enumerate(decisions, start=1):
            decision = raw_decision if isinstance(raw_decision, ClusterDecision) else self._decision_from_dict(raw_decision)
            opportunity_id = f"cluster_{decision.cluster.cluster_id}"[:36]
            decision_dict = decision.to_dict()
            existing_opp = db.query(Opportunity).filter(Opportunity.opportunity_id == opportunity_id).first()

            if not existing_opp:
                existing_opp = Opportunity(
                    opportunity_id=opportunity_id,
                    opportunity_type="cluster_priority",
                    status="pending",
                )
                db.add(existing_opp)

            existing_opp.target_query = decision.cluster.primary_member.query
            existing_opp.target_page = decision.cluster.primary_target_page
            existing_opp.cluster_id = decision.cluster.cluster_id
            existing_opp.cluster_name = decision.cluster.cluster_name
            existing_opp.cluster_version = decision.cluster.cluster_version
            existing_opp.decision_unit_type = "cluster"
            existing_opp.score = round(decision.final_score * 100, 2)
            existing_opp.confidence = round(decision.confidence, 4)
            existing_opp.current_position = round(decision.cluster.avg_position, 3)
            existing_opp.current_impressions = decision.cluster.total_impressions
            existing_opp.current_ctr = round(decision.cluster.avg_ctr, 4)
            existing_opp.current_clicks = decision.cluster.total_clicks
            existing_opp.potential_clicks = max(
                0,
                int(decision.cluster.total_impressions * max(decision.score_breakdown.get("ctr_gap", 0.0), 0.05)),
            )
            existing_opp.recommended_action_family = decision.selected_action_family
            existing_opp.recommended_action_confidence = round(decision.confidence, 4)
            existing_opp.action_type = decision.selected_action_family
            existing_opp.action_details = safe_json_dumps({"action_scores": decision.action_scores})
            existing_opp.score_breakdown_json = safe_json_dumps(decision.score_breakdown)
            existing_opp.steering_matches_json = safe_json_dumps(decision.steering_matches)
            existing_opp.decision_trace_json = safe_json_dumps(decision_dict)
            existing_opp.support_role = self._cluster_support_role(decision.cluster)
            existing_opp.target_asset_type = self._target_asset_type(decision.cluster.primary_member.catalog_context)
            existing_opp.engine_mode = "shadow"
            existing_opp.engine_version = decision.cluster.cluster_version
            existing_opp.fallback_reason = decision.fallback_reason
            existing_opp.decision_window_key = decision.decision_window_key
            existing_opp.priority = self._score_to_priority(decision.final_score)
            existing_opp.shadow_rank = rank

            existing_cluster = db.query(TopicCluster).filter(TopicCluster.cluster_id == decision.cluster.cluster_id).first()
            if not existing_cluster:
                existing_cluster = TopicCluster(
                    cluster_id=decision.cluster.cluster_id,
                    cluster_name=decision.cluster.cluster_name,
                )
                db.add(existing_cluster)

            existing_cluster.cluster_name = decision.cluster.cluster_name
            existing_cluster.cluster_version = decision.cluster.cluster_version
            existing_cluster.canonical_topic = decision.cluster.canonical_topic
            existing_cluster.hub_page_url = decision.cluster.primary_target_page
            existing_cluster.hub_keyword = decision.cluster.primary_member.query
            existing_cluster.intent = decision.cluster.intent_band
            existing_cluster.intent_band = decision.cluster.intent_band
            existing_cluster.topic_keywords = safe_json_dumps(
                [member.query for member in decision.cluster.members[: self.max_members_per_cluster]]
            )
            existing_cluster.member_count = len(decision.cluster.members)
            existing_cluster.cluster_impressions = decision.cluster.total_impressions
            existing_cluster.cluster_clicks = decision.cluster.total_clicks
            existing_cluster.cluster_avg_position = round(decision.cluster.avg_position, 3)
            existing_cluster.business_intent_score = round(decision.score_breakdown.get("commercial_intent", 0.0), 4)
            existing_cluster.conversion_proximity_score = round(
                decision.score_breakdown.get("conversion_proximity", 0.0), 4
            )
            existing_cluster.support_coverage_score = round(
                1.0 - decision.score_breakdown.get("internal_link_gap", 0.0),
                4,
            )
            existing_cluster.demand_freshness_hours = 0.0
            existing_cluster.last_gsc_sync_at = self.now
            existing_cluster.cluster_members_json = safe_json_dumps(decision.cluster.to_member_summary())
            existing_cluster.last_analyzed = self.now
            existing_cluster.is_active = 1

        db.commit()

    def evaluate_shadow_success_gates(self, metrics: Dict[str, float]) -> ShadowGateEvaluation:
        criteria = {
            "business_value_precision_improvement": {
                "passed": metrics.get("business_value_precision_improvement", 0.0) >= 0.20,
                "expected": ">= 0.20",
                "actual": metrics.get("business_value_precision_improvement", 0.0),
            },
            "execution_failure_rate_delta": {
                "passed": metrics.get("execution_failure_rate_delta", 0.0) <= 0.02,
                "expected": "<= 0.02",
                "actual": metrics.get("execution_failure_rate_delta", 0.0),
            },
            "duplicate_incident_delta": {
                "passed": metrics.get("duplicate_incident_delta", 0.0) <= 0.05,
                "expected": "<= 0.05",
                "actual": metrics.get("duplicate_incident_delta", 0.0),
            },
            "decision_trace_completeness": {
                "passed": metrics.get("decision_trace_completeness", 0.0) >= 0.99,
                "expected": ">= 0.99",
                "actual": metrics.get("decision_trace_completeness", 0.0),
            },
            "steering_cap_violations": {
                "passed": metrics.get("steering_cap_violations", 0.0) == 0.0,
                "expected": "== 0",
                "actual": metrics.get("steering_cap_violations", 0.0),
            },
        }
        passed = all(item["passed"] for item in criteria.values())
        return ShadowGateEvaluation(
            passed=passed,
            shadow_extension_days=0 if passed else 7,
            criteria=criteria,
        )

    def _normalize_gsc_row(self, row: Any) -> Dict[str, Any]:
        if hasattr(row, "to_dict"):
            row_dict = row.to_dict()
            ctr = row_dict.get("ctr", 0.0)
            if ctr > 1:
                ctr = ctr / 100.0
            return {
                "query": row_dict.get("query", ""),
                "page": row_dict.get("page", ""),
                "clicks": int(row_dict.get("clicks", 0) or 0),
                "impressions": int(row_dict.get("impressions", 0) or 0),
                "ctr": float(ctr or 0.0),
                "position": float(row_dict.get("position", 0.0) or 0.0),
            }

        if isinstance(row, dict):
            ctr = row.get("ctr", 0.0)
            if ctr > 1:
                ctr = ctr / 100.0
            return {
                "query": row.get("query", ""),
                "page": row.get("page", ""),
                "clicks": int(row.get("clicks", 0) or 0),
                "impressions": int(row.get("impressions", 0) or 0),
                "ctr": float(ctr or 0.0),
                "position": float(row.get("position", 0.0) or 0.0),
            }

        ctr = getattr(row, "ctr", 0.0)
        if ctr > 1:
            ctr = ctr / 100.0
        return {
            "query": getattr(row, "query", ""),
            "page": getattr(row, "page", ""),
            "clicks": int(getattr(row, "clicks", 0) or 0),
            "impressions": int(getattr(row, "impressions", 0) or 0),
            "ctr": float(ctr or 0.0),
            "position": float(getattr(row, "position", 0.0) or 0.0),
        }

    def _classify_intent_band(self, query: str, context: Dict[str, Any]) -> str:
        tokens = set(tokenize(query))
        commercial_hits = len(tokens & COMMERCIAL_TERMS)
        support_hits = len(tokens & SUPPORT_TERMS)
        has_conversion_page = bool(
            context.get("primary_taxonomy_url")
            or context.get("target_category_url")
            or context.get("target_tag_url")
            or context.get("supporting_products")
        )

        if commercial_hits or has_conversion_page:
            return "mixed-commercial-support" if support_hits else "commercial"
        if support_hits:
            return "support-only"
        return "mixed-commercial-support"

    def _classify_support_role(self, query: str, intent_band: str) -> str:
        if intent_band == "support-only":
            return "support"
        if set(tokenize(query)) & SUPPORT_TERMS:
            return "support"
        return "primary"

    def _find_cluster_match(
        self,
        clusters: Sequence[DemandCluster],
        member: ClusterMember,
    ) -> Optional[DemandCluster]:
        best_match = None
        best_score = 0.0
        member_tokens = member.query_tokens
        member_page = normalize_page(member.page)

        for cluster in clusters:
            if cluster.intent_band != member.intent_band and not (
                member.support_role == "support" and cluster.intent_band != "support-only"
            ):
                continue

            cluster_page = normalize_page(cluster.primary_target_page)
            topic_similarity = text_similarity(member_tokens, tokenize(cluster.canonical_topic))
            page_match_bonus = 0.35 if member_page and cluster_page and member_page == cluster_page else 0.0
            score = topic_similarity + page_match_bonus

            if member.support_role == "support" and member_page and cluster_page and member_page == cluster_page:
                score = max(score, 0.8)

            if score > best_score and score >= 0.72:
                best_score = score
                best_match = cluster

        return best_match

    def _choose_primary_member(self, members: Sequence[ClusterMember]) -> ClusterMember:
        return max(
            members,
            key=lambda member: (
                member.support_role == "primary",
                member.impressions,
                member.clicks,
                -member.position,
            ),
        )

    def _make_cluster_id(self, canonical_topic: str, primary_target_page: str, intent_band: str) -> str:
        raw = "|".join(
            [
                self.site_url,
                canonical_topic.strip().lower(),
                primary_target_page.strip().lower(),
                intent_band,
                self.cluster_version,
            ]
        )
        return sha1(raw.encode("utf-8")).hexdigest()[:24]

    def _build_cluster_decision(
        self,
        cluster: DemandCluster,
        used_keywords: set[str],
        max_impressions: int,
        max_clicks: int,
    ) -> ClusterDecision:
        steering = self._evaluate_steering(cluster)
        commercial_intent = clamp(self._commercial_intent(cluster) + steering["commercial_intent_boost"])
        demand = self._demand_score(cluster, max_impressions=max_impressions, max_clicks=max_clicks)
        conversion_proximity = self._conversion_proximity(cluster)
        ctr_gap = self._ctr_gap(cluster)
        content_gap = self._content_gap(cluster)
        internal_link_gap = self._internal_link_gap(cluster)
        cannibalization_penalty = self._cannibalization_penalty(cluster)
        backlink_need = self._backlink_need(cluster, demand=demand, commercial_intent=commercial_intent)

        score_breakdown = {
            "demand": demand,
            "commercial_intent": commercial_intent,
            "conversion_proximity": conversion_proximity,
            "ctr_gap": ctr_gap,
            "content_gap": content_gap,
            "internal_link_gap": internal_link_gap,
            "cannibalization_penalty": cannibalization_penalty,
            "backlink_need": backlink_need,
            "admin_steering_modifier": steering["capped_modifier"],
        }

        base_score = (
            demand * 0.24
            + commercial_intent * 0.18
            + conversion_proximity * 0.18
            + ctr_gap * 0.12
            + content_gap * 0.11
            + internal_link_gap * 0.08
            + backlink_need * 0.05
            - cannibalization_penalty * 0.10
        )

        final_score = clamp(base_score + steering["capped_modifier"])
        if cluster.intent_band == "support-only" and conversion_proximity < 0.60:
            final_score = round(final_score * 0.55, 4)

        action_scores = self._action_scores(
            cluster=cluster,
            final_score=final_score,
            demand=demand,
            commercial_intent=commercial_intent,
            conversion_proximity=conversion_proximity,
            ctr_gap=ctr_gap,
            content_gap=content_gap,
            internal_link_gap=internal_link_gap,
            backlink_need=backlink_need,
            cannibalization_penalty=cannibalization_penalty,
        )
        selected_action_family, selected_action_score, fallback_reason = self._select_action(
            cluster=cluster,
            action_scores=action_scores,
            steering=steering,
            used_keywords=used_keywords,
            conversion_proximity=conversion_proximity,
        )

        confidence = clamp(
            final_score * 0.45 + selected_action_score * 0.40 + (1.0 - cannibalization_penalty) * 0.15
        )
        if fallback_reason:
            confidence = min(confidence, 0.59)

        decision_window_key = f"{cluster.cluster_id}:{selected_action_family}:{self.now.strftime('%Y%m%d')}"
        authoritative_eligible = confidence >= 0.75 and not fallback_reason
        authoritative_enabled = authoritative_eligible and self.flags.action_authority_enabled(selected_action_family)

        return ClusterDecision(
            cluster=cluster,
            final_score=final_score,
            score_breakdown=score_breakdown,
            steering_matches=steering,
            selected_action_family=selected_action_family,
            selected_action_score=selected_action_score,
            action_scores=action_scores,
            confidence=confidence,
            fallback_reason=fallback_reason,
            decision_window_key=decision_window_key,
            authoritative_eligible=authoritative_eligible,
            authoritative_enabled=authoritative_enabled,
        )

    def _evaluate_steering(self, cluster: DemandCluster) -> Dict[str, Any]:
        matches = {
            "reference_keywords": [],
            "negative_keywords": [],
            "commercial_priority_terms": [],
            "priority_target_pages": [],
        }
        canonical_query = cluster.canonical_topic.lower()
        all_queries = [member.query.lower() for member in cluster.members]
        target_page = cluster.primary_target_page.lower()

        raw_modifier = 0.0
        commercial_intent_boost = 0.0
        hard_negative_match = False

        for keyword in self.steering.reference_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in canonical_query or any(keyword_lower in query for query in all_queries):
                matches["reference_keywords"].append(keyword)
                raw_modifier += 0.04
                continue

            keyword_tokens = tokenize(keyword_lower)
            if text_similarity(keyword_tokens, tokenize(canonical_query)) >= 0.6:
                matches["reference_keywords"].append(keyword)
                raw_modifier += 0.025

        for keyword in self.steering.negative_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower == canonical_query:
                matches["negative_keywords"].append(keyword)
                raw_modifier -= 0.20
                hard_negative_match = True
            elif keyword_lower in canonical_query or any(keyword_lower in query for query in all_queries):
                matches["negative_keywords"].append(keyword)
                raw_modifier -= 0.08

        for keyword in self.steering.commercial_priority_terms:
            keyword_lower = keyword.lower()
            if keyword_lower in canonical_query or any(keyword_lower in query for query in all_queries):
                matches["commercial_priority_terms"].append(keyword)
                commercial_intent_boost += 0.06

        for target in self.steering.priority_target_pages:
            target_lower = target.lower()
            if target_lower and target_lower in target_page:
                matches["priority_target_pages"].append(target)
                raw_modifier += 0.05

        capped_modifier = clamp(raw_modifier, -0.12, 0.12)

        return {
            **matches,
            "raw_modifier": round(raw_modifier, 4),
            "capped_modifier": round(capped_modifier, 4),
            "commercial_intent_boost": round(clamp(commercial_intent_boost, 0.0, 0.12), 4),
            "hard_negative_match": hard_negative_match,
            "cap_applied": round(raw_modifier, 4) != round(capped_modifier, 4),
        }

    def _demand_score(self, cluster: DemandCluster, max_impressions: int, max_clicks: int) -> float:
        impressions_score = math.log10(cluster.total_impressions + 1) / max(math.log10(max_impressions + 1), 1.0)
        clicks_score = math.log10(cluster.total_clicks + 1) / max(math.log10(max_clicks + 1), 1.0)
        return clamp(impressions_score * 0.65 + clicks_score * 0.35)

    def _commercial_intent(self, cluster: DemandCluster) -> float:
        base = {
            "commercial": 0.88,
            "mixed-commercial-support": 0.72,
            "support-only": 0.28,
        }.get(cluster.intent_band, 0.55)

        if cluster.primary_member.catalog_context.get("supporting_products"):
            base += 0.06
        if cluster.primary_member.catalog_context.get("primary_taxonomy_url"):
            base += 0.06
        return clamp(base)

    def _conversion_proximity(self, cluster: DemandCluster) -> float:
        context = cluster.primary_member.catalog_context
        page_type = (context.get("page_type") or "").lower()
        taxonomy_type = (context.get("primary_taxonomy_type") or "").lower()

        score = 0.35 if cluster.primary_target_page else 0.15
        if page_type == "product":
            score += 0.55
        elif page_type == "category":
            score += 0.42
        elif page_type == "tag":
            score += 0.30

        if taxonomy_type == "category":
            score += 0.18
        elif taxonomy_type == "tag":
            score += 0.12

        if context.get("supporting_products"):
            score += 0.12

        return clamp(score)

    def _ctr_gap(self, cluster: DemandCluster) -> float:
        expected_ctr = expected_ctr_for_position(cluster.avg_position)
        if expected_ctr <= 0:
            return 0.0
        return clamp((expected_ctr - cluster.avg_ctr) / expected_ctr)

    def _content_gap(self, cluster: DemandCluster) -> float:
        score = 0.10
        if cluster.avg_position > 15:
            score += 0.40
        elif cluster.avg_position > 10:
            score += 0.28
        elif cluster.avg_position > 6:
            score += 0.15

        if not cluster.primary_target_page:
            score += 0.22
        if cluster.intent_band == "support-only":
            score += 0.10

        publishability_score = cluster.primary_member.publishability.get("score", 0.5)
        score += clamp(0.7 - publishability_score, 0.0, 0.2)
        return clamp(score)

    def _support_coverage(self, cluster: DemandCluster) -> float:
        context = cluster.primary_member.catalog_context
        score = 0.0
        if cluster.primary_target_page:
            score += 0.36
        if context.get("primary_taxonomy_url"):
            score += 0.18
        score += min(len(context.get("supporting_products") or []), 3) * 0.10
        score += min(len(context.get("supporting_tags") or []), 3) * 0.06
        score += min(len(cluster.unique_pages), 3) * 0.06
        return clamp(score)

    def _internal_link_gap(self, cluster: DemandCluster) -> float:
        return clamp(1.0 - self._support_coverage(cluster))

    def _cannibalization_penalty(self, cluster: DemandCluster) -> float:
        extra_pages = max(len(cluster.unique_pages) - 1, 0)
        return clamp(extra_pages / 3.0)

    def _backlink_need(self, cluster: DemandCluster, demand: float, commercial_intent: float) -> float:
        position_signal = clamp(cluster.avg_position / 20.0)
        return clamp(position_signal * 0.45 + demand * 0.35 + commercial_intent * 0.20)

    def _action_scores(
        self,
        cluster: DemandCluster,
        final_score: float,
        demand: float,
        commercial_intent: float,
        conversion_proximity: float,
        ctr_gap: float,
        content_gap: float,
        internal_link_gap: float,
        backlink_need: float,
        cannibalization_penalty: float,
    ) -> Dict[str, float]:
        support_need = clamp(1.0 - self._support_coverage(cluster) + (0.10 if cluster.intent_band != "support-only" else 0.0))
        has_primary_page = 1.0 if cluster.primary_target_page else 0.0

        return {
            "ctr_optimize": clamp(
                final_score * 0.20
                + has_primary_page * 0.20
                + ctr_gap * 0.40
                + conversion_proximity * 0.15
                - cannibalization_penalty * 0.10
            ),
            "page_refresh": clamp(
                final_score * 0.22
                + has_primary_page * 0.18
                + content_gap * 0.36
                + demand * 0.14
                - cannibalization_penalty * 0.10
            ),
            "internal_link_push": clamp(
                final_score * 0.20
                + conversion_proximity * 0.20
                + internal_link_gap * 0.35
                + support_need * 0.15
                - cannibalization_penalty * 0.10
            ),
            "supporting_content_create": clamp(
                final_score * 0.18
                + commercial_intent * 0.18
                + support_need * 0.24
                + content_gap * 0.18
                + (0.16 if not cluster.primary_target_page else 0.05)
                - cannibalization_penalty * 0.15
            ),
            "backlink_support": clamp(
                final_score * 0.18
                + commercial_intent * 0.16
                + backlink_need * 0.44
                + demand * 0.12
                - cannibalization_penalty * 0.10
            ),
        }

    def _select_action(
        self,
        cluster: DemandCluster,
        action_scores: Dict[str, float],
        steering: Dict[str, Any],
        used_keywords: set[str],
        conversion_proximity: float,
    ) -> tuple[str, float, Optional[str]]:
        used_keywords = {keyword.lower() for keyword in used_keywords}
        canonical_topic = cluster.canonical_topic.lower()

        if steering.get("hard_negative_match"):
            top_action_family, top_action_score = max(action_scores.items(), key=lambda item: item[1])
            return top_action_family, top_action_score, "negative_keyword_conflict"

        gates = {}

        gates["ctr_optimize"] = None if cluster.primary_target_page else "missing_valid_target_page"
        gates["page_refresh"] = None if cluster.primary_target_page else "missing_retrievable_source_content"
        gates["internal_link_push"] = None if (cluster.primary_target_page or len(cluster.unique_pages) > 1) else "insufficient_eligible_targets"

        content_gate_reason = None
        if steering.get("hard_negative_match"):
            content_gate_reason = "negative_keyword_conflict"
        elif canonical_topic in used_keywords:
            content_gate_reason = "duplicate_target_guardrail"
        elif not cluster.primary_member.publishability.get("publishable", True):
            content_gate_reason = "publishability_gate_failed"
        elif cluster.intent_band == "support-only" and conversion_proximity < 0.60:
            content_gate_reason = "support_only_without_conversion_cluster"
        gates["supporting_content_create"] = content_gate_reason

        gates["backlink_support"] = None if action_scores["backlink_support"] >= 0.40 else "insufficient_authority_need"

        ranked_actions = sorted(action_scores.items(), key=lambda item: item[1], reverse=True)
        for action_family, action_score in ranked_actions:
            if gates.get(action_family):
                continue
            if action_score < 0.45:
                continue
            return action_family, action_score, None

        fallback_reason = next((reason for reason in gates.values() if reason), "low_confidence")
        top_action_family, top_action_score = ranked_actions[0]
        return top_action_family, top_action_score, fallback_reason

    def _cluster_support_role(self, cluster: DemandCluster) -> str:
        return "support" if cluster.intent_band == "support-only" else "primary"

    def _target_asset_type(self, context: Dict[str, Any]) -> str:
        return (
            context.get("page_type")
            or context.get("primary_taxonomy_type")
            or ("existing_page" if context.get("primary_taxonomy_url") else "mixed")
        )

    def _action_operational_risk(self, action_family: str) -> float:
        return {
            "ctr_optimize": 0.20,
            "page_refresh": 0.35,
            "internal_link_push": 0.30,
            "supporting_content_create": 0.60,
            "backlink_support": 0.75,
        }.get(action_family, 0.50)

    def _score_to_priority(self, score: float) -> str:
        score_pct = score * 100
        if score_pct >= 80:
            return "critical"
        if score_pct >= 60:
            return "high"
        if score_pct >= 40:
            return "medium"
        return "low"

    def _decision_from_dict(self, raw: Dict[str, Any]) -> ClusterDecision:
        members = [
            ClusterMember(
                query=member["query"],
                page=member["page"],
                clicks=member["clicks"],
                impressions=member["impressions"],
                ctr=member["ctr"],
                position=member["position"],
                intent_band=member["intent_band"],
                support_role=member["support_role"],
                catalog_context=member.get("catalog_context", {}),
                publishability=member.get("publishability", {}),
            )
            for member in raw["members"]
        ]
        primary_member = members[0]
        for member in members:
            if member.query == raw.get("canonical_topic") or member.query == raw.get("primary_query"):
                primary_member = member
                break

        cluster = DemandCluster(
            cluster_id=raw["cluster_id"],
            cluster_version=raw["cluster_version"],
            canonical_topic=raw["canonical_topic"],
            primary_target_page=raw.get("primary_target_page") or "",
            intent_band=raw["intent_band"],
            members=members,
            primary_member=primary_member,
        )

        return ClusterDecision(
            cluster=cluster,
            final_score=raw["score"],
            score_breakdown=raw["score_breakdown"],
            steering_matches=raw["steering_matches"],
            selected_action_family=raw["selected_action_family"],
            selected_action_score=raw["selected_action_score"],
            action_scores=raw["action_scores"],
            confidence=raw["confidence"],
            fallback_reason=raw.get("fallback_reason"),
            decision_window_key=raw["decision_window_key"],
            authoritative_eligible=raw.get("authoritative_eligible", False),
            authoritative_enabled=raw.get("authoritative_enabled", False),
        )
