import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.services.audit_service import AuditService
from app.ai.anomaly_detector import AnomalyDetectionEngine


class TestSecurity:
    def test_password_hashing_and_verification(self):
        raw = "SecurePass123!"
        hashed = hash_password(raw)
        assert hashed != raw
        assert verify_password(raw, hashed)
        assert not verify_password("WrongPass", hashed)

    def test_access_token_encode_decode(self):
        payload = {"sub": str(uuid.uuid4()), "role": "admin"}
        token = create_access_token(payload)
        assert isinstance(token, str)
        decoded = decode_token(token)
        assert decoded["sub"] == payload["sub"]
        assert decoded["role"] == "admin"

    def test_token_is_unique_per_call(self):
        payload = {"sub": "test-user"}
        t1 = create_access_token(payload)
        t2 = create_access_token(payload)
        assert t1 != t2


class TestAuditService:
    @pytest.mark.asyncio
    async def test_log_creates_audit_entry(self):
        db = AsyncMock()
        db.flush = AsyncMock()

        result = await AuditService.log(
            db=db,
            action="device.isolate",
            user_id=uuid.uuid4(),
            resource_type="device",
            resource_id="dev-123",
            ip_address="192.168.1.1",
        )

        db.add.assert_called_once()
        db.flush.assert_called_once()
        assert result.action == "device.isolate"

    @pytest.mark.asyncio
    async def test_log_accepts_none_user_id(self):
        db = AsyncMock()
        db.flush = AsyncMock()

        result = await AuditService.log(
            db=db,
            action="system.startup",
            user_id=None,
        )
        assert result.user_id is None


class TestAnomalyDetector:
    def test_extract_features_returns_correct_length(self):
        from app.schemas.schemas import MetricIngest, DiskPartitionMetric
        metric = MetricIngest(
            device_id=uuid.uuid4(),
            collected_at=datetime.now(timezone.utc),
            cpu_usage_percent=55.0,
            ram_usage_percent=70.0,
            swap_usage_percent=10.0,
            max_temperature_celsius=60.0,
            network_latency_ms=5.0,
            network_packet_loss_percent=0.1,
            disk_read_bytes_per_sec=1024.0,
            disk_write_bytes_per_sec=2048.0,
            active_process_count=150,
            zombie_process_count=0,
            disk_partitions=[
                DiskPartitionMetric(mount_point="/", total_bytes=100, used_bytes=50, free_bytes=50, usage_percent=50.0)
            ],
        )
        features = AnomalyDetectionEngine._extract_features(metric)
        assert len(features) == 10

    def test_ransomware_detection_triggers_on_high_disk_write_and_cpu(self):
        from app.schemas.schemas import MetricIngest, DiskPartitionMetric
        metric = MetricIngest(
            device_id=uuid.uuid4(),
            collected_at=datetime.now(timezone.utc),
            cpu_usage_percent=95.0,
            disk_write_bytes_per_sec=600 * 1024 * 1024,
            zombie_process_count=0,
            disk_partitions=[
                DiskPartitionMetric(mount_point="/", total_bytes=100, used_bytes=80, free_bytes=20, usage_percent=80.0)
            ],
        )
        detected, detail = AnomalyDetectionEngine._check_ransomware_patterns(metric)
        assert detected is True
        assert len(detail) > 0

    def test_ransomware_detection_no_trigger_for_normal(self):
        from app.schemas.schemas import MetricIngest, DiskPartitionMetric
        metric = MetricIngest(
            device_id=uuid.uuid4(),
            collected_at=datetime.now(timezone.utc),
            cpu_usage_percent=30.0,
            disk_write_bytes_per_sec=1024 * 1024,
            zombie_process_count=0,
            disk_partitions=[],
        )
        detected, _ = AnomalyDetectionEngine._check_ransomware_patterns(metric)
        assert detected is False

    def test_identify_anomalous_features_detects_high_cpu(self):
        features = [99.0, 30.0, 0.0, 40.0, 5.0, 0.0, 0.0, 0.0, 100.0, 0.0]
        result = AnomalyDetectionEngine._identify_anomalous_features(features)
        assert "cpu_usage_percent" in result["top_features"]

    def test_anomaly_score_normalization(self):
        raw_scores = [-0.5, 0.0, 0.5]
        for raw in raw_scores:
            normalized = max(0.0, min(1.0, 0.5 - raw))
            assert 0.0 <= normalized <= 1.0


class TestDeduplicationKey:
    def test_key_is_consistent(self):
        from app.services.alert_service import AlertService
        alert = MagicMock()
        alert.device_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        alert.alert_type = "cpu_high"
        alert.severity = "critical"

        k1 = AlertService._deduplication_key(alert)
        k2 = AlertService._deduplication_key(alert)
        assert k1 == k2
        assert len(k1) == 16

    def test_different_types_produce_different_keys(self):
        from app.services.alert_service import AlertService
        device_id = uuid.uuid4()
        a1, a2 = MagicMock(), MagicMock()
        a1.device_id = a2.device_id = device_id
        a1.alert_type = "cpu_high"
        a2.alert_type = "ram_high"
        a1.severity = a2.severity = "critical"

        assert AlertService._deduplication_key(a1) != AlertService._deduplication_key(a2)


class TestMetricsThresholds:
    @pytest.mark.asyncio
    async def test_cpu_critical_alert_created(self):
        from app.services.metrics_service import MetricsService, CPU_CRITICAL_THRESHOLD
        from app.schemas.schemas import MetricIngest, DiskPartitionMetric

        service = MetricsService()
        service._alert_service = AsyncMock()
        service._alert_service.create_alert = AsyncMock()

        db = AsyncMock()
        device = MagicMock()
        device.id = uuid.uuid4()
        device.hostname = "srv-01"

        metric = MetricIngest(
            device_id=device.id,
            collected_at=datetime.now(timezone.utc),
            cpu_usage_percent=CPU_CRITICAL_THRESHOLD + 1.0,
            disk_partitions=[
                DiskPartitionMetric(mount_point="/", total_bytes=100, used_bytes=50, free_bytes=50, usage_percent=50.0)
            ],
        )

        await service._evaluate_thresholds(db, device, metric, MagicMock())

        service._alert_service.create_alert.assert_called()
        call_kwargs = service._alert_service.create_alert.call_args[1]
        assert call_kwargs["alert_type"] == "cpu_high"
        assert call_kwargs["severity"] == "critical"
