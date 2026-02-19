"""
Alert management and notification service.
Creates, evaluates, and dispatches alerts via email and webhook.
Developed by: MERO:TG@QP4RM
"""

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

import aiohttp
import aiosmtplib
import structlog
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.redis_client import redis_client
from app.models.models import Alert, Device

logger = structlog.get_logger(__name__)

# Minimum time between duplicate alert notifications (deduplication window)
ALERT_DEDUP_WINDOW_SECONDS = 300  # 5 minutes


class AlertService:
    """
    Service responsible for creating alerts, evaluating severity,
    and dispatching notifications through configured channels.
    Implements deduplication to prevent notification storms.
    """

    async def create_alert(
        self,
        db: AsyncSession,
        device_id: uuid.UUID,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        metric_value: Optional[float] = None,
        threshold_value: Optional[float] = None,
        anomaly_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Alert:
        """
        Create a new alert record and trigger notifications.
        Applies deduplication to suppress repeated notifications.

        Args:
            db: Active async database session.
            device_id: UUID of the affected device.
            alert_type: Type identifier for the alert.
            severity: Severity level (critical/high/medium/low/info).
            title: Short human-readable alert title.
            message: Full alert description.
            metric_value: The observed metric value that triggered the alert.
            threshold_value: The threshold that was exceeded.
            anomaly_score: AI-computed anomaly probability (0.0–1.0).
            metadata: Additional structured context.

        Returns:
            The created Alert ORM record.
        """
        alert = Alert(
            device_id=device_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            metric_value=metric_value,
            threshold_value=threshold_value,
            anomaly_score=anomaly_score,
            metadata=metadata or {},
        )
        db.add(alert)
        await db.flush()
        await db.refresh(alert)

        logger.warning(
            "Alert created",
            alert_id=str(alert.id),
            alert_type=alert_type,
            severity=severity,
            device_id=str(device_id),
        )

        # Publish to Redis for real-time WebSocket broadcast
        await redis_client.publish(
            "alerts:new",
            json.dumps({
                "alert_id": str(alert.id),
                "device_id": str(device_id),
                "alert_type": alert_type,
                "severity": severity,
                "title": title,
            }),
        )

        # Dispatch notifications asynchronously (don't block the response)
        asyncio.create_task(self._dispatch_notifications(alert))

        return alert

    async def _dispatch_notifications(self, alert: Alert) -> None:
        """
        Send email and webhook notifications for an alert.
        Checks deduplication before dispatching.
        """
        dedup_key = self._deduplication_key(alert)
        is_suppressed = await redis_client.exists(f"alert:suppressed:{alert.id}")
        is_duplicate = await redis_client.exists(f"alert:dedup:{dedup_key}")

        if is_suppressed or is_duplicate:
            logger.debug(
                "Alert notification suppressed (dedup)",
                alert_id=str(alert.id),
                alert_type=alert.alert_type,
            )
            return

        # Mark as notified within dedup window
        await redis_client.setex(
            f"alert:dedup:{dedup_key}", ALERT_DEDUP_WINDOW_SECONDS, "1"
        )

        tasks = []
        if settings.ALERT_EMAIL_RECIPIENTS and settings.SMTP_HOST:
            tasks.append(self._send_email_notification(alert))
        if settings.WEBHOOK_URL:
            tasks.append(self._send_webhook_notification(alert))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(
                        "Notification dispatch error",
                        error=str(result),
                        alert_id=str(alert.id),
                    )

    @staticmethod
    def _deduplication_key(alert: Alert) -> str:
        """Generate a deduplication key based on device + alert type."""
        raw = f"{alert.device_id}:{alert.alert_type}:{alert.severity}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    async def _send_email_notification(self, alert: Alert) -> None:
        """Send formatted HTML email alert to all configured recipients."""
        subject = f"[{alert.severity.upper()}] {alert.title}"
        body_html = f"""
        <html><body>
        <h2 style="color:{'#cc0000' if alert.severity == 'critical' else '#ff6600'};">
            {alert.title}
        </h2>
        <table>
            <tr><td><b>Severity:</b></td><td>{alert.severity.upper()}</td></tr>
            <tr><td><b>Type:</b></td><td>{alert.alert_type}</td></tr>
            <tr><td><b>Device ID:</b></td><td>{alert.device_id}</td></tr>
            <tr><td><b>Message:</b></td><td>{alert.message}</td></tr>
            <tr><td><b>Time:</b></td><td>{alert.created_at.isoformat()}</td></tr>
            {f'<tr><td><b>Value:</b></td><td>{alert.metric_value}</td></tr>' if alert.metric_value else ''}
            {f'<tr><td><b>Threshold:</b></td><td>{alert.threshold_value}</td></tr>' if alert.threshold_value else ''}
            {f'<tr><td><b>Anomaly Score:</b></td><td>{alert.anomaly_score:.3f}</td></tr>' if alert.anomaly_score else ''}
        </table>
        <hr/><p style="color:gray;font-size:12px;">
            Hospital Infrastructure Monitoring System<br/>
            Developed by: MERO:TG@QP4RM
        </p>
        </body></html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = ", ".join(settings.ALERT_EMAIL_RECIPIENTS)
        msg.attach(MIMEText(body_html, "html"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_TLS,
                timeout=10,
            )
            logger.info("Alert email sent", alert_id=str(alert.id))
        except Exception as exc:
            logger.error("Failed to send alert email", error=str(exc), alert_id=str(alert.id))
            raise

    async def _send_webhook_notification(self, alert: Alert) -> None:
        """Send alert payload to configured webhook URL with HMAC signature."""
        import hmac
        import hashlib

        payload = {
            "alert_id": str(alert.id),
            "device_id": str(alert.device_id),
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "metric_value": alert.metric_value,
            "threshold_value": alert.threshold_value,
            "anomaly_score": alert.anomaly_score,
            "created_at": alert.created_at.isoformat(),
            "source": "hospital-monitoring-system",
            "developer": "MERO:TG@QP4RM",
        }
        payload_bytes = json.dumps(payload).encode()

        headers = {"Content-Type": "application/json"}
        if settings.WEBHOOK_SECRET:
            signature = hmac.new(
                settings.WEBHOOK_SECRET.encode(),
                payload_bytes,
                hashlib.sha256,
            ).hexdigest()
            headers["X-HMS-Signature"] = f"sha256={signature}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.WEBHOOK_URL,
                    data=payload_bytes,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if not response.ok:
                        raise ValueError(
                            f"Webhook returned HTTP {response.status}"
                        )
            logger.info("Webhook notification sent", alert_id=str(alert.id))
        except Exception as exc:
            logger.error(
                "Failed to send webhook notification",
                error=str(exc),
                alert_id=str(alert.id),
            )
            raise
