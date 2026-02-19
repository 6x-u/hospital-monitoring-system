"""
Alerts management API endpoints.
Handles alert listing, acknowledgment, suppression, and resolution.
Developed by: MERO:TG@QP4RM
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, and_, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Permission, require_permission
from app.db.session import get_db_session
from app.models.models import Alert
from app.schemas.schemas import (
    AlertAcknowledgeRequest,
    AlertListResponse,
    AlertResponse,
    AlertSuppressRequest,
)
from app.services.audit_service import AuditService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "/",
    response_model=AlertListResponse,
    summary="List all alerts with optional filters",
)
async def list_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    severity: Optional[str] = Query(default=None),
    alert_type: Optional[str] = Query(default=None),
    device_id: Optional[uuid.UUID] = Query(default=None),
    is_acknowledged: Optional[bool] = Query(default=None),
    is_resolved: Optional[bool] = Query(default=None),
    payload: dict = Depends(require_permission(Permission.ALERT_READ)),
    db: AsyncSession = Depends(get_db_session),
) -> AlertListResponse:
    """Retrieve paginated alerts with optional filters."""
    conditions = []
    if severity:
        conditions.append(Alert.severity == severity)
    if alert_type:
        conditions.append(Alert.alert_type == alert_type)
    if device_id:
        conditions.append(Alert.device_id == device_id)
    if is_acknowledged is not None:
        conditions.append(Alert.is_acknowledged == is_acknowledged)
    if is_resolved is not None:
        conditions.append(Alert.is_resolved == is_resolved)

    base_query = select(Alert)
    if conditions:
        base_query = base_query.where(and_(*conditions))

    count_result = await db.execute(
        select(sa_func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.order_by(Alert.created_at.desc()).offset(offset).limit(page_size)
    )
    alerts = result.scalars().all()

    return AlertListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[AlertResponse.model_validate(a) for a in alerts],
    )


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get alert by ID",
)
async def get_alert(
    alert_id: uuid.UUID,
    payload: dict = Depends(require_permission(Permission.ALERT_READ)),
    db: AsyncSession = Depends(get_db_session),
) -> AlertResponse:
    """Retrieve full details of a single alert."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found."
        )
    return AlertResponse.model_validate(alert)


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertResponse,
    summary="Acknowledge an alert",
)
async def acknowledge_alert(
    request: Request,
    alert_id: uuid.UUID,
    body: AlertAcknowledgeRequest,
    payload: dict = Depends(require_permission(Permission.ALERT_ACKNOWLEDGE)),
    db: AsyncSession = Depends(get_db_session),
) -> AlertResponse:
    """Mark an alert as acknowledged with an optional note."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    if alert.is_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Alert is already acknowledged.",
        )

    alert.is_acknowledged = True
    alert.acknowledged_by = uuid.UUID(payload["sub"])
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledgment_note = body.note
    await db.flush()

    await AuditService.log(
        db=db,
        user_id=uuid.UUID(payload["sub"]),
        action="alert.acknowledge",
        resource_type="alert",
        resource_id=str(alert_id),
        ip_address=request.client.host if request.client else None,
        details={"severity": alert.severity, "alert_type": alert.alert_type},
    )

    logger.info("Alert acknowledged", alert_id=str(alert_id), by=payload["sub"])
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertResponse,
    summary="Mark an alert as resolved",
)
async def resolve_alert(
    request: Request,
    alert_id: uuid.UUID,
    payload: dict = Depends(require_permission(Permission.ALERT_ACKNOWLEDGE)),
    db: AsyncSession = Depends(get_db_session),
) -> AlertResponse:
    """Mark an alert as fully resolved."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    await db.flush()

    await AuditService.log(
        db=db,
        user_id=uuid.UUID(payload["sub"]),
        action="alert.resolve",
        resource_type="alert",
        resource_id=str(alert_id),
        ip_address=request.client.host if request.client else None,
    )

    await db.refresh(alert)
    return AlertResponse.model_validate(alert)


@router.post(
    "/{alert_id}/suppress",
    response_model=AlertResponse,
    summary="Suppress duplicate notifications for an alert",
)
async def suppress_alert(
    request: Request,
    alert_id: uuid.UUID,
    body: AlertSuppressRequest,
    payload: dict = Depends(require_permission(Permission.ALERT_SUPPRESS)),
    db: AsyncSession = Depends(get_db_session),
) -> AlertResponse:
    """
    Suppress repeated notifications for a specific alert.
    Useful for known issues that are being addressed.
    """
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    alert.is_suppressed = True
    alert.last_notified_at = datetime.now(timezone.utc)
    await db.flush()

    from app.db.redis_client import redis_client
    suppress_key = f"alert:suppressed:{alert_id}"
    await redis_client.setex(suppress_key, body.duration_minutes * 60, "1")

    await AuditService.log(
        db=db,
        user_id=uuid.UUID(payload["sub"]),
        action="alert.suppress",
        resource_type="alert",
        resource_id=str(alert_id),
        ip_address=request.client.host if request.client else None,
        details={"duration_minutes": body.duration_minutes},
    )

    await db.refresh(alert)
    return AlertResponse.model_validate(alert)
