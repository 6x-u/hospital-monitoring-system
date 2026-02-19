"""
SQLAlchemy ORM models for the Hospital Infrastructure Monitoring System.
Defines all database tables with proper indexing, constraints, and relationships.
Developed by: MERO:TG@QP4RM
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Enum as SAEnum,
    JSON,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


def utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin for automatic created_at and updated_at timestamp columns."""
    created_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
        server_default=func.now(),
    )


class User(Base, TimestampMixin):
    """
    System users with role-based access control.
    Supports three roles: admin, engineer, viewer.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        SAEnum("admin", "engineer", "viewer", name="user_role_enum"),
        nullable=False,
        default="viewer",
    )
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    totp_secret = Column(String(32), nullable=True)  # For 2FA (optional)

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user", lazy="select")

    __table_args__ = (
        CheckConstraint("failed_login_attempts >= 0", name="check_failed_logins"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


class Device(Base, TimestampMixin):
    """
    Monitored devices/nodes in the hospital infrastructure.
    Represents servers, medical equipment controllers, and network nodes.
    """
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    hostname = Column(String(255), nullable=False, unique=True, index=True)
    ip_address = Column(String(45), nullable=False)  # Supports IPv6
    mac_address = Column(String(17), nullable=True)
    device_type = Column(
        SAEnum(
            "server", "workstation", "medical_device", "network_switch",
            "router", "storage", "other",
            name="device_type_enum",
        ),
        nullable=False,
        default="server",
    )
    department = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    os_type = Column(String(50), nullable=True)
    os_version = Column(String(100), nullable=True)
    agent_version = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_isolated = Column(Boolean, default=False, nullable=False)
    isolation_reason = Column(Text, nullable=True)
    isolated_at = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True, index=True)
    tags = Column(JSON, default=list, nullable=False)
    api_key_hash = Column(String(255), nullable=True)  # Hashed agent API key

    # Relationships
    metrics = relationship("Metric", back_populates="device", lazy="select",
                           cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="device", lazy="select",
                          cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_device_ip", "ip_address"),
        Index("idx_device_last_seen", "last_seen"),
        Index("idx_device_active_isolated", "is_active", "is_isolated"),
    )

    def __repr__(self) -> str:
        return f"<Device id={self.id} hostname={self.hostname}>"


class Metric(Base):
    """
    Time-series metrics collected from monitored devices.
    Optimized with composite indexes for time-based range queries.
    """
    __tablename__ = "metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    collected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )

    # CPU metrics
    cpu_usage_percent = Column(Float, nullable=True)
    cpu_frequency_mhz = Column(Float, nullable=True)
    cpu_core_count = Column(Integer, nullable=True)
    cpu_load_avg_1m = Column(Float, nullable=True)
    cpu_load_avg_5m = Column(Float, nullable=True)
    cpu_load_avg_15m = Column(Float, nullable=True)

    # Memory metrics
    ram_total_bytes = Column(Float, nullable=True)
    ram_used_bytes = Column(Float, nullable=True)
    ram_usage_percent = Column(Float, nullable=True)
    swap_total_bytes = Column(Float, nullable=True)
    swap_used_bytes = Column(Float, nullable=True)
    swap_usage_percent = Column(Float, nullable=True)

    # Disk metrics (JSON: list of per-partition stats)
    disk_partitions = Column(JSON, default=list, nullable=False)
    disk_read_bytes_per_sec = Column(Float, nullable=True)
    disk_write_bytes_per_sec = Column(Float, nullable=True)
    disk_iops_read = Column(Float, nullable=True)
    disk_iops_write = Column(Float, nullable=True)

    # Network metrics (JSON: list of per-interface stats)
    network_interfaces = Column(JSON, default=list, nullable=False)
    network_bytes_sent_per_sec = Column(Float, nullable=True)
    network_bytes_recv_per_sec = Column(Float, nullable=True)
    network_latency_ms = Column(Float, nullable=True)
    network_packet_loss_percent = Column(Float, nullable=True)

    # Temperature sensors (JSON: list of sensor readings)
    temperature_sensors = Column(JSON, default=list, nullable=False)
    max_temperature_celsius = Column(Float, nullable=True)

    # Process & service metrics
    active_process_count = Column(Integer, nullable=True)
    zombie_process_count = Column(Integer, nullable=True)
    open_file_descriptors = Column(Integer, nullable=True)

    # AI anomaly scores
    anomaly_score = Column(Float, nullable=True)
    is_anomalous = Column(Boolean, default=False, nullable=False)
    anomaly_features = Column(JSON, default=dict, nullable=False)

    # Relationships
    device = relationship("Device", back_populates="metrics")

    __table_args__ = (
        # Composite index for time-range queries per device
        Index("idx_metric_device_time", "device_id", "collected_at"),
        # Partial index for anomalous metrics
        Index(
            "idx_metric_anomalous",
            "is_anomalous",
            postgresql_where="is_anomalous = true",
        ),
    )

    def __repr__(self) -> str:
        return f"<Metric id={self.id} device_id={self.device_id} at={self.collected_at}>"


class Alert(Base, TimestampMixin):
    """
    System alerts generated by threshold violations or AI anomaly detection.
    Tracks severity, acknowledgment, and escalation state.
    """
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type = Column(
        SAEnum(
            "cpu_high", "ram_high", "disk_high", "temperature_high",
            "network_anomaly", "service_down", "ai_anomaly",
            "ransomware_pattern", "device_offline", "recovery_success",
            "recovery_failed", "security_breach",
            name="alert_type_enum",
        ),
        nullable=False,
    )
    severity = Column(
        SAEnum("critical", "high", "medium", "low", "info", name="alert_severity_enum"),
        nullable=False,
        default="medium",
        index=True,
    )
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    metric_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    anomaly_score = Column(Float, nullable=True)

    # State management
    is_acknowledged = Column(Boolean, default=False, nullable=False, index=True)
    acknowledged_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledgment_note = Column(Text, nullable=True)

    is_resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Notification tracking
    email_sent = Column(Boolean, default=False, nullable=False)
    webhook_sent = Column(Boolean, default=False, nullable=False)
    notification_count = Column(Integer, default=0, nullable=False)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    is_suppressed = Column(Boolean, default=False, nullable=False)

    metadata = Column(JSON, default=dict, nullable=False)

    # Relationships
    device = relationship("Device", back_populates="alerts")
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])

    __table_args__ = (
        Index("idx_alert_severity_ack", "severity", "is_acknowledged"),
        Index("idx_alert_device_created", "device_id", "created_at"),
        Index("idx_alert_unresolved", "is_resolved",
              postgresql_where="is_resolved = false"),
    )

    def __repr__(self) -> str:
        return (
            f"<Alert id={self.id} type={self.alert_type} severity={self.severity}>"
        )


class AuditLog(Base):
    """
    Immutable audit trail for all sensitive system operations.
    Records who did what, when, and from where.
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(36), nullable=True, index=True)
    status_code = Column(Integer, nullable=True)
    details = Column(JSON, default=dict, nullable=False)
    occurred_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        index=True,
    )

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_user_time", "user_id", "occurred_at"),
        Index("idx_audit_action_time", "action", "occurred_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action} user_id={self.user_id}>"
        )


class ServiceStatus(Base, TimestampMixin):
    """
    Tracks health status of monitored services on each device.
    Used by the auto-recovery engine to detect and respond to outages.
    """
    __tablename__ = "service_statuses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_name = Column(String(255), nullable=False, index=True)
    service_type = Column(
        SAEnum(
            "systemd", "docker", "process", "http_endpoint", "tcp_port",
            name="service_type_enum",
        ),
        nullable=False,
        default="process",
    )
    status = Column(
        SAEnum("running", "stopped", "degraded", "unknown", name="service_status_enum"),
        nullable=False,
        default="unknown",
        index=True,
    )
    response_time_ms = Column(Float, nullable=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    auto_recovery_enabled = Column(Boolean, default=True, nullable=False)
    recovery_command = Column(Text, nullable=True)

    device = relationship("Device", lazy="select")

    __table_args__ = (
        UniqueConstraint("device_id", "service_name", name="uq_device_service"),
        Index("idx_service_status_device", "device_id", "status"),
    )


class AIModel(Base, TimestampMixin):
    """
    Registry of AI models trained for anomaly detection.
    Stores model metadata and performance metrics.
    """
    __tablename__ = "ai_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_type = Column(
        SAEnum("isolation_forest", "lstm", name="ai_model_type_enum"),
        nullable=False,
    )
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )  # NULL = global model
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    model_path = Column(String(500), nullable=False)
    training_samples = Column(Integer, nullable=True)
    precision_score = Column(Float, nullable=True)
    recall_score = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    training_duration_seconds = Column(Float, nullable=True)
    last_retrained_at = Column(DateTime(timezone=True), nullable=True)
    hyperparameters = Column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("idx_ai_model_type_active", "model_type", "is_active"),
    )


class BackupRecord(Base, TimestampMixin):
    """Tracks all backup operations and their integrity status."""
    __tablename__ = "backup_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_type = Column(
        SAEnum("full", "incremental", "snapshot", name="backup_type_enum"),
        nullable=False,
    )
    storage_path = Column(String(1000), nullable=False)
    size_bytes = Column(Float, nullable=True)
    checksum_sha256 = Column(String(64), nullable=True)
    is_encrypted = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_result = Column(JSON, default=dict, nullable=False)
    status = Column(
        SAEnum("in_progress", "completed", "failed", "expired", name="backup_status_enum"),
        nullable=False,
        default="in_progress",
        index=True,
    )
    error_message = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_backup_status_created", "status", "created_at"),
    )
