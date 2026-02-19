"""
Devices management API endpoints.
Handles device registration, listing, updates, isolation, and health.
Developed by: MERO:TG@QP4RM
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Permission, require_permission
from app.db.session import get_db_session
from app.models.models import Device, Alert
from app.schemas.schemas import (
    DeviceCreate,
    DeviceIsolateRequest,
    DeviceListResponse,
    DeviceResponse,
    DeviceUpdate,
)
from app.services.audit_service import AuditService
from app.services.alert_service import AlertService
from app.core.security import get_current_user_payload

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "/",
    response_model=DeviceListResponse,
    summary="List all monitored devices",
)
async def list_devices(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    device_type: Optional[str] = Query(default=None),
    department: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    is_isolated: Optional[bool] = Query(default=None),
    payload: dict = Depends(require_permission(Permission.DEVICE_READ)),
    db: AsyncSession = Depends(get_db_session),
) -> DeviceListResponse:
    """Retrieve a paginated list of monitored devices with optional filters."""
    query = select(Device)

    if device_type:
        query = query.where(Device.device_type == device_type)
    if department:
        query = query.where(Device.department == department)
    if is_active is not None:
        query = query.where(Device.is_active == is_active)
    if is_isolated is not None:
        query = query.where(Device.is_isolated == is_isolated)

    count_result = await db.execute(
        select(sa_func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Device.created_at.desc()).offset(offset).limit(page_size)
    )
    devices = result.scalars().all()

    return DeviceListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[DeviceResponse.model_validate(d) for d in devices],
    )


@router.post(
    "/",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new monitored device",
)
async def create_device(
    request: Request,
    body: DeviceCreate,
    payload: dict = Depends(require_permission(Permission.DEVICE_WRITE)),
    db: AsyncSession = Depends(get_db_session),
) -> DeviceResponse:
    """Register a new device in the monitoring system."""
    # Check for duplicate hostname
    existing = await db.execute(
        select(Device).where(Device.hostname == body.hostname)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device with hostname '{body.hostname}' already exists.",
        )

    device = Device(
        hostname=body.hostname,
        ip_address=body.ip_address,
        mac_address=body.mac_address,
        device_type=body.device_type,
        department=body.department,
        location=body.location,
        os_type=body.os_type,
        os_version=body.os_version,
        tags=body.tags,
    )
    db.add(device)
    await db.flush()
    await db.refresh(device)

    await AuditService.log(
        db=db,
        user_id=uuid.UUID(payload["sub"]),
        action="device.create",
        resource_type="device",
        resource_id=str(device.id),
        ip_address=request.client.host if request.client else None,
        details={"hostname": device.hostname},
    )

    logger.info("Device registered", device_id=str(device.id), hostname=device.hostname)
    return DeviceResponse.model_validate(device)


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    summary="Get device by ID",
)
async def get_device(
    device_id: uuid.UUID,
    payload: dict = Depends(require_permission(Permission.DEVICE_READ)),
    db: AsyncSession = Depends(get_db_session),
) -> DeviceResponse:
    """Retrieve a single device's full details by its UUID."""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found.",
        )
    return DeviceResponse.model_validate(device)


@router.patch(
    "/{device_id}",
    response_model=DeviceResponse,
    summary="Update device information",
)
async def update_device(
    request: Request,
    device_id: uuid.UUID,
    body: DeviceUpdate,
    payload: dict = Depends(require_permission(Permission.DEVICE_WRITE)),
    db: AsyncSession = Depends(get_db_session),
) -> DeviceResponse:
    """Update mutable fields of a monitored device."""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)

    await db.flush()
    await db.refresh(device)

    await AuditService.log(
        db=db,
        user_id=uuid.UUID(payload["sub"]),
        action="device.update",
        resource_type="device",
        resource_id=str(device_id),
        ip_address=request.client.host if request.client else None,
        details={"updated_fields": list(update_data.keys())},
    )

    return DeviceResponse.model_validate(device)


@router.post(
    "/{device_id}/isolate",
    response_model=DeviceResponse,
    summary="Isolate a device from the network",
)
async def isolate_device(
    request: Request,
    device_id: uuid.UUID,
    body: DeviceIsolateRequest,
    payload: dict = Depends(require_permission(Permission.DEVICE_ISOLATE)),
    db: AsyncSession = Depends(get_db_session),
    alert_service: AlertService = Depends(lambda: AlertService()),
) -> DeviceResponse:
    """
    Mark a device as isolated. Creates a critical security alert.
    The actual network isolation is performed by the recovery engine.
    """
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    if device.is_isolated:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device is already isolated.",
        )

    device.is_isolated = True
    device.isolation_reason = body.reason
    device.isolated_at = datetime.now(timezone.utc)
    await db.flush()

    # Create a security alert for isolation event
    await alert_service.create_alert(
        db=db,
        device_id=device_id,
        alert_type="security_breach",
        severity="critical",
        title=f"Device Isolated: {device.hostname}",
        message=f"Device manually isolated. Reason: {body.reason}",
    )

    await AuditService.log(
        db=db,
        user_id=uuid.UUID(payload["sub"]),
        action="device.isolate",
        resource_type="device",
        resource_id=str(device_id),
        ip_address=request.client.host if request.client else None,
        details={"reason": body.reason, "hostname": device.hostname},
    )

    logger.warning(
        "Device isolated",
        device_id=str(device_id),
        hostname=device.hostname,
        reason=body.reason,
        isolated_by=payload["sub"],
    )
    await db.refresh(device)
    return DeviceResponse.model_validate(device)


@router.post(
    "/{device_id}/unisolate",
    response_model=DeviceResponse,
    summary="Remove device isolation",
)
async def unisolate_device(
    request: Request,
    device_id: uuid.UUID,
    payload: dict = Depends(require_permission(Permission.DEVICE_ISOLATE)),
    db: AsyncSession = Depends(get_db_session),
) -> DeviceResponse:
    """Remove isolation from a device after it has been cleared."""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    device.is_isolated = False
    device.isolation_reason = None
    device.isolated_at = None
    await db.flush()

    await AuditService.log(
        db=db,
        user_id=uuid.UUID(payload["sub"]),
        action="device.unisolate",
        resource_type="device",
        resource_id=str(device_id),
        ip_address=request.client.host if request.client else None,
    )

    await db.refresh(device)
    return DeviceResponse.model_validate(device)


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a device and all its data",
)
async def delete_device(
    request: Request,
    device_id: uuid.UUID,
    payload: dict = Depends(require_permission(Permission.DEVICE_DELETE)),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Permanently delete a device and cascade-delete all metrics and alerts."""
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    await db.delete(device)

    await AuditService.log(
        db=db,
        user_id=uuid.UUID(payload["sub"]),
        action="device.delete",
        resource_type="device",
        resource_id=str(device_id),
        ip_address=request.client.host if request.client else None,
        details={"hostname": device.hostname},
    )

    logger.warning(
        "Device deleted",
        device_id=str(device_id),
        hostname=device.hostname,
        deleted_by=payload["sub"],
    )
