"""
Application configuration management using Pydantic Settings.
Loads from environment variables with type validation and defaults.
Developed by: MERO:TG@QP4RM
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration class for the Hospital Monitoring System.
    All settings are loaded from environment variables with type validation.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "Hospital Infrastructure Monitoring System"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = Field(default="production")
    APP_DEBUG: bool = False
    DEVELOPER_CREDIT: str = "MERO:TG@QP4RM"
    API_PREFIX: str = "/api/v1"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    ALLOWED_HOSTS: List[str] = ["*"]

    # --- Security ---
    SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_KEY: str = Field(..., min_length=32)

    # --- Database ---
    DATABASE_URL: str = Field(...)
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800

    # --- Redis ---
    REDIS_URL: str = Field(...)
    REDIS_DB: int = 0
    CACHE_TTL_SECONDS: int = 300

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True

    # --- Rate Limiting ---
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    # --- Email ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_TLS: bool = True
    ALERT_EMAIL_RECIPIENTS: List[str] = []

    # --- Webhook ---
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_SECRET: Optional[str] = None

    # --- AI Configuration ---
    AI_ANOMALY_CONTAMINATION: float = 0.05
    AI_ISOLATION_FOREST_ESTIMATORS: int = 200
    AI_LSTM_SEQUENCE_LENGTH: int = 60
    AI_MODEL_RETRAIN_INTERVAL_HOURS: int = 24
    AI_ALERT_THRESHOLD: float = 0.85

    # --- Monitoring Agent ---
    AGENT_API_KEY: str = Field(default="")
    AGENT_COLLECTION_INTERVAL_SECONDS: int = 30

    # --- Backup ---
    BACKUP_ENCRYPTION_KEY: str = Field(default="")
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_S3_BUCKET: Optional[str] = None
    BACKUP_S3_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None

    @field_validator("ALERT_EMAIL_RECIPIENTS", mode="before")
    @classmethod
    def parse_email_recipients(cls, v: str | list) -> List[str]:
        if isinstance(v, str):
            return [e.strip() for e in v.split(",") if e.strip()]
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list) -> List[str]:
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except Exception:
                return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor for application settings."""
    return Settings()


settings: Settings = get_settings()
