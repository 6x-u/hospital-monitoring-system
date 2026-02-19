"""
Metrics ingestion and query API endpoints.
Handles agent data submissions and time-series queries.
Developed by: MERO:TG@QP4RM
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Permission, require_permission
from app.core.security import get_current_user_payload
from app.db.session import get_db_session
from app.db.redis_client import redis_client
from app.models.models import Metric, Device
from app.schemas.schemas import MetricIngest, MetricResponse, MetricSummary
from app.services.metrics_service import MetricsService

logger = structlog.get_logger(__name__)
router = APIRouter()


async def _authenticate_agent(request: Request, db: AsyncSession) -> Device:
    """
    Authenticate an incoming agent request using its API key.
    Returns the associated Device if valid.
    """
    from app.core.security import PasswordHasher
    api_key = request.headers.get("X-Agent-API-Key")
    device_id_str = request.headers.get("X-Device-ID")

    if not api_key or not device_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing agent authentication headers.",
        )

    try:
        device_id = uuid.UUID(device_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Device-ID format.",
        )

    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()

    if not device or not device.api_key_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device not found or not configured.",
        )

    if not PasswordHasher.verify_password(api_key, device.api_key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent API key.",
        )

    return device


@router.post(
    "/ingest",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest metrics from a monitoring agent",
)
async def ingest_metrics(
    request: Request,
    body: MetricIngest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Receive and process a batch of metrics from a monitoring agent.
    Agent authentication is done via X-Agent-API-Key and X-Device-ID headers.
    Triggers anomaly detection and alert evaluation.
    """
    device = await _authenticate_agent(request, db)

    if device.is_isolated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device is currently isolated. Metrics collection suspended.",
        )

    metrics_service = MetricsService()
    metric_record = await metrics_service.process_and_store(
        db=db, device=device, ingest_data=body
    )

    # Update device last_seen
    device.last_seen = datetime.now(timezone.utc)
    await db.flush()

    # Publish to Redis for WebSocket broadcast
    import json
    await redis_client.publish(
        f"metrics:device:{device.id}",
        json.dumps({"device_id": str(device.id), "metric_id": str(metric_record.id)}),
    )

    return {
        "status": "accepted",
        "metric_id": str(metric_record.id),
        "is_anomalous": metric_record.is_anomalous,
        "anomaly_score": metric_record.anomaly_score,
    }


@router.get(
    "/{device_id}/history",
    response_model=List[MetricResponse],
    summary="Get historical metrics for a device",
)
async def get_metric_history(
    device_id: uuid.UUID,
    start_time: Optional[datetime] = Query(
        default=None,
        description="Start of time range (ISO 8601)",
    ),
    end_time: Optional[datetime] = Query(
        default=None,
        description="End of time range (ISO 8601)",
    ),
    limit: int = Query(default=200, ge=1, le=1000),
    anomalous_only: bool = Query(default=False),
    payload: dict = Depends(require_permission(Permission.METRICS_READ)),
    db: AsyncSession = Depends(get_db_session),
) -> List[MetricResponse]:
    """
    Retrieve time-series metric history for a specific device.
    Defaults to the last 24 hours if no time range is specified.
    """
    if not end_time:
        end_time = datetime.now(timezone.utc)
    if not start_time:
        start_time = end_time - timedelta(hours=24)

    conditions = [
        Metric.device_id == device_id,
        Metric.collected_at >= start_time,
        Metric.collected_at <= end_time,
    ]
    if anomalous_only:
        conditions.append(Metric.is_anomalous == True)

    result = await db.execute(
        select(Metric)
        .where(and_(*conditions))
        .order_by(Metric.collected_at.desc())
        .limit(limit)
    )
    metrics = result.scalars().all()
    return [MetricResponse.model_validate(m) for m in metrics]


@router.get(
    "/summary/all",
    response_model=List[MetricSummary],
    summary="Get latest metric summaries for all active devices",
)
async def get_all_devices_summary(
    payload: dict = Depends(require_permission(Permission.METRICS_READ)),
    db: AsyncSession = Depends(get_db_session),
) -> List[MetricSummary]:
    """
    Return the latest aggregated metric summary for each active device.
    Results are cached in Redis for 30 seconds for performance.
    """
    cache_key = "metrics:summary:all"
    cached = await redis_client.get(cache_key)

    if cached:
        import json
        return [MetricSummary.model_validate(item) for item in json.loads(cached)]

    metrics_service = MetricsService()
    summaries = await metrics_service.get_all_device_summaries(db)

    import json
    await redis_client.setex(
        cache_key,
        30,
        json.dumps([s.model_dump(mode="json") for s in summaries]),
    )
    return summaries
