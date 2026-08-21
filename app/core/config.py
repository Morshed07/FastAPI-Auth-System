import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Auth System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./sqlite.db"

    # JWT Authentication
    JWT_SECRET_KEY: str = "super_secret_access_key_change_in_production_123456789"
    JWT_REFRESH_SECRET_KEY: str = "super_secret_refresh_key_change_in_production_987654321"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis Configuration (matching running Redis on port 6389)
    REDIS_URL: str = "redis://localhost:6389/0"

    # OTP Configuration
    OTP_EXPIRE_SECONDS: int = 300  # 5 Minutes TTL
    OTP_COOLDOWN_SECONDS: int = 60  # 1 Minute rate limit between resends

    # Email / SMTP Configuration
    MAIL_USERNAME: str = "user@example.com"
    MAIL_PASSWORD: str = "password"
    MAIL_FROM: str = "noreply@example.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_FROM_NAME: str = "FastAPI Auth System"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    SUPPRESS_SEND: bool = True  # Set to True for dev testing without actual SMTP server

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
