import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=155)
    email: EmailStr
    password: str = Field(..., min_length=6)
    re_password: str = Field(..., min_length=6)

    @model_validator(mode="after")
    def validate_passwords(self) -> "UserRegister":
        if self.password != self.re_password:
            raise ValueError("Passwords do not match")
        return self


class VerifyOTP(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class ResendOTP(BaseModel):
    email: EmailStr


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)
    re_new_password: str = Field(..., min_length=6)

    @model_validator(mode="after")
    def validate_passwords(self) -> "ResetPasswordRequest":
        if self.new_password != self.re_new_password:
            raise ValueError("Passwords do not match")
        return self


class ChangePassword(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)
    re_new_password: str = Field(..., min_length=6)

    @model_validator(mode="after")
    def validate_passwords(self) -> "ChangePassword":
        if self.new_password != self.re_new_password:
            raise ValueError("Passwords do not match")
        return self


class UserResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    avatar_url: str | None = None
    is_verified: bool
    is_active: bool
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str
