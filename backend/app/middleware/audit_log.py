"""
Audit log middleware — captures request metadata for all API calls.
Automatically records HTTP method, path, status code, and timing.
Developed by: MERO:TG@QP4RM
"""

import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)

# Paths to skip logging (health checks, metrics scraping)
SKIP_LOG_PATHS = {"/api/v1/system/health", "/favicon.ico"}


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware that logs structured request/response metadata.
    Injects a unique X-Request-ID header for correlation tracing.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in SKIP_LOG_PATHS:
            return await call_next(request)

        request_id = str(uuid.uuid4())
        start_time = time.monotonic()

        # Bind request context to structlog for duration of request
        with structlog.contextvars.bound_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        ):
            response = await call_next(request)
            duration_ms = (time.monotonic() - start_time) * 1000

            log_fn = logger.warning if response.status_code >= 400 else logger.info
            log_fn(
                "HTTP request processed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

        response.headers["X-Request-ID"] = request_id
        return response
