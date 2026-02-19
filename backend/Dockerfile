# =============================================================================
# Hospital Infrastructure Monitoring System — Backend Dockerfile
# Production-ready multi-stage build
# Developed by: MERO:TG@QP4RM
# =============================================================================

# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a venv for isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# --- Stage 2: Production Image ---
FROM python:3.12-slim AS production

LABEL maintainer="MERO:TG@QP4RM"
LABEL app="hospital-monitoring-backend"
LABEL version="1.0.0"

WORKDIR /app

# Install runtime-only dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r hmsuser && useradd -r -g hmsuser -s /bin/false hmsuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create required directories
RUN mkdir -p /app/models /var/log/hms && \
    chown -R hmsuser:hmsuser /app /var/log/hms

# Copy application source
COPY --chown=hmsuser:hmsuser . .

# Switch to non-root user
USER hmsuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/system/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--no-access-log", \
     "--proxy-headers"]
