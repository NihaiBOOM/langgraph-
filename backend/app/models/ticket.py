import enum
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AfterSalesType(str, enum.Enum):
    refund_only = "refund_only"
    return_refund = "return_refund"
    exchange = "exchange"


class TicketStatus(str, enum.Enum):
    pending = "pending"
    pending_review = "pending_review"
    completed = "completed"
    rejected = "rejected"


class RiskLevel(str, enum.Enum):
    low = "low"
    high = "high"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False, index=True)

    after_sales_type: Mapped[AfterSalesType] = mapped_column(
        SqlEnum(AfterSalesType, name="after_sales_type"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)

    risk_level: Mapped[RiskLevel] = mapped_column(
        SqlEnum(RiskLevel, name="risk_level"), default=RiskLevel.low, nullable=False
    )
    status: Mapped[TicketStatus] = mapped_column(
        SqlEnum(TicketStatus, name="ticket_status"), default=TicketStatus.pending, nullable=False, index=True
    )

    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    operation_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="tickets", foreign_keys=[user_id])
    reviewed_by_admin: Mapped["User | None"] = relationship(
        back_populates="reviewed_tickets", foreign_keys=[reviewed_by]
    )
    order: Mapped["Order"] = relationship(back_populates="tickets")
    session: Mapped["ChatSession"] = relationship(back_populates="tickets")
    logs: Mapped[list["TicketLog"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")