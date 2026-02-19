import asyncio
import base64
import hashlib
import json
import os
import platform
import socket
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import psutil
import structlog
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

AGENT_VERSION = "1.0.0"
DEVELOPER_CREDIT = "MERO:TG@QP4RM"

API_URL = os.environ.get("AGENT_API_URL", "http://localhost:8000/api/v1")
API_KEY = os.environ.get("AGENT_API_KEY", "")
DEVICE_ID = os.environ.get("AGENT_HOST_ID", "")
COLLECTION_INTERVAL = int(os.environ.get("AGENT_COLLECTION_INTERVAL_SECONDS", "30"))
ENCRYPTION_KEY = os.environ.get("AGENT_ENCRYPTION_KEY", "")
RECONNECT_DELAY = int(os.environ.get("AGENT_RECONNECT_DELAY_SECONDS", "5"))
MAX_RECONNECT_ATTEMPTS = int(os.environ.get("AGENT_MAX_RECONNECT_ATTEMPTS", "10"))

logger = structlog.get_logger(__name__)


def _print_startup_banner() -> None:
    banner = f"""
╔══════════════════════════════════════════════════════════════════╗
║     Hospital Infrastructure Monitoring Agent v{AGENT_VERSION}          ║
║                                                                  ║
║     Developed by: {DEVELOPER_CREDIT:<46}║
║     Python {platform.python_version():<14} on {platform.system():<26}║
║     Host: {socket.gethostname():<54}║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(banner, flush=True)


class EncryptionManager:
    def __init__(self, raw_key: str) -> None:
        if not raw_key:
            raise ValueError("Encryption key must not be empty")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"hospital_monitoring_system_salt",
            iterations=100000,
        )
        derived = base64.urlsafe_b64encode(kdf.derive(raw_key.encode()))
        self._fernet = Fernet(derived)

    def encrypt(self, data: str) -> str:
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()


class MetricsCollector:
    @staticmethod
    def collect() -> Dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        cpu_load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0)

        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        disk_partitions = []
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_partitions.append({
                    "mount_point": partition.mountpoint,
                    "total_bytes": float(usage.total),
                    "used_bytes": float(usage.used),
                    "free_bytes": float(usage.free),
                    "usage_percent": usage.percent,
                })
            except (PermissionError, OSError):
                continue

        disk_io = psutil.disk_io_counters()

        net_io = psutil.net_io_counters(pernic=True)
        network_interfaces = []
        for iface_name, stats in net_io.items():
            if iface_name == "lo":
                continue
            network_interfaces.append({
                "interface_name": iface_name,
                "bytes_sent_per_sec": float(stats.bytes_sent),
                "bytes_recv_per_sec": float(stats.bytes_recv),
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv,
                "errors_in": stats.errin,
                "errors_out": stats.errout,
            })

        net_global = psutil.net_io_counters()
        packet_loss = 0.0
        if net_global.packets_sent > 0:
            packet_loss = (net_global.errin + net_global.dropout) / net_global.packets_sent * 100

        temperature_sensors = []
        max_temp = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for sensor_name, readings in temps.items():
                    for reading in readings:
                        temperature_sensors.append({
                            "sensor_label": f"{sensor_name}:{reading.label or 'core'}",
                            "temperature_celsius": reading.current,
                            "high_threshold": reading.high,
                            "critical_threshold": reading.critical,
                        })
                        if max_temp is None or reading.current > max_temp:
                            max_temp = reading.current
        except AttributeError:
            pass

        process_count = len(psutil.pids())
        zombie_count = sum(
            1 for p in psutil.process_iter(["status"])
            if p.info.get("status") == psutil.STATUS_ZOMBIE
        )

        open_fds = None
        try:
            open_fds = psutil.Process(os.getpid()).num_fds()
        except (AttributeError, OSError):
            pass

        return {
            "device_id": DEVICE_ID,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "cpu_usage_percent": cpu_percent,
            "cpu_frequency_mhz": cpu_freq.current if cpu_freq else None,
            "cpu_core_count": psutil.cpu_count(logical=True),
            "cpu_load_avg_1m": cpu_load[0],
            "cpu_load_avg_5m": cpu_load[1],
            "cpu_load_avg_15m": cpu_load[2],
            "ram_total_bytes": float(mem.total),
            "ram_used_bytes": float(mem.used),
            "ram_usage_percent": mem.percent,
            "swap_total_bytes": float(swap.total),
            "swap_used_bytes": float(swap.used),
            "swap_usage_percent": swap.percent,
            "disk_partitions": disk_partitions,
            "disk_read_bytes_per_sec": float(disk_io.read_bytes) if disk_io else None,
            "disk_write_bytes_per_sec": float(disk_io.write_bytes) if disk_io else None,
            "disk_iops_read": float(disk_io.read_count) if disk_io else None,
            "disk_iops_write": float(disk_io.write_count) if disk_io else None,
            "network_interfaces": network_interfaces,
            "network_bytes_sent_per_sec": float(net_global.bytes_sent),
            "network_bytes_recv_per_sec": float(net_global.bytes_recv),
            "network_latency_ms": None,
            "network_packet_loss_percent": packet_loss,
            "temperature_sensors": temperature_sensors,
            "max_temperature_celsius": max_temp,
            "active_process_count": process_count,
            "zombie_process_count": zombie_count,
            "open_file_descriptors": open_fds,
        }


class MonitoringAgent:
    def __init__(self) -> None:
        self._collector = MetricsCollector()
        self._encryption = EncryptionManager(ENCRYPTION_KEY) if ENCRYPTION_KEY else None
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False
        self._consecutive_failures = 0

    async def start(self) -> None:
        _print_startup_banner()

        logger.info(
            "Agent starting",
            version=AGENT_VERSION,
            api_url=API_URL,
            device_id=DEVICE_ID,
            interval=COLLECTION_INTERVAL,
        )

        self._running = True

        connector = aiohttp.TCPConnector(ssl=True, limit=10)
        timeout = aiohttp.ClientTimeout(total=15)
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "X-Agent-API-Key": API_KEY,
                "X-Device-ID": DEVICE_ID,
                "X-Agent-Version": AGENT_VERSION,
                "User-Agent": f"HMS-Agent/{AGENT_VERSION}",
            },
        )

        try:
            await self._run_loop()
        finally:
            if self._session:
                await self._session.close()

    async def _run_loop(self) -> None:
        while self._running:
            cycle_start = time.monotonic()
            try:
                metrics = await asyncio.get_event_loop().run_in_executor(
                    None, self._collector.collect
                )
                await self._transmit(metrics)
                self._consecutive_failures = 0

            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._consecutive_failures += 1
                logger.error(
                    "Metric collection/transmission error",
                    error=str(exc),
                    consecutive_failures=self._consecutive_failures,
                )

                if self._consecutive_failures >= MAX_RECONNECT_ATTEMPTS:
                    logger.critical(
                        "Max reconnect attempts reached. Agent stopping.",
                        max_attempts=MAX_RECONNECT_ATTEMPTS,
                    )
                    break

                await asyncio.sleep(
                    min(RECONNECT_DELAY * self._consecutive_failures, 120)
                )
                continue

            elapsed = time.monotonic() - cycle_start
            sleep_time = max(0, COLLECTION_INTERVAL - elapsed)
            await asyncio.sleep(sleep_time)

    async def _transmit(self, metrics: Dict[str, Any]) -> None:
        payload_json = json.dumps(metrics)

        if self._encryption:
            encrypted = self._encryption.encrypt(payload_json)
            body = json.dumps({"encrypted": True, "payload": encrypted})
            headers = {"Content-Type": "application/json", "X-Encrypted": "true"}
        else:
            body = payload_json
            headers = {"Content-Type": "application/json"}

        url = f"{API_URL}/metrics/ingest"
        async with self._session.post(url, data=body, headers=headers) as response:
            if response.status == 202:
                result = await response.json()
                logger.info(
                    "Metrics transmitted",
                    is_anomalous=result.get("is_anomalous"),
                    anomaly_score=result.get("anomaly_score"),
                )
            else:
                error_body = await response.text()
                raise RuntimeError(
                    f"API returned HTTP {response.status}: {error_body}"
                )

    def stop(self) -> None:
        self._running = False


async def _main() -> None:
    agent = MonitoringAgent()
    loop = asyncio.get_event_loop()

    try:
        await agent.start()
    except KeyboardInterrupt:
        agent.stop()
        logger.info("Agent stopped by user")


if __name__ == "__main__":
    asyncio.run(_main())
