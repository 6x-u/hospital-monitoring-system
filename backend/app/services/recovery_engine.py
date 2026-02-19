"""
Auto-recovery engine for automatic service restoration.
Monitors service health and triggers recovery actions when failures are detected.
Developed by: MERO:TG@QP4RM
"""

import asyncio
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionFactory
from app.models.models import ServiceStatus, Device
from app.services.alert_service import AlertService

logger = structlog.get_logger(__name__)

# Maximum recovery attempts before giving up
MAX_RECOVERY_ATTEMPTS = 3
# Time between recovery attempts in seconds
RECOVERY_RETRY_DELAY = 30
# How often the engine polls for failed services
POLL_INTERVAL_SECONDS = 60


class RecoveryEngine:
    """
    Asynchronous service recovery engine.
    Polls service statuses, detects failures, and attempts automatic recovery.
    Notifies administrators on recovery success or failure.
    """

    def __init__(self) -> None:
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._alert_service = AlertService()
        # Track in-progress recovery attempts per service
        self._recovery_attempts: Dict[str, int] = {}

    async def start(self) -> None:
        """Start the recovery engine background task."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Auto-recovery engine started", poll_interval=POLL_INTERVAL_SECONDS)

    async def stop(self) -> None:
        """Stop the recovery engine gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Auto-recovery engine stopped")

    async def _run_loop(self) -> None:
        """Main polling loop for service health checking."""
        while self._running:
            try:
                await self._check_all_services()
            except Exception as exc:
                logger.error("Recovery engine loop error", error=str(exc))
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def _check_all_services(self) -> None:
        """
        Query all services with auto-recovery enabled that have failed.
        Trigger recovery for each failed service under the attempt limit.
        """
        async with AsyncSessionFactory() as db:
            result = await db.execute(
                select(ServiceStatus)
                .where(
                    ServiceStatus.auto_recovery_enabled == True,
                    ServiceStatus.status.in_(["stopped", "degraded"]),
                    ServiceStatus.consecutive_failures > 0,
                )
                .join(Device, ServiceStatus.device_id == Device.id)
                .where(
                    Device.is_active == True,
                    Device.is_isolated == False,
                )
            )
            failed_services: List[ServiceStatus] = result.scalars().all()

            for service in failed_services:
                service_key = f"{service.device_id}:{service.service_name}"
                attempts = self._recovery_attempts.get(service_key, 0)

                if attempts >= MAX_RECOVERY_ATTEMPTS:
                    logger.error(
                        "Max recovery attempts reached — escalating",
                        service=service.service_name,
                        device_id=str(service.device_id),
                        attempts=attempts,
                    )
                    await self._escalate_failure(db, service)
                    continue

                self._recovery_attempts[service_key] = attempts + 1
                asyncio.create_task(
                    self._attempt_recovery(service)
                )

    async def _attempt_recovery(self, service: ServiceStatus) -> None:
        """
        Attempt to restart a failed service.
        Logs all recovery actions and notifies on success or failure.
        """
        service_key = f"{service.device_id}:{service.service_name}"
        logger.warning(
            "Attempting service recovery",
            service=service.service_name,
            device_id=str(service.device_id),
            attempt=self._recovery_attempts.get(service_key, 1),
        )

        await asyncio.sleep(RECOVERY_RETRY_DELAY)

        success = False
        error_detail = ""

        try:
            if service.recovery_command:
                result = subprocess.run(
                    service.recovery_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                success = result.returncode == 0
                error_detail = result.stderr if not success else ""
            else:
                # Default: attempt systemd restart
                result = subprocess.run(
                    ["systemctl", "restart", service.service_name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                success = result.returncode == 0
                error_detail = result.stderr if not success else ""
        except subprocess.TimeoutExpired:
            success = False
            error_detail = "Recovery command timed out after 30 seconds"
        except Exception as exc:
            success = False
            error_detail = str(exc)

        async with AsyncSessionFactory() as db:
            if success:
                service.consecutive_failures = 0
                service.status = "running"
                self._recovery_attempts.pop(service_key, None)
                db.add(service)
                await db.commit()

                await self._alert_service.create_alert(
                    db=db,
                    device_id=service.device_id,
                    alert_type="recovery_success",
                    severity="info",
                    title=f"Service Recovered: {service.service_name}",
                    message=f"Auto-recovery successful for service '{service.service_name}' "
                            f"on device {service.device_id}.",
                )
                logger.info(
                    "Service recovery successful",
                    service=service.service_name,
                    device_id=str(service.device_id),
                )
            else:
                await self._alert_service.create_alert(
                    db=db,
                    device_id=service.device_id,
                    alert_type="recovery_failed",
                    severity="high",
                    title=f"Recovery Failed: {service.service_name}",
                    message=(
                        f"Auto-recovery attempt failed for '{service.service_name}'. "
                        f"Error: {error_detail}"
                    ),
                    metadata={"error": error_detail},
                )
                logger.error(
                    "Service recovery failed",
                    service=service.service_name,
                    device_id=str(service.device_id),
                    error=error_detail,
                )

    async def _escalate_failure(self, db: AsyncSession, service: ServiceStatus) -> None:
        """Escalate persistent failures to critical alerts for admin intervention."""
        await self._alert_service.create_alert(
            db=db,
            device_id=service.device_id,
            alert_type="service_down",
            severity="critical",
            title=f"CRITICAL: Service Down After {MAX_RECOVERY_ATTEMPTS} Recovery Attempts",
            message=(
                f"Service '{service.service_name}' has failed {MAX_RECOVERY_ATTEMPTS} "
                f"recovery attempts and requires immediate manual intervention."
            ),
            metadata={"consecutive_failures": service.consecutive_failures},
        )
