from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, AfterSalesStatus


def list_user_orders(db: Session, user_id: int) -> list[Order]:
    stmt = (
        select(Order)
        .where(Order.user_id == user_id, Order.after_sales_status == AfterSalesStatus.none)
        .options(selectinload(Order.product))
        .order_by(Order.purchased_at.desc())
    )
    return list(db.scalars(stmt))


def list_user_all_orders(db: Session, user_id: int) -> list[Order]:
    stmt = (
        select(Order)
        .where(Order.user_id == user_id)
        .options(selectinload(Order.product))
        .order_by(Order.purchased_at.desc())
    )
    return list(db.scalars(stmt))


def get_order_by_id_and_user(db: Session, order_id: int, user_id: int) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.user_id == user_id)
        .options(selectinload(Order.product))
    )
    return db.scalar(stmt)


def get_order_by_id(db: Session, order_id: int) -> Order | None:
    return db.scalar(select(Order).where(Order.id == order_id))