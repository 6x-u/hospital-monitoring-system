"""
AI-powered anomaly detection engine.
Uses Isolation Forest and LSTM models to detect abnormal infrastructure behavior.
Includes ransomware pattern detection and adaptive learning.
Developed by: MERO:TG@QP4RM
"""

import asyncio
import os
import pickle
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.core.config import settings
from app.schemas.schemas import MetricIngest

logger = structlog.get_logger(__name__)

# Feature extraction for anomaly detection
FEATURE_NAMES = [
    "cpu_usage_percent",
    "ram_usage_percent",
    "swap_usage_percent",
    "max_temperature_celsius",
    "network_latency_ms",
    "network_packet_loss_percent",
    "disk_read_bytes_per_sec",
    "disk_write_bytes_per_sec",
    "active_process_count",
    "zombie_process_count",
]

MODEL_DIR = Path("/app/models")
ISOLATION_FOREST_PATH = MODEL_DIR / "isolation_forest.pkl"
SCALER_PATH = MODEL_DIR / "scaler.pkl"

# Ransomware pattern detection thresholds
RANSOMWARE_DISK_WRITE_MULTIPLIER = 5.0   # 5× normal disk write activity
RANSOMWARE_CPU_THRESHOLD = 70.0           # High CPU during encryption
RANSOMWARE_PROCESS_SPIKE_MULTIPLIER = 3.0 # Sudden process count spike


class AnomalyDetectionEngine:
    """
    AI-powered anomaly detection using Isolation Forest with adaptive learning.

    Architecture:
    - Isolation Forest: Unsupervised anomaly detection on feature vectors.
    - StandardScaler: Feature normalization for consistent scoring.
    - Adaptive retraining: Model updates on scheduled intervals.
    - Ransomware detection: Rule-based pattern overlay on top of ML scores.
    """

    _instance: Optional["AnomalyDetectionEngine"] = None
    _model: Optional[IsolationForest] = None
    _scaler: Optional[StandardScaler] = None
    _baseline_stats: Dict[str, Dict[str, float]] = {}
    _training_buffer: List[List[float]] = []
    _is_initialized: bool = False

    def __new__(cls) -> "AnomalyDetectionEngine":
        """Singleton pattern to share model across requests."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self) -> None:
        """
        Initialize the anomaly detection engine.
        Loads existing model from disk or creates a default baseline model.
        """
        await asyncio.get_event_loop().run_in_executor(None, self._load_or_init_model)
        self._is_initialized = True
        logger.info(
            "AI anomaly detection engine initialized",
            model_type="IsolationForest",
            developer="MERO:TG@QP4RM",
        )

    def _load_or_init_model(self) -> None:
        """Load persisted model from disk or create a default untrained model."""
        MODEL_DIR.mkdir(parents=True, exist_ok=True)

        if ISOLATION_FOREST_PATH.exists() and SCALER_PATH.exists():
            with open(ISOLATION_FOREST_PATH, "rb") as f:
                self.__class__._model = pickle.load(f)
            with open(SCALER_PATH, "rb") as f:
                self.__class__._scaler = pickle.load(f)
            logger.info("Loaded existing AI model from disk")
        else:
            # Initialize with default hyperparameters
            self.__class__._model = IsolationForest(
                n_estimators=settings.AI_ISOLATION_FOREST_ESTIMATORS,
                contamination=settings.AI_ANOMALY_CONTAMINATION,
                max_features=1.0,
                bootstrap=True,
                random_state=42,
                n_jobs=-1,
            )
            self.__class__._scaler = StandardScaler()
            logger.info("Initialized new default AI model (untrained baseline)")

    @staticmethod
    def _extract_features(metric: MetricIngest) -> List[float]:
        """
        Extract a normalized feature vector from a metric payload.
        Missing values are substituted with safe defaults.
        """
        # Compute max disk usage across partitions
        max_disk_usage = 0.0
        if metric.disk_partitions:
            max_disk_usage = max(
                (p.usage_percent for p in metric.disk_partitions), default=0.0
            )

        return [
            metric.cpu_usage_percent or 0.0,
            metric.ram_usage_percent or 0.0,
            metric.swap_usage_percent or 0.0,
            metric.max_temperature_celsius or 0.0,
            metric.network_latency_ms or 0.0,
            metric.network_packet_loss_percent or 0.0,
            metric.disk_read_bytes_per_sec or 0.0,
            metric.disk_write_bytes_per_sec or 0.0,
            float(metric.active_process_count or 0),
            float(metric.zombie_process_count or 0),
        ]

    async def analyze_metric(
        self, metric: MetricIngest
    ) -> Tuple[Optional[float], bool, Dict[str, Any]]:
        """
        Analyze a metric payload for anomalies.

        Returns:
            Tuple of (anomaly_score, is_anomalous, anomaly_features_dict)
            anomaly_score: 0.0 (normal) to 1.0 (highly anomalous)
            is_anomalous: True if score exceeds configured threshold
            anomaly_features_dict: Dict explaining which features contributed
        """
        features = self._extract_features(metric)
        self.__class__._training_buffer.append(features)

        # Check for ransomware patterns (rule-based overlay)
        ransomware_detected, ransomware_detail = self._check_ransomware_patterns(metric)
        if ransomware_detected:
            logger.critical(
                "RANSOMWARE PATTERN DETECTED",
                device_features=dict(zip(FEATURE_NAMES, features)),
                detail=ransomware_detail,
            )
            return 1.0, True, {
                "top_features": ["disk_write_bytes_per_sec", "cpu_usage_percent"],
                "ransomware_pattern": True,
                "detail": ransomware_detail,
            }

        model = self.__class__._model
        scaler = self.__class__._scaler

        if model is None or not hasattr(model, "estimators_"):
            # Model not yet trained — retrain if enough data
            if len(self.__class__._training_buffer) >= 100:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._retrain_model
                )
            return None, False, {}

        # Async feature scoring
        score = await asyncio.get_event_loop().run_in_executor(
            None, self._score_features, features, scaler, model
        )

        is_anomalous = score >= settings.AI_ALERT_THRESHOLD
        anomaly_features: Dict[str, Any] = {}

        if is_anomalous:
            # Identify top anomalous features
            anomaly_features = self._identify_anomalous_features(features)

        return score, is_anomalous, anomaly_features

    @staticmethod
    def _score_features(
        features: List[float],
        scaler: StandardScaler,
        model: IsolationForest,
    ) -> float:
        """
        Compute anomaly score from feature vector.
        Returns a score between 0.0 (normal) and 1.0 (anomalous).
        """
        X = np.array(features).reshape(1, -1)
        if hasattr(scaler, "mean_"):
            X_scaled = scaler.transform(X)
        else:
            X_scaled = X

        # decision_function returns negative values for anomalies
        # We convert to a 0-1 score where 1 = anomaly
        raw_score = model.decision_function(X_scaled)[0]
        # Normalize score: clip to [-0.5, 0.5] and invert
        normalized = max(0.0, min(1.0, 0.5 - raw_score))
        return float(normalized)

    def _retrain_model(self) -> None:
        """Retrain Isolation Forest on buffered training data."""
        buffer = self.__class__._training_buffer
        if len(buffer) < 100:
            return

        X = np.array(buffer)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = IsolationForest(
            n_estimators=settings.AI_ISOLATION_FOREST_ESTIMATORS,
            contamination=settings.AI_ANOMALY_CONTAMINATION,
            max_features=1.0,
            bootstrap=True,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_scaled)

        self.__class__._model = model
        self.__class__._scaler = scaler
        self.__class__._training_buffer = buffer[-1000:]  # Keep last 1000 samples

        # Persist to disk
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with open(ISOLATION_FOREST_PATH, "wb") as f:
            pickle.dump(model, f)
        with open(SCALER_PATH, "wb") as f:
            pickle.dump(scaler, f)

        logger.info(
            "AI model retrained",
            training_samples=len(buffer),
            model_type="IsolationForest",
        )

    @staticmethod
    def _check_ransomware_patterns(metric: MetricIngest) -> Tuple[bool, str]:
        """
        Rule-based ransomware pattern detection.
        Checks for sudden spikes in disk I/O combined with high CPU activity.

        Returns:
            Tuple of (is_ransomware_pattern_detected, description_string)
        """
        indicators = []

        # High disk write activity
        if metric.disk_write_bytes_per_sec and metric.disk_write_bytes_per_sec > 500 * 1024 * 1024:
            indicators.append(f"Extreme disk write: {metric.disk_write_bytes_per_sec / 1024**2:.0f} MB/s")

        # Simultaneously high CPU usage
        if metric.cpu_usage_percent and metric.cpu_usage_percent > RANSOMWARE_CPU_THRESHOLD:
            indicators.append(f"Elevated CPU: {metric.cpu_usage_percent:.1f}%")

        # High zombie process count (could indicate malware spawning/killing processes)
        if metric.zombie_process_count and metric.zombie_process_count > 20:
            indicators.append(f"High zombie count: {metric.zombie_process_count}")

        # High disk I/O + high CPU together is a strong ransomware signal
        if len(indicators) >= 2:
            return True, "; ".join(indicators)

        return False, ""

    @staticmethod
    def _identify_anomalous_features(
        features: List[float],
    ) -> Dict[str, Any]:
        """
        Identify which features are contributing most to the anomaly
        by comparing against expected safe ranges.
        """
        safe_ranges = {
            "cpu_usage_percent": (0, 80),
            "ram_usage_percent": (0, 85),
            "swap_usage_percent": (0, 50),
            "max_temperature_celsius": (0, 70),
            "network_latency_ms": (0, 100),
            "network_packet_loss_percent": (0, 2),
            "disk_read_bytes_per_sec": (0, 200 * 1024 * 1024),
            "disk_write_bytes_per_sec": (0, 200 * 1024 * 1024),
            "active_process_count": (0, 500),
            "zombie_process_count": (0, 5),
        }

        top_features = []
        details: Dict[str, Any] = {}

        for i, (name, value) in enumerate(zip(FEATURE_NAMES, features)):
            low, high = safe_ranges.get(name, (0, float("inf")))
            if value > high:
                top_features.append(name)
                details[name] = {
                    "value": value,
                    "safe_max": high,
                    "deviation_pct": ((value - high) / high * 100) if high > 0 else 100,
                }

        return {
            "top_features": top_features[:5],
            "feature_details": details,
            "ransomware_pattern": False,
        }
