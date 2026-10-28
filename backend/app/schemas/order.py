from datetime import datetime

from pydantic import BaseModel, Field

from app.models.order import AfterSalesStatus, OrderStatus


class ProductBrief(BaseModel):
    sku: str
    name: str
    price: float

    class Config:
        from_attributes = True


class OrderListItem(BaseModel):
    id: int
    order_no: str
    product_id: int
    product: ProductBrief | None = None
    quantity: int
    unit_price: float
    total_amount: float
    order_status: OrderStatus
    after_sales_status: AfterSalesStatus
    purchased_at: datetime

    class Config:
        from_attributes = True


class OrderDetail(OrderListItem):
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True