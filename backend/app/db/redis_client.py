"""
Redis client wrapper for async operations.
Provides connection management, caching utilities, and pub/sub support.
Developed by: MERO:TG@QP4RM
"""

from typing import Any, Optional

import structlog
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError

from app.core.config import settings

logger = structlog.get_logger(__name__)


class RedisClient:
    """
    Async Redis client wrapper with connection pooling.
    Provides a clean interface for cache operations used across the system.
    """

    def __init__(self) -> None:
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    async def connect(self) -> None:
        """Initialize connection pool and verify connectivity."""
        self._pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=50,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        self._client = Redis(connection_pool=self._pool)
        await self._client.ping()
        logger.info("Redis connection pool established", url=settings.REDIS_URL)

    async def disconnect(self) -> None:
        """Close all Redis connections."""
        if self._client:
            await self._client.aclose()
        if self._pool:
            await self._pool.aclose()
        logger.info("Redis connection pool closed")

    def _get_client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client

    async def get(self, key: str) -> Optional[str]:
        """Get a string value from Redis."""
        try:
            return await self._get_client().get(key)
        except RedisError as exc:
            logger.error("Redis GET failed", key=key, error=str(exc))
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a string value with optional TTL in seconds."""
        try:
            if ttl:
                return await self._get_client().setex(key, ttl, str(value))
            return await self._get_client().set(key, str(value))
        except RedisError as exc:
            logger.error("Redis SET failed", key=key, error=str(exc))
            return False

    async def setex(self, key: str, ttl: int, value: Any) -> bool:
        """Set a value with expiry in seconds."""
        try:
            return await self._get_client().setex(key, ttl, str(value))
        except RedisError as exc:
            logger.error("Redis SETEX failed", key=key, error=str(exc))
            return False

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys. Returns count of deleted keys."""
        try:
            return await self._get_client().delete(*keys)
        except RedisError as exc:
            logger.error("Redis DELETE failed", keys=keys, error=str(exc))
            return 0

    async def exists(self, *keys: str) -> int:
        """Check if one or more keys exist. Returns count of existing keys."""
        try:
            return await self._get_client().exists(*keys)
        except RedisError as exc:
            logger.error("Redis EXISTS failed", keys=keys, error=str(exc))
            return 0

    async def incr(self, key: str) -> int:
        """Atomically increment a counter."""
        try:
            return await self._get_client().incr(key)
        except RedisError as exc:
            logger.error("Redis INCR failed", key=key, error=str(exc))
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on an existing key."""
        try:
            return await self._get_client().expire(key, ttl)
        except RedisError as exc:
            logger.error("Redis EXPIRE failed", key=key, error=str(exc))
            return False

    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a Redis channel for real-time events."""
        try:
            return await self._get_client().publish(channel, message)
        except RedisError as exc:
            logger.error("Redis PUBLISH failed", channel=channel, error=str(exc))
            return 0

    async def hset(self, name: str, mapping: dict) -> int:
        """Set multiple hash fields."""
        try:
            return await self._get_client().hset(name, mapping=mapping)
        except RedisError as exc:
            logger.error("Redis HSET failed", name=name, error=str(exc))
            return 0

    async def hgetall(self, name: str) -> dict:
        """Get all fields and values in a hash."""
        try:
            return await self._get_client().hgetall(name)
        except RedisError as exc:
            logger.error("Redis HGETALL failed", name=name, error=str(exc))
            return {}

    async def zadd(self, name: str, mapping: dict) -> int:
        """Add members to a sorted set."""
        try:
            return await self._get_client().zadd(name, mapping)
        except RedisError as exc:
            logger.error("Redis ZADD failed", name=name, error=str(exc))
            return 0

    async def zrangebyscore(
        self, name: str, min_score: float, max_score: float
    ) -> list:
        """Get members from a sorted set by score range."""
        try:
            return await self._get_client().zrangebyscore(name, min_score, max_score)
        except RedisError as exc:
            logger.error("Redis ZRANGEBYSCORE failed", name=name, error=str(exc))
            return []


# Singleton Redis client instance
redis_client = RedisClient()
