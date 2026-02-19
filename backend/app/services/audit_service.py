"""
Audit trail service for logging all sensitive system operations.
Creates immutable audit records with full context capture.
Developed by: MERO:TG@QP4RM
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuditLog

logger = structlog.get_logger(__name__)


class AuditService:
    """
    Immutable audit logger for system-wide operation tracking.
    All sensitive operations (auth, CRUD, isolation, config changes)
    must be logged through this service.
    """

    @staticmethod
    async def log(
        db: AsyncSession,
        action: str,
        user_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Create an immutable audit log entry in the database.

        Args:
            db: The active async SQLAlchemy session.
            action: Dot-notation action identifier (e.g., 'device.isolate').
            user_id: UUID of the user performing the action.
            resource_type: Type of resource affected (e.g., 'device', 'alert').
            resource_id: String identifier of the affected resource.
            ip_address: Client IP address.
            user_agent: Client user-agent string.
            request_id: Correlation request ID.
            status_code: HTTP status code of the operation result.
            details: Additional contextual key-value pairs.

        Returns:
            The created AuditLog ORM instance.
        """
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status_code=status_code,
            details=details or {},
            occurred_at=datetime.now(timezone.utc),
        )
        db.add(audit_entry)
        await db.flush()

        logger.info(
            "Audit event recorded",
            audit_id=str(audit_entry.id),
            action=action,
            user_id=str(user_id) if user_id else None,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        return audit_entry
