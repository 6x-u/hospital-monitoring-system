"""
JWT-based authentication system with access/refresh token support.
Implements secure token creation, validation, and rotation.
Developed by: MERO:TG@QP4RM
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.db.redis_client import redis_client

logger = structlog.get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


class TokenBlacklist:
    """
    Manages blacklisted (revoked) JWT tokens using Redis.
    Tokens are blacklisted on logout or security events.
    """

    @staticmethod
    async def add(jti: str, expires_in: int) -> None:
        """Add a JTI (JWT ID) to the blacklist with TTL matching token expiry."""
        await redis_client.setex(f"blacklist:jti:{jti}", expires_in, "1")

    @staticmethod
    async def is_blacklisted(jti: str) -> bool:
        """Check if a JTI is in the blacklist."""
        return await redis_client.exists(f"blacklist:jti:{jti}") > 0


class PasswordHasher:
    """Secure password hashing and verification using bcrypt."""

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Hash a plaintext password."""
        return pwd_context.hash(plain_password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)


class JWTHandler:
    """
    Handles creation and validation of JWT access and refresh tokens.
    Each token includes a unique JTI for revocation support.
    """

    @staticmethod
    def create_access_token(
        subject: str,
        role: str,
        additional_claims: Optional[dict] = None,
    ) -> str:
        """
        Create a short-lived JWT access token.

        Args:
            subject: The user's unique identifier (UUID string).
            role: The user's role (admin/engineer/viewer).
            additional_claims: Optional extra claims to embed.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        jti = str(uuid4())

        payload = {
            "sub": subject,
            "role": role,
            "jti": jti,
            "iat": now,
            "exp": expire,
            "type": "access",
            "iss": "hospital-monitoring-system",
        }
        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def create_refresh_token(subject: str, role: str) -> str:
        """
        Create a long-lived JWT refresh token.

        Args:
            subject: The user's unique identifier (UUID string).
            role: The user's role.

        Returns:
            Encoded JWT string.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        jti = str(uuid4())

        payload = {
            "sub": subject,
            "role": role,
            "jti": jti,
            "iat": now,
            "exp": expire,
            "type": "refresh",
            "iss": "hospital-monitoring-system",
        }

        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    async def decode_token(token: str) -> dict:
        """
        Decode and validate a JWT token.

        Args:
            token: The JWT string to decode.

        Returns:
            The decoded payload dictionary.

        Raises:
            HTTPException: If the token is invalid, expired, or blacklisted.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_iss": True, "require": ["sub", "jti", "exp", "type"]},
                issuer="hospital-monitoring-system",
            )
        except JWTError as exc:
            logger.warning("JWT decode failed", error=str(exc))
            raise credentials_exception from exc

        jti = payload.get("jti")
        if not jti:
            raise credentials_exception

        if await TokenBlacklist.is_blacklisted(jti):
            logger.warning("Attempted use of blacklisted token", jti=jti)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked.",
            )

        return payload


async def get_current_user_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """
    FastAPI dependency: extracts and validates the current user's JWT payload.
    Raises 401 if no valid token is present.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = await JWTHandler.decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Use access token.",
        )
    return payload
