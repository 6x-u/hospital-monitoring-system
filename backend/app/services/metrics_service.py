"""
Metrics processing service.
Receives raw agent data, runs AI analysis, evaluates thresholds,
and generates alerts when thresholds are violated.
Developed by: MERO:TG@QP4RM
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import structlog
from sqlalchemy import select, and_, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Device, Metric
from app.schemas.schemas import MetricIngest, MetricSummary
from app.services.alert_service import AlertService

logger = structlog.get_logger(__name__)

# Alerting thresholds
CPU_CRITICAL_THRESHOLD = 95.0
CPU_HIGH_THRESHOLD = 85.0
RAM_CRITICAL_THRESHOLD = 95.0
RAM_HIGH_THRESHOLD = 85.0
DISK_CRITICAL_THRESHOLD = 95.0
DISK_HIGH_THRESHOLD = 85.0
TEMPERATURE_CRITICAL_CELSIUS = 85.0
TEMPERATURE_HIGH_CELSIUS = 75.0
PACKET_LOSS_HIGH_THRESHOLD = 5.0
AI_ANOMALY_ALERT_THRESHOLD = 0.80


class MetricsService:
    """
    Processes raw metric payloads from monitoring agents.
    Stores metrics, triggers AI analysis, and evaluates alert conditions.
    """

    def __init__(self) -> None:
        self._alert_service = AlertService()

    async def process_and_store(
        self,
        db: AsyncSession,
        device: Device,
        ingest_data: MetricIngest,
    ) -> Metric:
        """
        Process a metric payload, run AI analysis, persist to database,
        and evaluate threshold-based alert conditions.

        Args:
            db: Active async database session.
            device: The Device ORM instance sending the metrics.
            ingest_data: Validated metric payload from the agent.

        Returns:
            The created Metric ORM record.
        """
        # Convert Pydantic sub-models to plain dicts for JSON storage
        disk_partitions = [p.model_dump() for p in ingest_data.disk_partitions]
        network_interfaces = [n.model_dump() for n in ingest_data.network_interfaces]
        temperature_sensors = [t.model_dump() for t in ingest_data.temperature_sensors]

        # Run AI anomaly detection
        from app.ai.anomaly_detector import AnomalyDetectionEngine
        ai_engine = AnomalyDetectionEngine()
        anomaly_score, is_anomalous, anomaly_features = await ai_engine.analyze_metric(
            ingest_data
        )

        metric = Metric(
            device_id=device.id,
            collected_at=ingest_data.collected_at,
            cpu_usage_percent=ingest_data.cpu_usage_percent,
            cpu_frequency_mhz=ingest_data.cpu_frequency_mhz,
            cpu_core_count=ingest_data.cpu_core_count,
            cpu_load_avg_1m=ingest_data.cpu_load_avg_1m,
            cpu_load_avg_5m=ingest_data.cpu_load_avg_5m,
            cpu_load_avg_15m=ingest_data.cpu_load_avg_15m,
            ram_total_bytes=ingest_data.ram_total_bytes,
            ram_used_bytes=ingest_data.ram_used_bytes,
            ram_usage_percent=ingest_data.ram_usage_percent,
            swap_total_bytes=ingest_data.swap_total_bytes,
            swap_used_bytes=ingest_data.swap_used_bytes,
            swap_usage_percent=ingest_data.swap_usage_percent,
            disk_partitions=disk_partitions,
            disk_read_bytes_per_sec=ingest_data.disk_read_bytes_per_sec,
            disk_write_bytes_per_sec=ingest_data.disk_write_bytes_per_sec,
            disk_iops_read=ingest_data.disk_iops_read,
            disk_iops_write=ingest_data.disk_iops_write,
            network_interfaces=network_interfaces,
            network_bytes_sent_per_sec=ingest_data.network_bytes_sent_per_sec,
            network_bytes_recv_per_sec=ingest_data.network_bytes_recv_per_sec,
            network_latency_ms=ingest_data.network_latency_ms,
            network_packet_loss_percent=ingest_data.network_packet_loss_percent,
            temperature_sensors=temperature_sensors,
            max_temperature_celsius=ingest_data.max_temperature_celsius,
            active_process_count=ingest_data.active_process_count,
            zombie_process_count=ingest_data.zombie_process_count,
            open_file_descriptors=ingest_data.open_file_descriptors,
            anomaly_score=anomaly_score,
            is_anomalous=is_anomalous,
            anomaly_features=anomaly_features,
        )
        db.add(metric)
        await db.flush()

        # Evaluate thresholds and emit alerts
        await self._evaluate_thresholds(db, device, ingest_data, metric)
        if is_anomalous and anomaly_score and anomaly_score >= AI_ANOMALY_ALERT_THRESHOLD:
            await self._alert_service.create_alert(
                db=db,
                device_id=device.id,
                alert_type="ai_anomaly",
                severity="high" if anomaly_score < 0.95 else "critical",
                title=f"AI Anomaly Detected: {device.hostname}",
                message=(
                    f"AI engine detected anomalous behavior on {device.hostname}. "
                    f"Anomaly score: {anomaly_score:.3f}. "
                    f"Suspicious features: {', '.join(anomaly_features.get('top_features', []))}"
                ),
                anomaly_score=anomaly_score,
                metadata={"features": anomaly_features},
            )

        return metric

    async def _evaluate_thresholds(
        self,
        db: AsyncSession,
        device: Device,
        data: MetricIngest,
        metric: Metric,
    ) -> None:
        """Evaluate threshold conditions and create alerts where exceeded."""
        # CPU
        if data.cpu_usage_percent is not None:
            if data.cpu_usage_percent >= CPU_CRITICAL_THRESHOLD:
                await self._alert_service.create_alert(
                    db=db, device_id=device.id,
                    alert_type="cpu_high", severity="critical",
                    title=f"Critical CPU Usage: {device.hostname}",
                    message=f"CPU usage at {data.cpu_usage_percent:.1f}% "
                            f"(threshold: {CPU_CRITICAL_THRESHOLD}%)",
                    metric_value=data.cpu_usage_percent,
                    threshold_value=CPU_CRITICAL_THRESHOLD,
                )
            elif data.cpu_usage_percent >= CPU_HIGH_THRESHOLD:
                await self._alert_service.create_alert(
                    db=db, device_id=device.id,
                    alert_type="cpu_high", severity="high",
                    title=f"High CPU Usage: {device.hostname}",
                    message=f"CPU usage at {data.cpu_usage_percent:.1f}%",
                    metric_value=data.cpu_usage_percent,
                    threshold_value=CPU_HIGH_THRESHOLD,
                )

        # RAM
        if data.ram_usage_percent is not None:
            if data.ram_usage_percent >= RAM_CRITICAL_THRESHOLD:
                await self._alert_service.create_alert(
                    db=db, device_id=device.id,
                    alert_type="ram_high", severity="critical",
                    title=f"Critical RAM Usage: {device.hostname}",
                    message=f"RAM usage at {data.ram_usage_percent:.1f}%",
                    metric_value=data.ram_usage_percent,
                    threshold_value=RAM_CRITICAL_THRESHOLD,
                )

        # Disk (check all partitions)
        for partition in data.disk_partitions:
            if partition.usage_percent >= DISK_CRITICAL_THRESHOLD:
                await self._alert_service.create_alert(
                    db=db, device_id=device.id,
                    alert_type="disk_high", severity="critical",
                    title=f"Critical Disk Usage: {device.hostname}",
                    message=f"Disk {partition.mount_point} at {partition.usage_percent:.1f}%",
                    metric_value=partition.usage_percent,
                    threshold_value=DISK_CRITICAL_THRESHOLD,
                    metadata={"mount_point": partition.mount_point},
                )

        # Temperature
        if data.max_temperature_celsius is not None:
            if data.max_temperature_celsius >= TEMPERATURE_CRITICAL_CELSIUS:
                await self._alert_service.create_alert(
                    db=db, device_id=device.id,
                    alert_type="temperature_high", severity="critical",
                    title=f"Critical Temperature: {device.hostname}",
                    message=f"Temperature at {data.max_temperature_celsius:.1f}°C",
                    metric_value=data.max_temperature_celsius,
                    threshold_value=TEMPERATURE_CRITICAL_CELSIUS,
                )

        # Network packet loss
        if (
            data.network_packet_loss_percent is not None
            and data.network_packet_loss_percent >= PACKET_LOSS_HIGH_THRESHOLD
        ):
            await self._alert_service.create_alert(
                db=db, device_id=device.id,
                alert_type="network_anomaly", severity="high",
                title=f"High Packet Loss: {device.hostname}",
                message=f"Packet loss at {data.network_packet_loss_percent:.1f}%",
                metric_value=data.network_packet_loss_percent,
                threshold_value=PACKET_LOSS_HIGH_THRESHOLD,
            )

    async def get_all_device_summaries(
        self, db: AsyncSession
    ) -> List[MetricSummary]:
        """
        Generate metric summaries for all active devices
        aggregated over the last 5 minutes.
        """
        from app.models.models import Device as DeviceModel

        five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)

        result = await db.execute(
            select(DeviceModel).where(DeviceModel.is_active == True)
        )
        devices = result.scalars().all()
        summaries: List[MetricSummary] = []

        for device in devices:
            metrics_result = await db.execute(
                select(
                    sa_func.avg(Metric.cpu_usage_percent).label("avg_cpu"),
                    sa_func.avg(Metric.ram_usage_percent).label("avg_ram"),
                    sa_func.max(Metric.max_temperature_celsius).label("max_temp"),
                    sa_func.avg(Metric.network_latency_ms).label("avg_latency"),
                    sa_func.count(Metric.id).filter(Metric.is_anomalous == True).label("anomaly_count"),
                    sa_func.max(Metric.collected_at).label("last_updated"),
                ).where(
                    and_(
                        Metric.device_id == device.id,
                        Metric.collected_at >= five_min_ago,
                    )
                )
            )
            row = metrics_result.one()

            summaries.append(MetricSummary(
                device_id=device.id,
                hostname=device.hostname,
                avg_cpu_percent=float(row.avg_cpu) if row.avg_cpu else None,
                avg_ram_percent=float(row.avg_ram) if row.avg_ram else None,
                max_temperature=float(row.max_temp) if row.max_temp else None,
                avg_latency_ms=float(row.avg_latency) if row.avg_latency else None,
                anomaly_count=row.anomaly_count or 0,
                last_updated=row.last_updated,
            ))

        return summaries
