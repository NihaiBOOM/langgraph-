import enum
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role"), default=UserRole.user, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    orders: Mapped[list["Order"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    chat_session: Mapped["ChatSession"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", foreign_keys="[Ticket.user_id]"
    )
    reviewed_tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="reviewed_by_admin", foreign_keys="[Ticket.reviewed_by]"
    )