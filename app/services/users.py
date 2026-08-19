import os
import uuid
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password
from app.models.users import User
from app.schemas.users import UserCreate


class UserService:
    
    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: UUID) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(db: AsyncSession) -> list[User]:
        result = await db.execute(select(User))
        return list(result.scalars().all())

    @classmethod
    async def create(cls, db: AsyncSession, user_in: UserCreate) -> User:
        
        if user_in.password != user_in.re_password:
            raise ValueError("Passwords do not match")
        
        existing = await cls.get_by_email(db, user_in.email)
        if existing:
            raise ValueError("Email already registered")
        
        hashed_pwd = hash_password(user_in.password)
        
        new_user = User(
            full_name=user_in.full_name,
            email=user_in.email,
            avatar_url=user_in.avatar_url,
            password=hashed_pwd  # Store hashed password
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    @classmethod
    async def update(
        cls,
        db: AsyncSession,
        user_id: UUID,
        full_name: str | None = None,
        email: str | None = None,
        avatar: UploadFile | None = None
    ) -> User:
        user = await cls.get_by_id(db, user_id)
        if not user:
            raise ValueError("User not found")
        # 1. Update text fields if provided
        if full_name is not None:
            user.full_name = full_name
        if email is not None:
            user.email = email
        # 2. Process image upload if an image file was selected
        if avatar is not None and avatar.filename:
            allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
            ext = os.path.splitext(avatar.filename)[1].lower()
            if ext not in allowed_extensions:
                raise ValueError("Only JPG, PNG, and WEBP images are allowed")
            filename = f"{uuid.uuid4()}{ext}"
            file_path = os.path.join("uploads", "avatars", filename)
            contents = await avatar.read()
            with open(file_path, "wb") as f:
                f.write(contents)
            user.avatar_url = f"/uploads/avatars/{filename}"
        # 3. Save changes
        await db.commit()
        await db.refresh(user)
        return user

    @classmethod
    async def delete(cls, db: AsyncSession, user_id: UUID) -> bool:
        user = await cls.get_by_id(db, user_id)
        if not user:
            return False
        
        await db.delete(user)
        await db.commit()
        return True
