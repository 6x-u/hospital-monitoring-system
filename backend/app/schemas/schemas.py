"""
Pydantic request/response schemas for the Hospital Monitoring System.
Provides validated data transfer objects for all API endpoints.
Developed by: MERO:TG@QP4RM
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ===========================================================================
# Base Schemas
# ===========================================================================

class BaseResponse(BaseModel):
    """Standard API response envelope."""
    model_config = {"from_attributes": True}


class PaginationParams(BaseModel):
    """Common pagination query parameters."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseResponse):
    """Paginated list response wrapper."""
    total: int
    page: int
    page_size: int
    items: List[Any]


# ===========================================================================
# Authentication Schemas
# ===========================================================================

class LoginRequest(BaseModel):
    """User login credentials."""
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=256)


class TokenResponse(BaseResponse):
    """JWT token pair response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request body."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout request — invalidates both tokens."""
    refresh_token: str


# ===========================================================================
# User Schemas
# ===========================================================================

class UserCreate(BaseModel):
    """Schema for creating a new user (admin only)."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    full_name: Optional[str] = Field(None, max_length=255)
    password: str = Field(..., min_length=12, max_length=256)
    role: str = Field(default="viewer", pattern=r"^(admin|engineer|viewer)$")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce minimum password complexity."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v):
            raise ValueError("Password must contain at least one special character.")
        return v


class UserUpdate(BaseModel):
    """Schema for updating user details."""
    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = Field(None, pattern=r"^(admin|engineer|viewer)$")
    is_active: Optional[bool] = None


class UserResponse(BaseResponse):
    """User details response (excludes sensitive fields)."""
    id: uuid.UUID
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class UserListResponse(PaginatedResponse):
    items: List[UserResponse]


# ===========================================================================
# Device Schemas
# ===========================================================================

class DeviceCreate(BaseModel):
    """Schema for registering a new monitored device."""
    hostname: str = Field(..., min_length=1, max_length=255)
    ip_address: str = Field(..., min_length=7, max_length=45)
    mac_address: Optional[str] = Field(None, max_length=17)
    device_type: str = Field(
        default="server",
        pattern=r"^(server|workstation|medical_device|network_switch|router|storage|other)$",
    )
    department: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    os_type: Optional[str] = Field(None, max_length=50)
    os_version: Optional[str] = Field(None, max_length=100)
    tags: List[str] = Field(default_factory=list)


class DeviceUpdate(BaseModel):
    """Schema for updating device information."""
    ip_address: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class DeviceIsolateRequest(BaseModel):
    """Request to isolate a device from the network."""
    reason: str = Field(..., min_length=10, max_length=1000)


class DeviceResponse(BaseResponse):
    """Device details response."""
    id: uuid.UUID
    hostname: str
    ip_address: str
    mac_address: Optional[str]
    device_type: str
    department: Optional[str]
    location: Optional[str]
    os_type: Optional[str]
    os_version: Optional[str]
    agent_version: Optional[str]
    is_active: bool
    is_isolated: bool
    isolation_reason: Optional[str]
    isolated_at: Optional[datetime]
    last_seen: Optional[datetime]
    tags: List[str]
    created_at: datetime
    updated_at: datetime


class DeviceListResponse(PaginatedResponse):
    items: List[DeviceResponse]


# ===========================================================================
# Metrics Schemas
# ===========================================================================

class DiskPartitionMetric(BaseModel):
    """Metrics for a single disk partition."""
    mount_point: str
    total_bytes: float
    used_bytes: float
    free_bytes: float
    usage_percent: float


class NetworkInterfaceMetric(BaseModel):
    """Metrics for a single network interface."""
    interface_name: str
    bytes_sent_per_sec: float
    bytes_recv_per_sec: float
    packets_sent: int
    packets_recv: int
    errors_in: int
    errors_out: int


class TemperatureSensorMetric(BaseModel):
    """Reading from a single temperature sensor."""
    sensor_label: str
    temperature_celsius: float
    high_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None


class MetricIngest(BaseModel):
    """Payload submitted by monitoring agents."""
    device_id: str
    collected_at: datetime
    cpu_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    cpu_frequency_mhz: Optional[float] = Field(None, ge=0.0)
    cpu_core_count: Optional[int] = Field(None, ge=1)
    cpu_load_avg_1m: Optional[float] = Field(None, ge=0.0)
    cpu_load_avg_5m: Optional[float] = Field(None, ge=0.0)
    cpu_load_avg_15m: Optional[float] = Field(None, ge=0.0)
    ram_total_bytes: Optional[float] = Field(None, ge=0.0)
    ram_used_bytes: Optional[float] = Field(None, ge=0.0)
    ram_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    swap_total_bytes: Optional[float] = Field(None, ge=0.0)
    swap_used_bytes: Optional[float] = Field(None, ge=0.0)
    swap_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    disk_partitions: List[DiskPartitionMetric] = Field(default_factory=list)
    disk_read_bytes_per_sec: Optional[float] = Field(None, ge=0.0)
    disk_write_bytes_per_sec: Optional[float] = Field(None, ge=0.0)
    disk_iops_read: Optional[float] = Field(None, ge=0.0)
    disk_iops_write: Optional[float] = Field(None, ge=0.0)
    network_interfaces: List[NetworkInterfaceMetric] = Field(default_factory=list)
    network_bytes_sent_per_sec: Optional[float] = Field(None, ge=0.0)
    network_bytes_recv_per_sec: Optional[float] = Field(None, ge=0.0)
    network_latency_ms: Optional[float] = Field(None, ge=0.0)
    network_packet_loss_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    temperature_sensors: List[TemperatureSensorMetric] = Field(default_factory=list)
    max_temperature_celsius: Optional[float] = None
    active_process_count: Optional[int] = Field(None, ge=0)
    zombie_process_count: Optional[int] = Field(None, ge=0)
    open_file_descriptors: Optional[int] = Field(None, ge=0)


class MetricResponse(BaseResponse):
    """Metric record response."""
    id: uuid.UUID
    device_id: uuid.UUID
    collected_at: datetime
    cpu_usage_percent: Optional[float]
    ram_usage_percent: Optional[float]
    disk_partitions: List[Dict[str, Any]]
    network_interfaces: List[Dict[str, Any]]
    temperature_sensors: List[Dict[str, Any]]
    max_temperature_celsius: Optional[float]
    network_latency_ms: Optional[float]
    network_packet_loss_percent: Optional[float]
    anomaly_score: Optional[float]
    is_anomalous: bool
    anomaly_features: Dict[str, Any]


class MetricSummary(BaseModel):
    """Aggregated metric summary for a device."""
    device_id: uuid.UUID
    hostname: str
    avg_cpu_percent: Optional[float]
    avg_ram_percent: Optional[float]
    max_temperature: Optional[float]
    avg_latency_ms: Optional[float]
    anomaly_count: int
    last_updated: Optional[datetime]


# ===========================================================================
# Alert Schemas
# ===========================================================================

class AlertAcknowledgeRequest(BaseModel):
    """Request to acknowledge an alert."""
    note: Optional[str] = Field(None, max_length=2000)


class AlertSuppressRequest(BaseModel):
    """Request to suppress duplicate notifications for an alert."""
    duration_minutes: int = Field(..., ge=1, le=10080)  # Max 1 week


class AlertResponse(BaseResponse):
    """Alert details response."""
    id: uuid.UUID
    device_id: uuid.UUID
    alert_type: str
    severity: str
    title: str
    message: str
    metric_value: Optional[float]
    threshold_value: Optional[float]
    anomaly_score: Optional[float]
    is_acknowledged: bool
    acknowledged_by: Optional[uuid.UUID]
    acknowledged_at: Optional[datetime]
    acknowledgment_note: Optional[str]
    is_resolved: bool
    resolved_at: Optional[datetime]
    email_sent: bool
    webhook_sent: bool
    notification_count: int
    is_suppressed: bool
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AlertListResponse(PaginatedResponse):
    items: List[AlertResponse]


# ===========================================================================
# Report Schemas
# ===========================================================================

class ReportGenerateRequest(BaseModel):
    """Request to generate a system report."""
    report_type: str = Field(
        ..., pattern=r"^(daily|weekly|monthly|custom|security|performance)$"
    )
    device_ids: Optional[List[uuid.UUID]] = None  # None = all devices
    start_date: datetime
    end_date: datetime
    include_charts: bool = True
    include_ai_insights: bool = True
    format: str = Field(default="pdf", pattern=r"^(pdf|json|csv)$")

    @model_validator(mode="after")
    def validate_date_range(self) -> "ReportGenerateRequest":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date.")
        if (self.end_date - self.start_date).days > 90:
            raise ValueError("Report date range cannot exceed 90 days.")
        return self


class ReportResponse(BaseResponse):
    """Report generation response."""
    report_id: uuid.UUID
    status: str
    download_url: Optional[str]
    generated_at: Optional[datetime]
    file_size_bytes: Optional[int]


# ===========================================================================
# WebSocket Schemas
# ===========================================================================

class WSMessage(BaseModel):
    """WebSocket message envelope."""
    event: str
    data: Dict[str, Any]
    timestamp: datetime


class SystemHealthResponse(BaseResponse):
    """Overall system health summary."""
    total_devices: int
    active_devices: int
    isolated_devices: int
    offline_devices: int
    critical_alerts: int
    unresolved_alerts: int
    avg_cpu_percent: Optional[float]
    avg_ram_percent: Optional[float]
    system_status: str  # "healthy" | "degraded" | "critical"
    developer: str = "MERO:TG@QP4RM"
