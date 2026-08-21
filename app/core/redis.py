import redis.asyncio as aioredis
from typing import AsyncGenerator
from app.core.config import settings

# Global Redis client instance
redis_client: aioredis.Redis | None = None


async def init_redis() -> None:
    """Initialize Redis connection pool."""
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            protocol=2
        )


async def close_redis() -> None:
    """Close Redis connection pool."""
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None


def get_redis() -> aioredis.Redis:
    """Returns initialized Redis client."""
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized. Call init_redis() first.")
    return redis_client


class RedisOTPService:

    @staticmethod
    async def store_otp(email: str, otp: str, ttl: int = settings.OTP_EXPIRE_SECONDS) -> None:
        """Stores OTP in Redis with 5-minute (300s) TTL."""
        client = get_redis()
        key = f"otp:{email.lower()}"
        await client.set(key, otp, ex=ttl)

    @staticmethod
    async def get_otp(email: str) -> str | None:
        """Retrieves active OTP for email."""
        client = get_redis()
        key = f"otp:{email.lower()}"
        return await client.get(key)

    @staticmethod
    async def delete_otp(email: str) -> None:
        """Deletes OTP from Redis once verified."""
        client = get_redis()
        key = f"otp:{email.lower()}"
        await client.delete(key)

    @staticmethod
    async def set_cooldown(email: str, ttl: int = settings.OTP_COOLDOWN_SECONDS) -> None:
        """Sets rate-limiting cooldown key (default 60s) to prevent spamming OTP requests."""
        client = get_redis()
        key = f"otp_cooldown:{email.lower()}"
        await client.set(key, "1", ex=ttl)

    @staticmethod
    async def is_cooldown_active(email: str) -> bool:
        """Checks if OTP resend cooldown is active."""
        client = get_redis()
        key = f"otp_cooldown:{email.lower()}"
        return await client.exists(key) > 0


class RedisTokenService:

    @staticmethod
    async def blacklist_token(jti: str, ttl_seconds: int) -> None:
        """Blacklists a refresh token jti until its expiration."""
        client = get_redis()
        key = f"blacklist:{jti}"
        await client.set(key, "revoked", ex=ttl_seconds)

    @staticmethod
    async def is_token_blacklisted(jti: str) -> bool:
        """Checks if a refresh token jti is blacklisted."""
        client = get_redis()
        key = f"blacklist:{jti}"
        return await client.exists(key) > 0
