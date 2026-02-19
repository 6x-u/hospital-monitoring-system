"""
Authentication API endpoints.
Handles login, token refresh, logout, and password change operations.
Developed by: MERO:TG@QP4RM
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    JWTHandler,
    PasswordHasher,
    TokenBlacklist,
    get_current_user_payload,
)
from app.core.config import settings
from app.db.session import get_db_session
from app.db.redis_client import redis_client
from app.models.models import User
from app.schemas.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
)
from app.services.audit_service import AuditService

logger = structlog.get_logger(__name__)
router = APIRouter()

# Brute-force protection: max failed attempts before lockout
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes


async def _check_brute_force(ip_address: str) -> None:
    """
    Check if an IP address is currently blocked due to brute-force attempts.
    Raises HTTP 429 if blocked.
    """
    block_key = f"auth:blocked:{ip_address}"
    if await redis_client.exists(block_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again in 15 minutes.",
        )


async def _record_failed_attempt(ip_address: str) -> None:
    """Increment failure counter for an IP and block if threshold is exceeded."""
    attempt_key = f"auth:attempts:{ip_address}"
    count = await redis_client.incr(attempt_key)
    await redis_client.expire(attempt_key, LOCKOUT_DURATION_SECONDS)

    if int(count) >= MAX_LOGIN_ATTEMPTS:
        block_key = f"auth:blocked:{ip_address}"
        await redis_client.setex(block_key, LOCKOUT_DURATION_SECONDS, "1")
        logger.warning(
            "IP blocked due to brute force attempts",
            ip=ip_address,
            attempts=count,
        )


async def _clear_failed_attempts(ip_address: str) -> None:
    """Clear failure counter after successful login."""
    await redis_client.delete(f"auth:attempts:{ip_address}")
    await redis_client.delete(f"auth:blocked:{ip_address}")


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT tokens",
    status_code=status.HTTP_200_OK,
)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Authenticate user with username and password.
    Returns access + refresh JWT token pair.
    Implements brute-force protection via IP-based rate limiting.
    """
    client_ip = request.client.host if request.client else "unknown"

    await _check_brute_force(client_ip)

    # Fetch user by username
    result = await db.execute(
        select(User).where(User.username == body.username)
    )
    user: Optional[User] = result.scalar_one_or_none()

    if not user or not PasswordHasher.verify_password(body.password, user.hashed_password):
        await _record_failed_attempt(client_ip)
        # Consistent error message regardless of whether user exists
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )

    # Check account lockout
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is temporarily locked. Try again later.",
        )

    # Successful login — clear failure counters
    await _clear_failed_attempts(client_ip)

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.flush()

    # Generate token pair
    access_token = JWTHandler.create_access_token(
        subject=str(user.id),
        role=user.role,
    )
    refresh_token = JWTHandler.create_refresh_token(
        subject=str(user.id),
        role=user.role,
    )

    await AuditService.log(
        db=db,
        user_id=user.id,
        action="auth.login",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent"),
        details={"username": user.username},
    )

    logger.info("User logged in successfully", user_id=str(user.id), role=user.role)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using refresh token",
)
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    The old refresh token is blacklisted on use (rotation).
    """
    payload = await JWTHandler.decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Provide a refresh token.",
        )

    user_id = payload.get("sub")
    role = payload.get("role")
    old_jti = payload.get("jti")

    # Blacklist the used refresh token (rotation security)
    if old_jti:
        await TokenBlacklist.add(old_jti, settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400)

    # Verify user still exists and is active
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user: Optional[User] = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive.",
        )

    new_access_token = JWTHandler.create_access_token(subject=user_id, role=role)
    new_refresh_token = JWTHandler.create_refresh_token(subject=user_id, role=role)

    logger.info("Tokens refreshed", user_id=user_id)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke tokens and end session",
)
async def logout(
    request: Request,
    body: LogoutRequest,
    payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Revoke the current access token and the provided refresh token.
    Both tokens are added to the Redis blacklist.
    """
    access_jti = payload.get("jti")
    access_exp = payload.get("exp", 0)
    now_ts = int(datetime.now(timezone.utc).timestamp())

    if access_jti:
        remaining = max(access_exp - now_ts, 0)
        await TokenBlacklist.add(access_jti, remaining + 60)

    # Decode and blacklist refresh token
    try:
        refresh_payload = await JWTHandler.decode_token(body.refresh_token)
        refresh_jti = refresh_payload.get("jti")
        if refresh_jti:
            await TokenBlacklist.add(
                refresh_jti, settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
            )
    except HTTPException:
        pass  # Refresh token may already be expired — still proceed

    await AuditService.log(
        db=db,
        user_id=uuid.UUID(payload["sub"]),
        action="auth.logout",
        resource_type="user",
        resource_id=payload["sub"],
        ip_address=request.client.host if request.client else None,
    )

    logger.info("User logged out", user_id=payload["sub"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
async def get_current_user(
    payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(payload["sub"]))
    )
    user: Optional[User] = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return UserResponse.model_validate(user)
