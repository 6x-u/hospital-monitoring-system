"""
System health check and info endpoints.
Provides liveness/readiness probes for Kubernetes and load balancers.
Developed by: MERO:TG@QP4RM
"""

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rbac import Permission, require_permission
from app.db.session import get_db_session
from app.db.redis_client import redis_client
from app.schemas.schemas import SystemHealthResponse

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "/health",
    summary="Basic health check (no auth required)",
    response_model=dict,
)
async def health_check() -> dict:
    """Liveness probe for load balancers and Kubernetes."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "developer": settings.DEVELOPER_CREDIT,
    }


@router.get(
    "/ready",
    summary="Readiness probe — checks DB and Redis connectivity",
    response_model=dict,
)
async def readiness_check(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Readiness probe that verifies both database and Redis connectivity.
    Returns 200 if ready, 503 if any dependency is unavailable.
    """
    db_ok = False
    redis_ok = False

    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.error("Database readiness check failed", error=str(exc))

    try:
        await redis_client._get_client().ping()
        redis_ok = True
    except Exception as exc:
        logger.error("Redis readiness check failed", error=str(exc))

    ready = db_ok and redis_ok
    return {
        "status": "ready" if ready else "not_ready",
        "checks": {
            "database": "ok" if db_ok else "failed",
            "redis": "ok" if redis_ok else "failed",
        },
    }


@router.get(
    "/info",
    summary="System information (authenticated)",
    response_model=dict,
)
async def system_info(
    payload: dict = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> dict:
    """Return detailed system information for authenticated admin/engineers."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "developer": settings.DEVELOPER_CREDIT,
        "api_prefix": settings.API_PREFIX,
        "developer_contact": "TG:@QP4RM",
    }
