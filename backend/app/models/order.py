import enum
from datetime import datetime

from sqlalchemy import String, Float, DateTime, ForeignKey, Enum as SqlEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderStatus(str, enum.Enum):
    paid = "paid"
    cancelled = "cancelled"


class AfterSalesStatus(str, enum.Enum):
    none = "none"
    refunded = "refunded"
    returned = "returned"
    exchanged = "exchanged"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    order_status: Mapped[OrderStatus] = mapped_column(
        SqlEnum(OrderStatus, name="order_status"), default=OrderStatus.paid, nullable=False
    )
    purchased_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    after_sales_status: Mapped[AfterSalesStatus] = mapped_column(
        SqlEnum(AfterSalesStatus, name="after_sales_status"),
        default=AfterSalesStatus.none,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="orders")
    product: Mapped["Product"] = relationship(back_populates="orders")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="order")