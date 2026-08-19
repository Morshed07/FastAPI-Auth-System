from pydantic import BaseModel, ConfigDict, model_validator
import uuid


class UserCreate(BaseModel):
    full_name: str
    email: str
    avatar_url: str | None = None
    password: str
    re_password: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    avatar_url: str | None = None


class UserResponse(BaseModel):

    id: uuid.UUID
    full_name: str
    email: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)