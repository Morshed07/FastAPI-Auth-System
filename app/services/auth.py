from datetime import datetime, timezone
from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.core.redis import RedisOTPService, RedisTokenService
from app.services.email import EmailQueueService, generate_otp
from app.models.users import User
from app.schemas.auth import (
    UserRegister,
    VerifyOTP,
    ResendOTP,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
    ChangePassword,
)


class AuthService:

    @staticmethod
    async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
        """Internal helper to fetch user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @classmethod
    async def register(
        cls,
        db: AsyncSession,
        background_tasks: BackgroundTasks,
        user_in: UserRegister
    ) -> MessageResponse:
        """Registers user, generates 5-min TTL OTP in Redis, and queues verification email."""
        existing_user = await cls._get_user_by_email(db, user_in.email)

        if existing_user:
            if existing_user.is_verified:
                raise ValueError("Email already registered and verified.")
            else:
                # Update existing unverified user's name & password
                existing_user.full_name = user_in.full_name
                existing_user.password = hash_password(user_in.password)
                await db.commit()
                user = existing_user
        else:
            # Create new user record (unverified)
            hashed_pwd = hash_password(user_in.password)
            user = User(
                full_name=user_in.full_name,
                email=user_in.email,
                password=hashed_pwd,
                is_verified=False,
                is_active=True,
                role="user"
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # Check rate-limiting cooldown
        if await RedisOTPService.is_cooldown_active(user.email):
            return MessageResponse(
                message="User registered. An OTP code was already sent recently. Please wait 60s before requesting another."
            )

        # Generate OTP & Store in Redis with 5-minute (300s) TTL
        otp = generate_otp()
        await RedisOTPService.store_otp(user.email, otp, settings.OTP_EXPIRE_SECONDS)
        await RedisOTPService.set_cooldown(user.email, settings.OTP_COOLDOWN_SECONDS)

        # Enqueue Email Sending Task
        EmailQueueService.send_verification_otp(
            background_tasks=background_tasks,
            email=user.email,
            otp=otp,
            full_name=user.full_name
        )

        return MessageResponse(
            message="Registration successful. Please check your email for the 6-digit OTP code."
        )

    @classmethod
    async def verify_otp(cls, db: AsyncSession, verify_in: VerifyOTP) -> TokenResponse:
        """Verifies OTP from Redis, marks user is_verified=True, and returns JWT access + refresh tokens."""
        # 1. Fetch OTP from Redis layer
        stored_otp = await RedisOTPService.get_otp(verify_in.email)
        if not stored_otp or stored_otp != verify_in.otp:
            raise ValueError("Invalid or expired OTP code")

        # 2. Fetch user
        user = await cls._get_user_by_email(db, verify_in.email)
        if not user:
            raise ValueError("User account not found")

        # 3. Clean up OTP in Redis
        await RedisOTPService.delete_otp(verify_in.email)

        # 4. Mark user verified in DB
        user.is_verified = True
        await db.commit()
        await db.refresh(user)

        # 5. Generate JWT tokens
        access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        })
        refresh_token, _ = create_refresh_token({
            "sub": str(user.id)
        })

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    @classmethod
    async def resend_otp(
        cls,
        db: AsyncSession,
        background_tasks: BackgroundTasks,
        resend_in: ResendOTP
    ) -> MessageResponse:
        """Resends a new 5-minute OTP with 60-second Redis rate-limit cooldown."""
        user = await cls._get_user_by_email(db, resend_in.email)
        if not user:
            raise ValueError("User with this email does not exist")

        if user.is_verified:
            return MessageResponse(message="Account is already verified.")

        # Check rate-limiting cooldown in Redis
        if await RedisOTPService.is_cooldown_active(user.email):
            raise ValueError("Please wait 60 seconds before requesting another OTP code.")

        # Generate & store new OTP in Redis (5 min TTL)
        otp = generate_otp()
        await RedisOTPService.store_otp(user.email, otp, settings.OTP_EXPIRE_SECONDS)
        await RedisOTPService.set_cooldown(user.email, settings.OTP_COOLDOWN_SECONDS)

        # Queue Email Sending
        EmailQueueService.send_verification_otp(
            background_tasks=background_tasks,
            email=user.email,
            otp=otp,
            full_name=user.full_name
        )

        return MessageResponse(message="A new OTP code has been sent to your email.")

    @classmethod
    async def login(cls, db: AsyncSession, login_in: UserLogin) -> TokenResponse:
        """Authenticates user email and password, returning JWT access & refresh tokens."""
        user = await cls._get_user_by_email(db, login_in.email)
        if not user or not verify_password(login_in.password, user.password):
            raise ValueError("Invalid email or password")

        if not user.is_verified:
            raise ValueError("Account is not verified. Please verify your email using OTP first.")

        if not user.is_active:
            raise ValueError("Account is disabled. Please contact support.")

        access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        })
        refresh_token, _ = create_refresh_token({
            "sub": str(user.id)
        })

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    @classmethod
    async def refresh_tokens(cls, refresh_in: RefreshTokenRequest) -> TokenResponse:
        """Issues new access token using a valid, non-blacklisted refresh token."""
        try:
            payload = decode_token(refresh_in.refresh_token, settings.JWT_REFRESH_SECRET_KEY)
        except ValueError as e:
            raise ValueError(f"Invalid refresh token: {str(e)}")

        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")

        jti = payload.get("jti")
        if not jti or await RedisTokenService.is_token_blacklisted(jti):
            raise ValueError("Refresh token has been revoked")

        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token payload")

        # Create new access token
        access_token = create_access_token({"sub": user_id})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_in.refresh_token,
            token_type="bearer"
        )

    @classmethod
    async def logout(cls, refresh_in: RefreshTokenRequest) -> MessageResponse:
        """Revokes refresh token by storing its JTI in Redis blacklist until expiration."""
        try:
            payload = decode_token(refresh_in.refresh_token, settings.JWT_REFRESH_SECRET_KEY)
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                now_ts = int(datetime.now(timezone.utc).timestamp())
                ttl_seconds = max(exp - now_ts, 1)
                await RedisTokenService.blacklist_token(jti, ttl_seconds)
        except ValueError:
            pass  # Token is already expired or invalid

        return MessageResponse(message="Successfully logged out")

    @classmethod
    async def forgot_password(
        cls,
        db: AsyncSession,
        background_tasks: BackgroundTasks,
        forgot_in: ForgotPasswordRequest
    ) -> MessageResponse:
        """Generates password reset OTP in Redis with 5-minute TTL and queues email."""
        user = await cls._get_user_by_email(db, forgot_in.email)
        if not user:
            # Generic message to prevent email enumeration attacks
            return MessageResponse(
                message="If an account exists with this email, a reset OTP code has been sent."
            )

        if await RedisOTPService.is_cooldown_active(user.email):
            return MessageResponse(
                message="A reset code was recently sent. Please wait 60s before requesting another."
            )

        otp = generate_otp()
        await RedisOTPService.store_otp(user.email, otp, settings.OTP_EXPIRE_SECONDS)
        await RedisOTPService.set_cooldown(user.email, settings.OTP_COOLDOWN_SECONDS)

        EmailQueueService.send_password_reset_otp(
            background_tasks=background_tasks,
            email=user.email,
            otp=otp,
            full_name=user.full_name
        )

        return MessageResponse(
            message="If an account exists with this email, a reset OTP code has been sent."
        )

    @classmethod
    async def reset_password(cls, db: AsyncSession, reset_in: ResetPasswordRequest) -> MessageResponse:
        """Verifies reset OTP from Redis and updates user password."""
        stored_otp = await RedisOTPService.get_otp(reset_in.email)
        if not stored_otp or stored_otp != reset_in.otp:
            raise ValueError("Invalid or expired OTP code")

        user = await cls._get_user_by_email(db, reset_in.email)
        if not user:
            raise ValueError("User not found")

        # Delete OTP from Redis
        await RedisOTPService.delete_otp(reset_in.email)

        # Update password
        user.password = hash_password(reset_in.new_password)
        await db.commit()

        return MessageResponse(message="Password reset successfully. You can now login with your new password.")

    @classmethod
    async def change_password(
        cls,
        db: AsyncSession,
        current_user: User,
        change_in: ChangePassword
    ) -> MessageResponse:
        """Changes user password if current password is correct."""
        if not verify_password(change_in.old_password, current_user.password):
            raise ValueError("Incorrect old password")

        if change_in.new_password == change_in.old_password:
            raise ValueError("New password cannot be same as old password")

        current_user.password = hash_password(change_in.new_password)
        await db.commit()

        return MessageResponse(message="Password changed successfully.")