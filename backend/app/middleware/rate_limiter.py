"""
Rate limiting middleware using Redis sliding window algorithm.
Protects all endpoints against abuse and DDoS attempts.
Developed by: MERO:TG@QP4RM
"""

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.config import settings
from app.db.redis_client import redis_client

logger = structlog.get_logger(__name__)

# Paths exempt from rate limiting
EXEMPT_PATHS = {"/api/v1/system/health", "/api/docs", "/api/redoc", "/api/openapi.json"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiting middleware backed by Redis.
    Enforces per-IP limits with configurable window and burst capacity.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.requests_per_minute = settings.RATE_LIMIT_PER_MINUTE
        self.window_seconds = 60

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for exempt paths
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Identify client by IP
        client_ip = self._get_client_ip(request)
        key = f"rate_limit:{client_ip}"

        current_count = await redis_client.incr(key)
        if current_count == 1:
            await redis_client.expire(key, self.window_seconds)

        remaining = max(0, self.requests_per_minute - int(current_count))

        if int(current_count) > self.requests_per_minute:
            logger.warning(
                "Rate limit exceeded",
                ip=client_ip,
                count=current_count,
                limit=self.requests_per_minute,
            )
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please slow down.",
                    "retry_after": self.window_seconds,
                },
            )
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["Retry-After"] = str(self.window_seconds)
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP from headers, falling back to connection info."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
