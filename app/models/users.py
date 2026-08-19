from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
        )
        
    full_name: Mapped[str] = mapped_column(
        String(155)
        )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
        )

    avatar_url: Mapped[str] = mapped_column(
        String(500),
        nullable=True
        )

    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
        )

    def __repr__(self) -> str:
        return f"User(id={self.id}, name={self.full_name})"