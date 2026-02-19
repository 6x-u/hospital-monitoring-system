from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import engine, create_db_tables
from app.db.redis_client import redis_client
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.audit_log import AuditLogMiddleware
from app.services.recovery_engine import RecoveryEngine
from app.services.backup_service import BackupService
from app.ai.anomaly_detector import AnomalyDetectionEngine

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    logger.info(
        "Starting Hospital Infrastructure Monitoring System",
        version=settings.APP_VERSION,
        developer=settings.DEVELOPER_CREDIT,
        environment=settings.APP_ENV,
    )

    await create_db_tables()
    logger.info("Database tables verified/created")

    await redis_client.connect()
    logger.info("Redis connection established")

    ai_engine = AnomalyDetectionEngine()
    await ai_engine.initialize()
    app.state.ai_engine = ai_engine
    logger.info("AI anomaly detection engine initialized")

    recovery_engine = RecoveryEngine()
    await recovery_engine.start()
    app.state.recovery_engine = recovery_engine
    logger.info("Auto-recovery engine started")

    backup_service = BackupService()
    await backup_service.start_scheduler()
    app.state.backup_service = backup_service
    logger.info("Backup service scheduler started")

    logger.info(
        "System fully operational",
        developer=settings.DEVELOPER_CREDIT,
        api_prefix=settings.API_PREFIX,
    )

    yield

    logger.info("Initiating graceful shutdown...")
    await recovery_engine.stop()
    await backup_service.stop_scheduler()
    await redis_client.disconnect()
    await engine.dispose()
    logger.info("Shutdown complete")


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Enterprise-grade hospital infrastructure monitoring system "
            "with AI-powered anomaly detection, real-time alerting, "
            "and automated recovery. "
            f"Developed by: {settings.DEVELOPER_CREDIT}"
        ),
        version=settings.APP_VERSION,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        contact={
            "name": "System Developer",
            "url": "https://t.me/QP4RM",
        },
        license_info={
            "name": "Proprietary",
        },
        lifespan=lifespan,
    )

    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
    )
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(AuditLogMiddleware)

    application.include_router(api_router, prefix=settings.API_PREFIX)

    @application.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            exc_type=type(exc).__name__,
            exc_message=str(exc),
            path=str(request.url),
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred.",
                "request_id": request.headers.get("X-Request-ID", "unknown"),
            },
        )

    return application


app = create_application()
