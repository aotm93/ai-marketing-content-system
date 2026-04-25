"""Shared Google Search Console runtime and readiness helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy import func, inspect
from sqlalchemy.orm import Session

from src.config import settings
from src.config.utils import get_config_value
from src.integrations.gsc_client import GSCAuthMethod, GSCClient
from src.models.gsc_data import Opportunity, TopicCluster


def _model_column_names(model: Any) -> set[str]:
    return {column.name for column in model.__table__.columns}


OPPORTUNITY_SYNC_REQUIRED_COLUMNS = _model_column_names(Opportunity)

CLUSTER_SHADOW_REQUIRED_COLUMNS = _model_column_names(TopicCluster)


@dataclass(frozen=True)
class GSCRuntimeConfig:
    enabled: bool
    site_url: Optional[str]
    auth_method: GSCAuthMethod
    credentials_json: Optional[str]
    credentials_path: Optional[str]
    credential_source: Optional[str]
    configured: bool
    issues: tuple[str, ...]

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "site_url": self.site_url,
            "auth_method": self.auth_method.value,
            "credential_source": self.credential_source or "none",
            "configured": self.configured,
            "issues": list(self.issues),
        }


def _normalize_auth_method(value: Optional[str]) -> tuple[GSCAuthMethod, list[str]]:
    issues: list[str] = []
    raw_value = (value or GSCAuthMethod.SERVICE_ACCOUNT.value).strip().lower()

    try:
        return GSCAuthMethod(raw_value), issues
    except ValueError:
        issues.append("invalid_auth_method")
        return GSCAuthMethod.SERVICE_ACCOUNT, issues


def resolve_gsc_runtime(overrides: Optional[Dict[str, Any]] = None) -> GSCRuntimeConfig:
    overrides = overrides or {}

    enabled = bool(overrides.get("gsc_enabled", settings.gsc_enabled))
    site_url = (overrides.get("gsc_site_url", settings.gsc_site_url) or "").strip() or None
    credentials_json = (overrides.get("gsc_credentials_json", settings.gsc_credentials_json) or "").strip() or None
    credentials_path = (overrides.get("gsc_credentials_path", settings.gsc_credentials_path) or "").strip() or None
    auth_method, issues = _normalize_auth_method(overrides.get("gsc_auth_method", settings.gsc_auth_method))

    credential_source = None
    if credentials_json:
        credential_source = "json"
    elif credentials_path:
        credential_source = "path"

    if not enabled:
        issues.append("gsc_disabled")
    if not site_url:
        issues.append("missing_site_url")
    if auth_method == GSCAuthMethod.OAUTH:
        issues.append("oauth_not_supported")
    elif credential_source is None:
        issues.append("missing_credentials")

    configured = enabled and site_url is not None and auth_method == GSCAuthMethod.SERVICE_ACCOUNT and credential_source is not None

    return GSCRuntimeConfig(
        enabled=enabled,
        site_url=site_url,
        auth_method=auth_method,
        credentials_json=credentials_json,
        credentials_path=credentials_path,
        credential_source=credential_source,
        configured=configured,
        issues=tuple(dict.fromkeys(issues)),
    )


def build_gsc_client(runtime: Optional[GSCRuntimeConfig] = None) -> GSCClient:
    runtime = runtime or resolve_gsc_runtime()
    if not runtime.enabled:
        raise RuntimeError("GSC integration disabled")
    if not runtime.site_url:
        raise RuntimeError("GSC site URL is missing")
    if runtime.auth_method == GSCAuthMethod.OAUTH:
        raise RuntimeError("OAuth GSC authentication is not supported in this runtime")
    if runtime.credential_source is None:
        raise RuntimeError("GSC credentials are missing")

    return GSCClient(
        site_url=runtime.site_url,
        auth_method=runtime.auth_method,
        credentials_json=runtime.credentials_json,
        credentials_path=runtime.credentials_path,
    )


def get_gsc_client_or_none() -> Optional[GSCClient]:
    runtime = resolve_gsc_runtime()
    if not runtime.configured:
        return None

    try:
        return build_gsc_client(runtime)
    except Exception:
        return None


def inspect_gsc_schema(db: Session) -> Dict[str, Any]:
    inspector = inspect(db.bind)

    has_opportunities = inspector.has_table("opportunities")
    has_topic_clusters = inspector.has_table("topic_clusters")
    has_gsc_queries = inspector.has_table("gsc_queries")
    has_alembic = inspector.has_table("alembic_version")

    opportunity_columns = set()
    topic_cluster_columns = set()

    if has_opportunities:
        opportunity_columns = {column["name"] for column in inspector.get_columns("opportunities")}
    if has_topic_clusters:
        topic_cluster_columns = {column["name"] for column in inspector.get_columns("topic_clusters")}

    missing_opportunity_columns = sorted(OPPORTUNITY_SYNC_REQUIRED_COLUMNS - opportunity_columns)
    missing_cluster_columns = sorted(CLUSTER_SHADOW_REQUIRED_COLUMNS - topic_cluster_columns)

    opportunity_materialization_ready = has_opportunities and not missing_opportunity_columns
    cluster_shadow_ready = opportunity_materialization_ready and has_topic_clusters and not missing_cluster_columns
    authoritative_ready = cluster_shadow_ready and has_alembic

    return {
        "status": "ready" if opportunity_materialization_ready else "degraded",
        "migration_tracked": has_alembic,
        "tables": {
            "gsc_queries": has_gsc_queries,
            "opportunities": has_opportunities,
            "topic_clusters": has_topic_clusters,
            "alembic_version": has_alembic,
        },
        "opportunity_materialization_ready": opportunity_materialization_ready,
        "cluster_shadow_ready": cluster_shadow_ready,
        "authoritative_ready": authoritative_ready,
        "missing_columns": {
            "opportunities": missing_opportunity_columns,
            "topic_clusters": missing_cluster_columns,
        },
    }


def get_gsc_operational_metrics(db: Session, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    schema = schema or inspect_gsc_schema(db)

    metrics: Dict[str, Any] = {
        "raw_query_count": None,
        "last_raw_query_sync_at": None,
        "persisted_opportunity_count": None,
        "last_opportunity_sync_at": get_config_value(db, "GSC_LAST_OPPORTUNITY_SYNC_AT"),
        "last_opportunity_sync_status": get_config_value(db, "GSC_LAST_OPPORTUNITY_SYNC_STATUS"),
        "last_opportunity_sync_error": get_config_value(db, "GSC_LAST_OPPORTUNITY_SYNC_ERROR"),
        "last_opportunity_sync_count": get_config_value(db, "GSC_LAST_OPPORTUNITY_SYNC_COUNT"),
    }

    if schema["tables"]["gsc_queries"]:
        from src.models.gsc_data import GSCQuery

        metrics["raw_query_count"] = db.query(func.count(GSCQuery.id)).scalar() or 0
        latest_query_sync = db.query(func.max(GSCQuery.synced_at)).scalar()
        metrics["last_raw_query_sync_at"] = latest_query_sync.isoformat() if latest_query_sync else None

    if schema["opportunity_materialization_ready"]:
        from src.models.gsc_data import Opportunity

        metrics["persisted_opportunity_count"] = db.query(func.count(Opportunity.id)).scalar() or 0

    return metrics


def get_gsc_readiness(db: Optional[Session] = None, include_live_health: bool = False) -> Dict[str, Any]:
    runtime = resolve_gsc_runtime()
    readiness: Dict[str, Any] = runtime.to_public_dict()
    readiness["opportunity_sync_enabled"] = bool(getattr(settings, "gsc_opportunity_sync_enabled", True))

    if not runtime.enabled:
        readiness["status"] = "disabled"
    elif not runtime.configured:
        readiness["status"] = "misconfigured"
    else:
        readiness["status"] = "ready"

    if db is not None:
        schema = inspect_gsc_schema(db)
        readiness["schema"] = schema
        readiness["metrics"] = get_gsc_operational_metrics(db, schema=schema)
        if readiness["status"] == "ready" and not schema["opportunity_materialization_ready"]:
            readiness["status"] = "degraded"

    if include_live_health and runtime.configured:
        try:
            client = build_gsc_client(runtime)
            readiness["health"] = client.health_check()
            if readiness["health"].get("status") != "connected":
                readiness["status"] = readiness["health"].get("status") or "error"
        except Exception as exc:
            readiness["health"] = {"status": "error", "error": str(exc)}
            readiness["status"] = "error"
    else:
        readiness["health"] = None

    return readiness


def gsc_http_status(readiness: Dict[str, Any]) -> int:
    status = readiness.get("status")
    if status == "ready":
        return 200
    if status == "degraded":
        return 409
    return 503
