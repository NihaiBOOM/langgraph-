from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.exceptions import AppException
from app.db.session import get_db
from app.models.user import User
from app.schemas.order import OrderDetail, OrderListItem
from app.services import order_service

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("", response_model=dict)
def list_my_orders(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    orders = order_service.list_user_all_orders(db, user_id=current_user.id)
    return {
        "success": True,
        "data": [OrderListItem.model_validate(o) for o in orders],
        "message": "ok",
    }


@router.get("/{order_id}", response_model=dict)
def get_my_order_detail(
    order_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = order_service.get_order_by_id_and_user(db, order_id, current_user.id)
    if not order:
        raise AppException(message="订单不存在或无权查看", status_code=404, error_code="NOT_FOUND")
    return {
        "success": True,
        "data": OrderDetail.model_validate(order),
        "message": "ok",
    }