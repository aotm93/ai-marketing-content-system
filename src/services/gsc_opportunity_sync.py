"""Materialize live GSC opportunities into the persisted Opportunity pool."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha1
import json
from typing import Any, Dict, Optional

from sqlalchemy import func, inspect
from sqlalchemy.orm import Session

from src.config import settings
from src.models.config import SystemConfig
from src.models.gsc_data import Opportunity
from src.services.gsc_runtime import inspect_gsc_schema


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

DISCOVERY_FALLBACK_MIN_IMPRESSIONS = 10
DISCOVERY_FALLBACK_MIN_QUERY_TERMS = 2
DISCOVERY_FALLBACK_MIN_POSITION = 20.0


def _safe_json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _expected_ctr(position: float) -> float:
    normalized_position = max(1, min(10, int(round(position or 10))))
    return EXPECTED_CTR.get(normalized_position, 0.02)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _materialized_opportunity_id(site_url: str, query: str, page: str) -> str:
    digest = sha1(f"{site_url}|{query.lower()}|{page.lower()}".encode("utf-8")).hexdigest()[:32]
    return f"gsc_{digest}"


def _decision_window_key(now: datetime, site_url: str, query: str, page: str) -> str:
    digest = sha1(f"{site_url}|{query.lower()}|{page.lower()}".encode("utf-8")).hexdigest()[:16]
    return f"gsc:{now.strftime('%Y%m%d')}:{digest}"


def _score_breakdown(row: Any) -> Dict[str, float]:
    impressions = float(getattr(row, "impressions", 0) or 0)
    position = float(getattr(row, "position", 0.0) or 0.0)
    ctr = float(getattr(row, "ctr", 0.0) or 0.0)
    expected_ctr = _expected_ctr(position)

    return {
        "demand": round(_clamp(impressions / 2000.0), 4),
        "position_opportunity": round(_clamp((20.0 - position) / 16.0), 4),
        "ctr_gap": round(_clamp(expected_ctr - ctr), 4),
    }


def _discovery_score_breakdown(row: Any) -> Dict[str, float]:
    impressions = float(getattr(row, "impressions", 0) or 0)
    position = float(getattr(row, "position", 0.0) or 0.0)
    clicks = float(getattr(row, "clicks", 0) or 0)

    safe_position = min(max(position, DISCOVERY_FALLBACK_MIN_POSITION), 100.0)
    click_share = clicks / max(impressions, 1.0)

    return {
        "demand": round(_clamp(impressions / 100.0), 4),
        "discovery_gap": round(
            _clamp((safe_position - DISCOVERY_FALLBACK_MIN_POSITION) / 80.0),
            4,
        ),
        "zero_click_gap": round(
            _clamp(1.0 - min(click_share, 0.25) / 0.25),
            4,
        ),
    }


def _priority_from_score(score: float) -> str:
    if score >= 80:
        return "high"
    if score >= 55:
        return "medium"
    return "low"


def _set_system_config(db: Session, key: str, value: Optional[str], data_type: str = "string") -> None:
    if not inspect(db.bind).has_table("system_config"):
        return

    record = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not record:
        record = SystemConfig(key=key)
        db.add(record)

    record.value = value
    record.data_type = data_type


def _fallback_sort_key(row: Any) -> tuple[float, float, float]:
    impressions = float(getattr(row, "impressions", 0) or 0)
    position = min(float(getattr(row, "position", 0.0) or 0.0), 100.0)
    clicks = float(getattr(row, "clicks", 0) or 0)
    return (impressions, position, -clicks)


def _load_discovery_fallback_rows(
    client: Any,
    *,
    now: datetime,
    days_back: int,
    limit: int,
) -> list[Any]:
    if not hasattr(client, "get_search_analytics"):
        return []

    start_date = (now - timedelta(days=days_back)).date().isoformat()
    end_date = now.date().isoformat()
    row_limit = min(max(limit * 10, 250), 25000)

    rows = client.get_search_analytics(
        start_date=start_date,
        end_date=end_date,
        dimensions=["query", "page"],
        row_limit=row_limit,
    )

    candidates = []
    for row in rows:
        query = (getattr(row, "query", "") or "").strip()
        page = (getattr(row, "page", "") or "").strip()
        impressions = int(getattr(row, "impressions", 0) or 0)
        position = float(getattr(row, "position", 0.0) or 0.0)
        clicks = int(getattr(row, "clicks", 0) or 0)

        if not query or not page:
            continue
        if len(query.split()) < DISCOVERY_FALLBACK_MIN_QUERY_TERMS:
            continue
        if impressions < DISCOVERY_FALLBACK_MIN_IMPRESSIONS:
            continue
        if position <= DISCOVERY_FALLBACK_MIN_POSITION:
            continue
        if clicks > max(5, int(impressions * 0.20)):
            continue

        candidates.append(row)

    candidates.sort(key=_fallback_sort_key, reverse=True)
    return candidates[:limit]


def materialize_gsc_opportunities(
    db: Session,
    client: Any,
    *,
    days: Optional[int] = None,
    limit: int = 100,
    force: bool = False,
    triggered_by: str = "manual",
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    schema = inspect_gsc_schema(db)

    if not getattr(settings, "gsc_opportunity_sync_enabled", True) and not force:
        return {
            "status": "disabled",
            "reason": "gsc_opportunity_sync_disabled",
            "schema": schema,
        }

    if not schema["opportunity_materialization_ready"]:
        return {
            "status": "degraded",
            "reason": "opportunity_schema_not_ready",
            "schema": schema,
        }

    days_back = max(1, int(days or settings.gsc_sync_days_back or 28))
    row_limit = max(1, min(int(limit or 100), 500))

    try:
        live_rows = client.get_low_hanging_fruits(days=days_back, limit=row_limit)
        materialization_strategy = "low_hanging_fruit"
        if not live_rows:
            live_rows = _load_discovery_fallback_rows(
                client,
                now=now,
                days_back=days_back,
                limit=row_limit,
            )
            materialization_strategy = "discovery_fallback" if live_rows else "low_hanging_fruit"

        created = 0
        updated = 0

        for row in live_rows:
            query = (getattr(row, "query", "") or "").strip()
            page = (getattr(row, "page", "") or "").strip()
            if not query or not page:
                continue

            opportunity_id = _materialized_opportunity_id(client.site_url, query, page)
            decision_window_key = _decision_window_key(now, client.site_url, query, page)
            is_discovery_fallback = materialization_strategy == "discovery_fallback"
            breakdown = _discovery_score_breakdown(row) if is_discovery_fallback else _score_breakdown(row)
            if is_discovery_fallback:
                score = round(
                    min(
                        100.0,
                        (
                            breakdown["demand"] * 0.45
                            + breakdown["discovery_gap"] * 0.40
                            + breakdown["zero_click_gap"] * 0.15
                        )
                        * 100.0,
                    ),
                    2,
                )
                confidence = round(
                    min(
                        0.80,
                        0.35 + breakdown["demand"] * 0.20 + breakdown["discovery_gap"] * 0.15,
                    ),
                    4,
                )
            else:
                score = round(
                    min(
                        100.0,
                        (
                            breakdown["demand"] * 0.50
                            + breakdown["position_opportunity"] * 0.35
                            + breakdown["ctr_gap"] * 0.15
                        )
                        * 100.0,
                    ),
                    2,
                )
                confidence = round(
                    min(
                        0.95,
                        0.45 + breakdown["demand"] * 0.25 + breakdown["position_opportunity"] * 0.20,
                    ),
                    4,
                )

            existing = db.query(Opportunity).filter(Opportunity.opportunity_id == opportunity_id).first()
            if existing is None:
                existing = Opportunity(
                    opportunity_id=opportunity_id,
                    opportunity_type="new_page" if is_discovery_fallback else "low_hanging_fruit",
                    status="pending",
                )
                db.add(existing)
                created += 1
            else:
                updated += 1

            existing.opportunity_type = "new_page" if is_discovery_fallback else "low_hanging_fruit"
            existing.target_query = query
            existing.target_page = page
            existing.score = score
            existing.confidence = confidence
            existing.current_position = float(getattr(row, "position", 0.0) or 0.0)
            existing.current_impressions = int(getattr(row, "impressions", 0) or 0)
            existing.current_ctr = float(getattr(row, "ctr", 0.0) or 0.0)
            existing.current_clicks = int(getattr(row, "clicks", 0) or 0)
            existing.potential_clicks = max(
                1 if is_discovery_fallback and existing.current_impressions else 0,
                int(
                    existing.current_impressions
                    * (
                        max(0.03, min(0.12, breakdown["zero_click_gap"] * 0.12))
                        if is_discovery_fallback
                        else max(breakdown["ctr_gap"], 0.02)
                    )
                ),
            )
            existing.recommended_action_family = "new_content" if is_discovery_fallback else "ctr_optimize"
            existing.recommended_action_confidence = confidence
            existing.action_type = existing.action_type or ("generate" if is_discovery_fallback else "optimize")
            existing.action_details = _safe_json_dumps(
                {
                    "source": "gsc_discovery_fallback" if is_discovery_fallback else "gsc_materializer",
                    "days_back": days_back,
                    "triggered_by": triggered_by,
                    "fallback_used": is_discovery_fallback,
                    "current_target_page": page,
                    **(
                        {
                            "discovery_gap": breakdown["discovery_gap"],
                            "zero_click_gap": breakdown["zero_click_gap"],
                            "suggested_action": "create_supporting_content",
                        }
                        if is_discovery_fallback
                        else {
                            "ctr_gap": breakdown["ctr_gap"],
                        }
                    ),
                }
            )
            existing.score_breakdown_json = _safe_json_dumps(breakdown)
            existing.decision_trace_json = _safe_json_dumps(
                {
                    "source": "gsc_discovery_fallback" if is_discovery_fallback else "gsc_materializer",
                    "query": query,
                    "page": page,
                    "impressions": existing.current_impressions,
                    "clicks": existing.current_clicks,
                    "position": existing.current_position,
                    "decision_window_key": decision_window_key,
                }
            )
            existing.engine_mode = "gsc_discovery_fallback" if is_discovery_fallback else "gsc_materialized"
            existing.engine_version = "gsc-opportunity-sync-v2"
            existing.fallback_reason = "no_low_hanging_fruits" if is_discovery_fallback else None
            existing.decision_window_key = decision_window_key
            existing.priority = _priority_from_score(score)

        _set_system_config(db, "GSC_LAST_OPPORTUNITY_SYNC_AT", now.isoformat())
        _set_system_config(db, "GSC_LAST_OPPORTUNITY_SYNC_STATUS", "success")
        _set_system_config(db, "GSC_LAST_OPPORTUNITY_SYNC_ERROR", "")
        _set_system_config(db, "GSC_LAST_OPPORTUNITY_SYNC_COUNT", str(len(live_rows)), data_type="int")
        _set_system_config(db, "GSC_LAST_OPPORTUNITY_SYNC_TRIGGER", triggered_by)
        db.commit()

        persisted_pool_count = db.query(func.count(Opportunity.id)).scalar() or 0
        return {
            "status": "success",
            "days": days_back,
            "limit": row_limit,
            "live_opportunity_count": len(live_rows),
            "created": created,
            "updated": updated,
            "persisted_opportunity_count": persisted_pool_count,
            "materialization_strategy": materialization_strategy,
            "synced_at": now.isoformat(),
            "triggered_by": triggered_by,
        }
    except Exception as exc:
        db.rollback()
        _set_system_config(db, "GSC_LAST_OPPORTUNITY_SYNC_AT", now.isoformat())
        _set_system_config(db, "GSC_LAST_OPPORTUNITY_SYNC_STATUS", "error")
        _set_system_config(db, "GSC_LAST_OPPORTUNITY_SYNC_ERROR", str(exc))
        db.commit()
        return {
            "status": "error",
            "error": str(exc),
            "days": days_back,
            "limit": row_limit,
        }
