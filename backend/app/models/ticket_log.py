import enum
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ActorType(str, enum.Enum):
    system = "system"
    agent = "agent"
    user = "user"
    admin = "admin"


class TicketLog(Base):
    __tablename__ = "ticket_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    actor_type: Mapped[ActorType] = mapped_column(
        SqlEnum(ActorType, name="actor_type"), nullable=False
    )
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    ticket: Mapped["Ticket"] = relationship(back_populates="logs")