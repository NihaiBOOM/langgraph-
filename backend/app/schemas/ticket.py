from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.models.ticket import AfterSalesType, RiskLevel, TicketStatus


class TicketCreateRequest(BaseModel):
    order_id: int = Field(..., gt=0, description="关联的订单 ID")
    after_sales_type: AfterSalesType
    reason: str = Field(..., min_length=5, max_length=2000)
    risk_level: RiskLevel = RiskLevel.low


class TicketOrderInfo(BaseModel):
    order_no: str | None = None
    product_name: str | None = None
    product_image: str | None = None
    quantity: int | None = None
    unit_price: float | None = None
    total_amount: float | None = None
    purchased_at: datetime | None = None

    class Config:
        from_attributes = True


class TicketListItem(BaseModel):
    id: int
    ticket_no: str
    user_id: int
    username: str | None = None
    order_id: int
    after_sales_type: AfterSalesType
    reason: str
    risk_level: RiskLevel
    status: TicketStatus
    created_at: datetime
    order: TicketOrderInfo | None = None

    class Config:
        from_attributes = True


class TicketReviewRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$")
    resolution: str | None = Field(None, min_length=1, max_length=2000)


class TicketDetail(TicketListItem):
    ai_summary: str | None = None
    policy_summary: str | None = None
    proposed_resolution: str | None = None
    result_summary: str | None = None
    rejection_reason: str | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None
    operation_completed_at: datetime | None = None
    updated_at: datetime

    class Config:
        from_attributes = True


class TicketLogResponse(BaseModel):
    id: int
    ticket_id: int
    actor_type: str
    actor_user_id: int | None = None
    action: str
    message: str
    metadata_json: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True