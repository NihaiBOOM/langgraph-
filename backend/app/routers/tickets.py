from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user
from app.core.exceptions import AppException
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.ticket import TicketStatus
from app.models.ticket_log import ActorType
from app.schemas.ticket import (
    TicketCreateRequest,
    TicketDetail,
    TicketListItem,
    TicketLogResponse,
    TicketOrderInfo,
    TicketReviewRequest,
)
from app.services import ticket_log_service, ticket_service

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _fill_order_info(detail: TicketListItem, ticket) -> None:
    if ticket.order and ticket.order.product:
        detail.order = TicketOrderInfo(
            order_no=ticket.order.order_no,
            product_name=ticket.order.product.name,
            product_image=getattr(ticket.order.product, "image_url", None),
            quantity=ticket.order.quantity,
            unit_price=ticket.order.unit_price,
            total_amount=ticket.order.total_amount,
            purchased_at=ticket.order.purchased_at,
        )


@router.get("", response_model=dict)
def list_tickets(
    all: bool = Query(False, description="管理员传 true 列出所有工单"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if all and current_user.role == UserRole.admin:
        tickets = ticket_service.list_all_tickets(db)
    else:
        if all:
            raise AppException(message="无权访问", status_code=403, error_code="FORBIDDEN")
        tickets = ticket_service.list_user_tickets(db, user_id=current_user.id)

    items = []
    for t in tickets:
        item = TicketListItem.model_validate(t)
        if current_user.role == UserRole.admin:
            u = db.query(User).filter(User.id == t.user_id).first()
            item.username = u.username if u else None
        _fill_order_info(item, t)
        items.append(item)
    return {"success": True, "data": items, "message": "ok"}


@router.get("/{ticket_id}", response_model=dict)
def get_my_ticket_detail(
    ticket_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.admin:
        ticket = ticket_service.get_ticket_by_id(db, ticket_id)
    else:
        ticket = ticket_service.get_ticket_by_id_and_user(db, ticket_id, current_user.id)
    if not ticket:
        raise AppException(message="工单不存在或无权查看", status_code=404, error_code="NOT_FOUND")
    detail = TicketDetail.model_validate(ticket)
    if current_user.role == UserRole.admin:
        u = db.query(User).filter(User.id == ticket.user_id).first()
        detail.username = u.username if u else None
    _fill_order_info(detail, ticket)
    return {
        "success": True,
        "data": detail,
        "message": "ok",
    }


@router.get("/{ticket_id}/logs", response_model=dict)
def get_ticket_logs(
    ticket_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.admin:
        ticket = ticket_service.get_ticket_by_id(db, ticket_id)
    else:
        ticket = ticket_service.get_ticket_by_id_and_user(db, ticket_id, current_user.id)
    if not ticket:
        raise AppException(message="工单不存在或无权查看", status_code=404, error_code="NOT_FOUND")
    logs = ticket_log_service.list_logs_by_ticket(db, ticket_id)
    return {
        "success": True,
        "data": [TicketLogResponse.model_validate(l) for l in logs],
        "message": "ok",
    }


@router.post("", response_model=dict)
def create_ticket_for_current_user(
    req: TicketCreateRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.admin:
        raise AppException(message="管理员不能创建工单", status_code=403, error_code="FORBIDDEN")

    from app.services import order_service
    order = order_service.get_order_by_id_and_user(db, req.order_id, current_user.id)
    if not order:
        raise AppException(message="订单不存在或无权为该订单创建工单", status_code=404, error_code="NOT_FOUND")

    from app.db.session import SessionLocal
    from app.models.chat_session import ChatSession

    session = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).first()
    if not session:
        session = ChatSession(user_id=current_user.id, thread_id=f"thread-{current_user.id}")
        db.add(session)
        db.commit()
        db.refresh(session)

    ticket = ticket_service.create_ticket(
        db,
        user_id=current_user.id,
        order_id=order.id,
        session_id=session.id,
        after_sales_type=req.after_sales_type,
        reason=req.reason,
        risk_level=req.risk_level,
    )
    ticket = ticket_service.get_ticket_by_id(db, ticket.id)
    detail = TicketDetail.model_validate(ticket)
    _fill_order_info(detail, ticket)
    return {
        "success": True,
        "data": detail,
        "message": "工单创建成功",
    }


@router.post("/{ticket_id}/review", response_model=dict)
def admin_review_ticket(
    ticket_id: int,
    req: TicketReviewRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.admin:
        raise AppException(message="仅管理员可以审核工单", status_code=403, error_code="FORBIDDEN")

    ticket = ticket_service.get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise AppException(message="工单不存在", status_code=404, error_code="NOT_FOUND")

    if req.decision == "approve":
        new_status = TicketStatus.completed
        comment = req.resolution or "管理员通过审核"
        ticket_service.simulate_after_sales_execution(db, ticket_id=ticket_id, actor_user_id=current_user.id)
    else:
        if not req.resolution or not req.resolution.strip():
            raise AppException(message="拒绝工单必须填写原因", status_code=400, error_code="REJECT_REASON_REQUIRED")
        new_status = TicketStatus.rejected
        comment = req.resolution.strip()

    updated = ticket_service.update_status(
        db,
        ticket_id=ticket_id,
        new_status=new_status,
        actor_type=ActorType.admin,
        actor_user_id=current_user.id,
        comment=comment,
    )

    updated = ticket_service.get_ticket_by_id(db, ticket_id)
    detail = TicketDetail.model_validate(updated)
    _fill_order_info(detail, updated)
    return {"success": True, "data": detail, "message": "审核完成"}