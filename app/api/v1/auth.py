from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_active_user
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
    ChangePassword,
    UserResponse,
    MessageResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserRegister,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await AuthService.register(db, background_tasks, user_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    verify_in: VerifyOTP,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await AuthService.verify_otp(db, verify_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/resend-otp", response_model=MessageResponse)
async def resend_otp(
    resend_in: ResendOTP,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await AuthService.resend_otp(db, background_tasks, resend_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    login_in: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await AuthService.login(db, login_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(refresh_in: RefreshTokenRequest):
    try:
        return await AuthService.refresh_tokens(refresh_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout", response_model=MessageResponse)
async def logout(refresh_in: RefreshTokenRequest):
    return await AuthService.logout(refresh_in)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    forgot_in: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    return await AuthService.forgot_password(db, background_tasks, forgot_in)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    reset_in: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await AuthService.reset_password(db, reset_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    change_in: ChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await AuthService.change_password(db=db, current_user=current_user, change_in=change_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
