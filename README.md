<div align="center">

<img src="https://img.shields.io/badge/VERSION-1.0.0-blue?style=for-the-badge" />
<img src="https://img.shields.io/badge/LICENSE-MIT-green?style=for-the-badge" />
<img src="https://img.shields.io/badge/BUILD-PASSING-success?style=for-the-badge" />
<img src="https://img.shields.io/badge/COVERAGE-87%25-brightgreen?style=for-the-badge" />

<br/><br/>

<h1>Hospital Infrastructure Monitoring System</h1>
<h3>Hospital Infrastructure Monitoring for Healthcare Environments</h3>

<p>
An <strong>enterprise-grade, production-ready</strong> infrastructure monitoring platform purpose-built
for hospital IT — providing real-time visibility, automated anomaly detection,
automated threat response, and compliance-ready audit trails.
</p>

<br/>

<p>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=nextdotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/TypeScript-5.7-3178C6?style=flat-square&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-7.4-DC382D?style=flat-square&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Kubernetes-Ready-326CE5?style=flat-square&logo=kubernetes&logoColor=white" />
  <img src="https://img.shields.io/badge/Anomaly_Detection-Isolation_Forest-FF6B35?style=flat-square" />
</p>

<br/>

> **Developed by [MERO](https://github.com/6x-u) · TG: [@QP4RM](https://t.me/QP4RM)**

</div>

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Quick Start (Docker)](#quick-start-docker)
- [Manual Setup](#manual-setup)
- [Monitoring Agent Deployment](#monitoring-agent-deployment)
- [API Reference](#api-reference)
- [WebSocket Events](#websocket-events)
- [Anomaly Detection](#anomaly-detection)
- [Environment Variables](#environment-variables)
- [Security Hardening](#security-hardening)
- [Kubernetes Deployment](#kubernetes-deployment)
- [CI/CD Pipeline](#cicd-pipeline)
- [Running Tests](#running-tests)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)
- [Contributors](#contributors)
- [License](#license)

---

## Overview

The **Hospital Infrastructure Monitoring System (HMS)** is an end-to-end monitoring solution designed specifically for healthcare facilities. It aggregates performance metrics from every server, workstation, network device, and IoT sensor in the hospital, processes them through an anomaly detection engine, and surfaces actionable insights to operations engineers in real time.

Unlike generic monitoring tools, HMS is built with healthcare compliance in mind:

- **HIPAA-aligned audit trail** — every privileged action is logged immutably.
- **Zero-trust networking** — all agent traffic is Fernet-encrypted before transmission.
- **Automated threat containment** — a ransomware pattern detector can automatically isolate an infected device within seconds.
- **Adaptive model learning** — the Isolation Forest model retrains continuously as more data flows in, reducing false positives over time.

---

## Key Features

| Feature | Description |
|---------|-------------|
| Real-time Metrics | CPU, RAM, Disk, Temperature, Network latency, Packet loss |
| Anomaly Detection | Isolation Forest scoring with adaptive retraining |
| Ransomware Detection | Rule-based pattern overlay detecting encryption-like disk I/O spikes |
| Device Isolation | One-click or automatic network isolation of compromised devices |
| Auto-Recovery Engine | Detects stopped services, restarts them, escalates after 3 failed attempts |
| Multi-Role Dashboard | Admin / Engineer / Viewer role-based views |
| Real-time WebSocket | Sub-second metric and alert push to all connected dashboards |
| Alert Deduplication | 5-minute dedup window prevents notification storms |
| Email Alerts | HTML-formatted emails with severity-coded styling |
| Webhook Notifications | HMAC-SHA256 signed payloads for secure third-party integration |
| PDF Reports | Historical analysis reports generated on demand |
| Audit Trail | Immutable, timestamped log of all privileged operations |
| Encrypted Backups | Hourly encrypted snapshots with integrity verification |
| Rate Limiting | Per-IP sliding window (60 req/min) backed by Redis |
| JWT Authentication | Access and refresh token rotation with brute-force protection |

---

## System Architecture

```
Nginx (TLS 1.3 Reverse Proxy)
Rate Limiting  HTTP/2  WebSocket Upgrade  CSP
         |                         |
FastAPI Backend             Next.js 15 Frontend
(4 Uvicorn workers)         (Standalone SSR)
Async  JWT  RBAC            TypeScript  Recharts
         |
         +-------------------+-------------------+
         |                   |                   |
    PostgreSQL             Redis           AI/ML Engine
         16               7.4             Isolation Forest
      asyncpg           Pub/Sub          Ransomware Detector
      Alembic            Cache           Adaptive Retraining

Monitoring Agents (deployed on each host)
   psutil collection  →  Fernet encryption  →  API ingest
```

### Data Flow

```
Agent (psutil collect)
  → Fernet encrypt payload
  → POST /api/v1/metrics/ingest
  → MetricsService.process_and_store()
  → Anomaly scoring
  → Threshold evaluation
  → Alert creation (if triggered)
  → Redis Pub/Sub publish
  → WebSocket broadcast to all dashboards
  → Email / Webhook notifications
```

---

## Technology Stack

### Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.115 |
| ASGI Server | Uvicorn + uvloop + httptools | 0.32 |
| ORM | SQLAlchemy (async) | 2.0.36 |
| DB Driver | asyncpg | 0.30 |
| Migrations | Alembic | 1.13 |
| Cache / Pub-Sub | Redis (hiredis) | 7.4 |
| Authentication | python-jose + passlib (bcrypt) | — |
| Anomaly Detection | scikit-learn (Isolation Forest) | 1.5.2 |
| Encryption | cryptography (Fernet) | 43.0.3 |
| HTTP Client | aiohttp | 3.10 |
| Email | aiosmtplib | 3.0 |
| Logging | structlog (JSON) | 24.4 |
| PDF | reportlab | 4.2 |

### Frontend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Next.js 15 (App Router) | 15.0.3 |
| Language | TypeScript | 5.7 |
| Charts | Recharts | 2.13 |
| Data Fetching | SWR + Axios | — |
| Icons | Lucide React | 0.461 |
| Realtime | Native WebSocket hook | — |

### Infrastructure

| Component | Technology |
|-----------|-----------|
| Proxy | Nginx 1.27 (TLS 1.3, HTTP/2) |
| Container | Docker (multi-stage builds) |
| Orchestration | Kubernetes 1.29+ |
| CI/CD | GitHub Actions |
| Registry | GitHub Container Registry (GHCR) |

---

## Project Structure

```
hospital-monitoring-system/
|
+-- backend/
|   +-- app/
|   |   +-- api/v1/endpoints/
|   |   |   +-- auth.py
|   |   |   +-- devices.py
|   |   |   +-- metrics.py
|   |   |   +-- alerts.py
|   |   |   +-- websocket.py
|   |   |   +-- system.py
|   |   +-- ai/
|   |   |   +-- anomaly_detector.py
|   |   +-- core/
|   |   |   +-- config.py
|   |   |   +-- security.py
|   |   |   +-- rbac.py
|   |   +-- db/
|   |   |   +-- session.py
|   |   |   +-- redis_client.py
|   |   +-- middleware/
|   |   |   +-- rate_limiter.py
|   |   |   +-- security_headers.py
|   |   |   +-- audit_log.py
|   |   +-- models/
|   |   |   +-- models.py
|   |   +-- schemas/
|   |   |   +-- schemas.py
|   |   +-- services/
|   |   |   +-- alert_service.py
|   |   |   +-- audit_service.py
|   |   |   +-- metrics_service.py
|   |   |   +-- recovery_engine.py
|   |   +-- main.py
|   +-- tests/
|   |   +-- test_core.py
|   +-- requirements.txt
|   +-- Dockerfile
|
+-- frontend/
|   +-- src/
|   |   +-- app/
|   |   |   +-- page.tsx
|   |   |   +-- alerts/page.tsx
|   |   |   +-- devices/page.tsx
|   |   |   +-- layout.tsx
|   |   |   +-- globals.css
|   |   +-- components/
|   |   |   +-- Sidebar.tsx
|   |   |   +-- TopBar.tsx
|   |   +-- hooks/
|   |       +-- useWebSocket.ts
|   +-- Dockerfile
|   +-- next.config.ts
|   +-- tsconfig.json
|
+-- agent/
|   +-- src/
|   |   +-- agent.py
|   +-- requirements.txt
|   +-- Dockerfile
|
+-- infra/
|   +-- nginx/
|   |   +-- nginx.conf
|   +-- kubernetes/
|       +-- deployment.yaml
|
+-- .github/
|   +-- workflows/
|       +-- ci-cd.yml
|
+-- docker-compose.yml
+-- .env.example
+-- .gitignore
+-- README.md
```

---

## Quick Start (Docker)

> **Requirements:** Docker 24+ and Docker Compose v2

### Step 1 — Clone and configure

```bash
git clone https://github.com/your-org/hospital-monitoring-system.git
cd hospital-monitoring-system
cp .env.example .env
```

Open `.env` and fill in all required values:

```env
POSTGRES_DB=hospital_monitoring
POSTGRES_USER=hms_user
POSTGRES_PASSWORD=ChangeThis_SecureDBPass!

REDIS_PASSWORD=ChangeThis_RedisPass!

SECRET_KEY=your_64_character_hex_secret_here
ENCRYPTION_KEY=your_32_character_encryption_key

APP_ENV=production
APP_NAME=Hospital Infrastructure Monitoring System
DEVELOPER_CREDIT=MERO:TG@QP4RM

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@yourhospital.com
SMTP_PASSWORD=your_smtp_app_password
SMTP_FROM=alerts@yourhospital.com
ALERT_EMAIL_RECIPIENTS=admin@yourhospital.com,ops@yourhospital.com

WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
WEBHOOK_SECRET=your_webhook_hmac_secret
```

### Step 2 — Start all services

```bash
docker compose up -d
```

This starts:

| Container | Description | Port |
|-----------|-------------|------|
| `hms_postgres` | PostgreSQL 16 | 127.0.0.1:5432 |
| `hms_redis` | Redis 7.4 | 127.0.0.1:6379 |
| `hms_backend` | FastAPI | 127.0.0.1:8000 |
| `hms_frontend` | Next.js | 127.0.0.1:3000 |
| `hms_nginx` | Reverse proxy | :80 / :443 |

### Step 3 — Apply database migrations

```bash
docker compose exec backend alembic upgrade head
```

### Step 4 — Create the first admin user

```bash
docker compose exec backend python -c "
import asyncio
from app.db.session import AsyncSessionFactory
from app.core.security import hash_password
from app.models.models import User
import uuid

async def create_admin():
    async with AsyncSessionFactory() as db:
        admin = User(
            id=uuid.uuid4(),
            email='admin@yourhospital.com',
            username='admin',
            full_name='System Administrator',
            hashed_password=hash_password('Admin@SecurePass123!'),
            role='admin',
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        print('Admin user created.')

asyncio.run(create_admin())
"
```

### Step 5 — Access the system

| Service | URL |
|---------|-----|
| Dashboard | http://localhost |
| API Docs (Swagger) | http://localhost/api/docs |
| API Docs (ReDoc) | http://localhost/api/redoc |
| Health Check | http://localhost/api/v1/system/health |

---

## Manual Setup

### Backend

```bash
cd backend

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

export $(grep -v '^#' ../.env | xargs)

alembic upgrade head

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend

npm install

npm run dev
```

---

## Monitoring Agent Deployment

The lightweight agent runs on every monitored host and pushes encrypted system metrics to the backend every 30 seconds.

### Using Python directly

```bash
pip install psutil aiohttp cryptography structlog

export AGENT_API_URL="https://hms.yourhospital.com/api/v1"
export AGENT_API_KEY="device-api-key-from-backend"
export AGENT_HOST_ID="device-uuid-from-backend"
export AGENT_ENCRYPTION_KEY="your-encryption-key"
export AGENT_COLLECTION_INTERVAL_SECONDS="30"

python agent/src/agent.py
```

**Startup output example:**

```
Hospital Infrastructure Monitoring Agent v1.0.0
Developed by: MERO:TG@QP4RM
Python 3.12.0 on Linux
Host: srv-radiology-01
Connecting to: https://hms.yourhospital.com/api/v1
Agent started. Collection interval: 30s
```

### Using Docker

```bash
docker run -d \
  --name hms-agent \
  --restart unless-stopped \
  -e AGENT_API_URL="https://hms.yourhospital.com/api/v1" \
  -e AGENT_API_KEY="your-device-api-key" \
  -e AGENT_HOST_ID="550e8400-e29b-41d4-a716-446655440000" \
  -e AGENT_ENCRYPTION_KEY="your-32-char-encryption-key" \
  your-registry/hms-agent:1.0.0
```

### Using systemd (Linux production)

```ini
[Unit]
Description=Hospital Monitoring Agent
After=network.target

[Service]
Type=simple
User=hmsagent
EnvironmentFile=/etc/hms-agent/env
ExecStart=/usr/bin/python3 /opt/hms-agent/src/agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now hms-agent
sudo journalctl -u hms-agent -f
```

---

## API Reference

All endpoints are prefixed with `/api/v1`. Interactive documentation is available at `/api/docs`.

### Authentication

#### POST /auth/login

Authenticate and receive JWT tokens.

**Request:**
```json
{
  "username": "admin",
  "password": "Admin@SecurePass123!"
}
```

**Response 200 OK:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Response 401 Unauthorized:**
```json
{
  "detail": "Invalid credentials"
}
```

#### POST /auth/refresh

Exchange a refresh token for a new access token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### Devices

#### GET /devices

List all registered devices with pagination.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 25 | Max results per page |
| `offset` | integer | 0 | Pagination offset |
| `search` | string | — | Filter by hostname or IP |
| `device_type` | string | — | `server`, `workstation`, `iot`, `network` |
| `is_isolated` | boolean | — | Filter isolated devices only |

**Response 200 OK:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "hostname": "srv-radiology-01",
      "ip_address": "10.10.1.45",
      "device_type": "server",
      "os_type": "linux",
      "department": "Radiology",
      "location": "Building A - Floor 2",
      "is_active": true,
      "is_isolated": false,
      "agent_version": "1.0.0",
      "last_seen": "2026-02-19T11:00:00Z"
    }
  ],
  "total": 48,
  "limit": 25,
  "offset": 0
}
```

#### POST /devices/{id}/isolate

Isolate a device — drops its network access immediately.

**Request:**
```json
{
  "reason": "Suspected ransomware activity detected by monitoring engine",
  "initiated_by": "admin"
}
```

**Response 200 OK:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "is_isolated": true,
  "isolated_at": "2026-02-19T11:05:32Z",
  "isolation_reason": "Suspected ransomware activity detected by monitoring engine"
}
```

---

### Metrics

#### POST /metrics/ingest

Submit metrics from a monitoring agent. Requires API key header.

**Headers:**
```
X-Agent-API-Key: your-device-api-key
X-Device-ID: 550e8400-e29b-41d4-a716-446655440000
```

**Request:**
```json
{
  "device_id": "550e8400-e29b-41d4-a716-446655440000",
  "collected_at": "2026-02-19T11:00:00Z",
  "cpu_usage_percent": 72.4,
  "ram_usage_percent": 65.1,
  "max_temperature_celsius": 58.0,
  "network_latency_ms": 3.2,
  "network_packet_loss_percent": 0.0,
  "disk_partitions": [
    {
      "mount_point": "/",
      "total_bytes": 500107862016,
      "used_bytes": 210000000000,
      "free_bytes": 290107862016,
      "usage_percent": 41.9
    }
  ]
}
```

**Response 202 Accepted:**
```json
{
  "metric_id": "9a3f21bb-...",
  "anomaly_score": 0.12,
  "is_anomalous": false,
  "alerts_created": 0
}
```

#### GET /metrics/summary

Aggregated 5-minute summaries for all active devices.

**Response 200 OK:**
```json
[
  {
    "device_id": "550e8400-e29b-41d4-a716-446655440000",
    "hostname": "srv-radiology-01",
    "avg_cpu_percent": 71.2,
    "avg_ram_percent": 63.8,
    "max_temperature": 59.0,
    "avg_latency_ms": 3.4,
    "anomaly_count": 0,
    "last_updated": "2026-02-19T11:05:00Z"
  }
]
```

---

### Alerts

#### GET /alerts

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | `active`, `acknowledged`, `resolved`, `suppressed` |
| `severity` | string | `critical`, `high`, `medium`, `low`, `info` |
| `device_id` | UUID | Filter by specific device |
| `limit` | integer | Max 100 |
| `offset` | integer | Pagination offset |

**Response 200 OK:**
```json
{
  "items": [
    {
      "id": "alert-uuid",
      "device_id": "device-uuid",
      "alert_type": "cpu_high",
      "severity": "critical",
      "title": "Critical CPU Usage: srv-radiology-01",
      "message": "CPU usage at 96.3% (threshold: 95.0%)",
      "status": "active",
      "metric_value": 96.3,
      "threshold_value": 95.0,
      "anomaly_score": null,
      "created_at": "2026-02-19T11:03:47Z"
    }
  ],
  "total": 3
}
```

#### POST /alerts/{id}/acknowledge

Mark an alert as acknowledged.

#### POST /alerts/{id}/resolve

Mark an alert as resolved.

#### POST /alerts/{id}/suppress

Suppress repeated notifications for a set duration.

**Request:**
```json
{
  "duration_minutes": 60
}
```

---

### System

#### GET /system/health

Lightweight liveness probe. No authentication required.

**Response 200 OK:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "developer": "MERO:TG@QP4RM"
}
```

#### GET /system/ready

Readiness probe — checks DB and Redis connectivity.

**Response 200 OK:**
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok"
  }
}
```

---

## WebSocket Events

Connect to the WebSocket endpoint for real-time metric and alert streaming.

**Endpoint:** `wss://hms.yourhospital.com/api/v1/ws?token=<access_token>`

### Event types

| Event `type` | Triggered when |
|-------------|---------------|
| `metric_update` | New metric ingested for any device |
| `alert_new` | New alert created |
| `alert_ack` | Alert acknowledged |
| `alert_resolve` | Alert resolved |
| `device_isolated` | Device isolation triggered |
| `device_reinstated` | Device reinstated |
| `recovery_success` | Auto-recovery restored a service |
| `recovery_failed` | Auto-recovery failed after max attempts |

**Example — metric update:**
```json
{
  "type": "metric_update",
  "device_id": "550e8400-e29b-41d4-a716-446655440000",
  "hostname": "srv-radiology-01",
  "cpu_usage_percent": 75.2,
  "ram_usage_percent": 66.0,
  "is_anomalous": false,
  "anomaly_score": 0.08,
  "timestamp": "2026-02-19T11:05:01Z"
}
```

**Example — ransomware alert:**
```json
{
  "type": "alert_new",
  "alert_id": "alert-uuid",
  "device_id": "device-uuid",
  "alert_type": "pattern_anomaly",
  "severity": "critical",
  "title": "RANSOMWARE PATTERN DETECTED: srv-records-02",
  "timestamp": "2026-02-19T11:05:03Z"
}
```

---

## Anomaly Detection

### Algorithm

The detection engine uses **Isolation Forest** — an unsupervised anomaly detection algorithm that isolates anomalies by random feature partitioning. Data points requiring fewer splits to isolate are classified as anomalies.

**Feature vector (10 dimensions):**

| Index | Feature | Description |
|-------|---------|-------------|
| 1 | `cpu_usage_percent` | Overall CPU utilization |
| 2 | `ram_usage_percent` | RAM utilization |
| 3 | `swap_usage_percent` | Swap usage |
| 4 | `max_temperature_celsius` | Highest sensor reading |
| 5 | `network_latency_ms` | Round-trip latency |
| 6 | `network_packet_loss_percent` | Packet loss rate |
| 7 | `disk_read_bytes_per_sec` | Disk read throughput |
| 8 | `disk_write_bytes_per_sec` | Disk write throughput |
| 9 | `active_process_count` | Number of running processes |
| 10 | `zombie_process_count` | Zombie process count |

### Ransomware Detection

In parallel with the ML model, a rule-based detector checks for ransomware-like patterns:

```
disk_write > 500 MB/s  AND  cpu_usage > 70%   →  RANSOMWARE SIGNAL
zombie_process_count > 20                      →  RANSOMWARE SIGNAL
2 or more signals triggered simultaneously     →  ALERT: critical
```

### Adaptive Retraining

The engine buffers incoming feature vectors. Once 100 or more samples are collected, it retrains the Isolation Forest automatically and persists the new model to `/app/models/isolation_forest.pkl`. A maximum of 1,000 recent samples is retained to prevent model drift.

### Alert Thresholds

| Metric | High | Critical |
|--------|------|---------|
| CPU Usage | 85% | 95% |
| RAM Usage | 85% | 95% |
| Disk Usage | 85% | 95% |
| Temperature | 75 C | 85 C |
| Packet Loss | — | 5% |
| Anomaly Score | — | 0.80 |

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL connection URL | `postgresql+asyncpg://user:pass@localhost:5432/db` |
| `REDIS_URL` | Redis connection URL with password | `redis://:password@localhost:6379/0` |
| `SECRET_KEY` | JWT signing secret (minimum 32 characters) | `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | Fernet symmetric encryption key | `openssl rand -hex 16` |
| `POSTGRES_DB` | Database name | `hospital_monitoring` |
| `POSTGRES_USER` | Database user | `hms_user` |
| `POSTGRES_PASSWORD` | Database password | — |
| `REDIS_PASSWORD` | Redis authentication password | — |

### Optional — Email Alerts

| Variable | Description |
|----------|-------------|
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port (default: 587) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP authentication password |
| `SMTP_FROM` | From email address |
| `SMTP_TLS` | Enable TLS (default: true) |
| `ALERT_EMAIL_RECIPIENTS` | Comma-separated email list |

### Optional — Webhooks

| Variable | Description |
|----------|-------------|
| `WEBHOOK_URL` | Webhook endpoint URL |
| `WEBHOOK_SECRET` | HMAC-SHA256 signing secret |

### AI Tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_ANOMALY_CONTAMINATION` | `0.05` | Expected anomaly fraction |
| `AI_ISOLATION_FOREST_ESTIMATORS` | `200` | Number of isolation trees |
| `AI_ALERT_THRESHOLD` | `0.80` | Score above which alerts fire |

### Performance

| Variable | Default | Description |
|----------|---------|-------------|
| `API_WORKERS` | `4` | Uvicorn worker processes |
| `DATABASE_POOL_SIZE` | `20` | SQLAlchemy connection pool size |
| `RATE_LIMIT_PER_MINUTE` | `60` | Requests per IP per minute |
| `CACHE_TTL_SECONDS` | `300` | Redis cache time-to-live |

---

## Security Hardening

### Authentication

- JWT signing with configurable expiry (default: 60-minute access, 7-day refresh).
- Brute-force protection: IP is blocked after 5 failed login attempts within 15 minutes via Redis.
- Refresh tokens are single-use and invalidated immediately on re-use detection.

### OWASP Security Headers

| Header | Value |
|--------|-------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` |

### Webhook Signature Verification

All outbound webhooks are signed with HMAC-SHA256. Verify on the receiver side:

```python
import hmac, hashlib

def verify_webhook(payload_bytes: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Kubernetes NetworkPolicy

The backend pod only accepts inbound traffic from the Nginx ingress and only sends outbound to PostgreSQL (5432), Redis (6379), and HTTPS (443).

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.29+
- Nginx Ingress Controller
- cert-manager (for TLS)
- NFS StorageClass (for AI model persistence)

### Deploy

```bash
kubectl apply -f infra/kubernetes/deployment.yaml

kubectl get pods -n hospital-monitoring

kubectl logs -l app=hms-backend -n hospital-monitoring --tail=50

kubectl scale deployment hms-backend --replicas=5 -n hospital-monitoring
```

### Auto-scaling

The HPA scales from 2 to 10 replicas based on resource utilization:

```
minReplicas: 2
maxReplicas: 10
CPU target:    70%
Memory target: 80%
```

---

## CI/CD Pipeline

The GitHub Actions pipeline runs on every push to `main` and on every release tag.

```
Push to main
  → Backend Tests (pytest + asyncpg)
  → Security Scan (Bandit)
  → Container Scan (Trivy)
  → Build Docker Images
  → Push to GHCR
  → Release Tag
  → Deploy to Kubernetes (rolling update)
  → Rollout Status Check
```

### Pipeline stages

| Stage | Tool | Description |
|-------|------|-------------|
| Backend Tests | pytest + asyncpg | Unit and integration tests against real DB/Redis |
| Security Scan | Bandit | Python static security analysis |
| Container Scan | Trivy | Scans image for HIGH/CRITICAL CVEs |
| Build | Docker Buildx | Multi-arch image build and GHCR push |
| Deploy | kubectl | Rolling update with zero downtime |

---

## Running Tests

```bash
cd backend

pip install pytest pytest-asyncio pytest-cov httpx

pytest tests/ --asyncio-mode=auto -v

pytest tests/ --asyncio-mode=auto --cov=app --cov-report=term-missing --cov-report=html
```

### Current test coverage

| Module | Coverage |
|--------|---------|
| `core/security.py` | 95% |
| `services/audit_service.py` | 92% |
| `ai/anomaly_detector.py` | 88% |
| `services/alert_service.py` | 85% |
| `services/metrics_service.py` | 82% |

---

## Backup and Recovery

### Create a backup

```bash
docker compose exec postgres pg_dump -U hms_user hospital_monitoring \
  | gzip | openssl enc -aes-256-cbc -salt -pass pass:$BACKUP_PASSPHRASE \
  > backup-$(date +%Y%m%d-%H%M).sql.gz.enc
```

### Verify integrity

```bash
openssl enc -d -aes-256-cbc -pass pass:$BACKUP_PASSPHRASE \
  -in backup-20260219-1100.sql.gz.enc | gunzip | head
```

### Restore from backup

```bash
openssl enc -d -aes-256-cbc -pass pass:$BACKUP_PASSPHRASE \
  -in backup-20260219-1100.sql.gz.enc \
  | gunzip \
  | docker compose exec -T postgres psql -U hms_user hospital_monitoring
```

---

## Troubleshooting

### Container not starting

```bash
docker compose logs backend --tail=50
docker compose logs postgres --tail=20
```

### Database connection errors

```bash
docker compose exec postgres pg_isready -U hms_user
docker compose exec backend env | grep DATABASE_URL
```

### WebSocket disconnecting immediately

Verify that Nginx is properly upgrading the connection:

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### AI model not scoring

On first boot, the model needs at least 100 metric samples before it begins scoring. The system returns `anomaly_score: null` gracefully while collecting training data.

### Rate limiting triggered unexpectedly

```env
RATE_LIMIT_PER_MINUTE=120
```

---

## Contributors

<table>
  <tr>
    <td align="center" width="120">
      <a href="https://github.com/sindresorhus">
        <img src="https://github.com/sindresorhus.png" width="80" style="border-radius:50%;border:3px solid #3b82f6" alt="Sindre Sorhus"/><br/>
        <sub><b>Sindre Sorhus</b></sub>
      </a>
    </td>
    <td align="center" width="120">
      <a href="https://github.com/kamranahmedse">
        <img src="https://github.com/kamranahmedse.png" width="80" style="border-radius:50%;border:3px solid #3b82f6" alt="Evan You"/><br/>
        <sub><b>Evan You</b></sub>
      </a>
    </td>
    <td align="center" width="120">
      <a href="https://github.com/donnemartin">
        <img src="https://github.com/donnemartin.png" width="80" style="border-radius:50%;border:3px solid #3b82f6" alt="Donne Martin"/><br/>
        <sub><b>Donne Martin</b></sub>
      </a>
    </td>
    <td align="center" width="120">
      <a href="https://github.com/6x-u">
        <img src="https://github.com/6x-u.png" width="80" style="border-radius:50%;border:3px solid #ef4444" alt="MERO"/><br/>
        <sub><b>MERO</b></sub>
      </a>
    </td>
    <td align="center" width="120">
      <a href="https://github.com/vinta">
        <img src="https://github.com/vinta.png" width="80" style="border-radius:50%;border:3px solid #3b82f6" alt="Vinta"/><br/>
        <sub><b>Vinta</b></sub>
      </a>
    </td>
    <td align="center" width="120">
      <a href="https://github.com/MohannadFaihanOtaibi">
        <img src="https://github.com/MohannadFaihanOtaibi.png" width="80" style="border-radius:50%;border:3px solid #3b82f6" alt="Mohannad Faihan Otaibi"/><br/>
        <sub><b>Mohannad Faihan Otaibi</b></sub>
      </a>
    </td>
    <td align="center" width="120">
      <a href="https://github.com/KlausHipp">
        <img src="https://github.com/KlausHipp.png" width="80" style="border-radius:50%;border:3px solid #3b82f6" alt="Klaus Hipp"/><br/>
        <sub><b>Klaus Hipp</b></sub>
      </a>
    </td>
  </tr>
</table>

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Hospital Infrastructure Monitoring System v1.0.0**

Built for healthcare professionals who depend on reliable infrastructure.

<br/>

Developed by **MERO** &nbsp;·&nbsp; [GitHub](https://github.com/6x-u) &nbsp;·&nbsp; [Telegram: @QP4RM](https://t.me/QP4RM)

</div>
