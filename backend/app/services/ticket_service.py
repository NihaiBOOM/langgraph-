"""
工单业务逻辑层 —— 被 AI Tool (create_ticket) 和 REST 路由 (tickets.py) 共同调用

核心业务规则全部硬编码在这里，LLM 无法绕过：
  1. STATUS_TRANSITIONS 状态机 —— 工单状态只能按固定路径流转
  2. 订单 after_sales_status 防重复 —— 一个订单只能申请一次售后
  3. simulate_after_sales_execution 防重复执行 —— operation_completed_at 非空即拒绝

风控等级（高/低）由 tools.py 里的 _calc_risk 决定，传入 risk_level 参数，
这里根据 risk_level 自动决定：低风险直接执行→自动完成；高风险走 pending_review→等管理员审核。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.order import Order
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_log import ActorType
from app.services import ticket_log_service


# -------------------- 状态机 --------------------
# 工单状态只能按这个字典定义的路径流转，这是硬编码的安全规则
STATUS_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.pending: {TicketStatus.completed, TicketStatus.pending_review, TicketStatus.rejected},
    TicketStatus.pending_review: {TicketStatus.completed, TicketStatus.rejected},
    TicketStatus.completed: set(),      # 终态，不能再变
    TicketStatus.rejected: set(),       # 终态，不能再变
}


def generate_ticket_no(db: Session) -> str:
    """生成工单号：TK-YYYYMMDD-0001（每日递增，基于当天已存在数量 + 1）。"""
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"TK-{today}-"
    existing = (
        db.query(Ticket)
        .filter(Ticket.ticket_no.like(f"{prefix}%"))
        .count()
    )
    seq = existing + 1
    return f"{prefix}{seq:04d}"


def ensure_valid_transition(current: TicketStatus, new: TicketStatus) -> None:
    """
    状态机校验 —— 所有 update_status 调用前必须先过这道关。
    不合法的流转直接抛 AppException，HTTP 层返回 400。
    """
    if new not in STATUS_TRANSITIONS.get(current, set()):
        raise AppException(
            message=f"工单状态不能从 {current.value} 转为 {new.value}",
            status_code=400,
            error_code="INVALID_STATUS_TRANSITION",
        )


# -------------------- 查询 --------------------

def list_user_tickets(db: Session, user_id: int) -> list[Ticket]:
    """列出当前用户的所有工单（带关联的订单和商品信息）。"""
    return (
        db.query(Ticket)
        .options(joinedload(Ticket.order).joinedload(Order.product))
        .filter(Ticket.user_id == user_id)
        .order_by(Ticket.created_at.desc())
        .all()
    )


def list_all_tickets(db: Session) -> list[Ticket]:
    """管理员看全部工单。"""
    return (
        db.query(Ticket)
        .options(joinedload(Ticket.order).joinedload(Order.product))
        .order_by(Ticket.created_at.desc())
        .all()
    )


def get_ticket_by_id_and_user(
    db: Session, ticket_id: int, user_id: int
) -> Optional[Ticket]:
    """同时校验 ticket_id + user_id —— 用户只能看自己的工单。"""
    return (
        db.query(Ticket)
        .options(joinedload(Ticket.order).joinedload(Order.product))
        .filter(Ticket.id == ticket_id, Ticket.user_id == user_id)
        .first()
    )


def get_ticket_by_id(db: Session, ticket_id: int) -> Optional[Ticket]:
    """按 ticket_id 查（管理员用，不校验 user_id）。"""
    return (
        db.query(Ticket)
        .options(joinedload(Ticket.order).joinedload(Order.product))
        .filter(Ticket.id == ticket_id)
        .first()
    )


# -------------------- 创建工单 --------------------

def create_ticket(
    db: Session,
    *,
    user_id: int,
    order_id: int,
    session_id: int,
    after_sales_type,
    reason: str,
    risk_level=None,
) -> Ticket:
    """
    核心业务 —— 创建售后工单。

    执行流程：
      1. 订单归属校验 + 防重复售后（after_sales_status 必须是 none）
      2. INSERT Ticket + UPDATE Order.after_sales_status
      3. 写一条 TICKET_CREATED 日志
      4. 根据 risk_level 自动分流：
           低风险 → simulate_after_sales_execution（模拟执行）→ 状态变 completed
           高风险 → 状态变 pending_review（等管理员审核）

    这个函数同时被两条路径调用：
      - AI 路径：tools.create_ticket → 过 Graph State 闸门 → 到这里
      - HTTP 路径：管理员审核后 approve → 到这里（不常见，一般直接 update_status）
    """
    from app.models.ticket import RiskLevel
    from app.models.order import AfterSalesStatus

    # ======= 业务校验：订单存在 =======
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise AppException(message="订单不存在", status_code=404, error_code="ORDER_NOT_FOUND")

    # ======= 业务校验：防重复售后（硬编码）=======
    if order.after_sales_status != AfterSalesStatus.none:
        raise AppException(
            message=f"该订单已申请过售后（状态：{order.after_sales_status.value}），不可重复申请",
            status_code=400,
            error_code="ORDER_ALREADY_AFTERSALES",
        )

    ticket = Ticket(
        ticket_no=generate_ticket_no(db),
        user_id=user_id,
        order_id=order_id,
        session_id=session_id,
        after_sales_type=after_sales_type,
        reason=reason,
        risk_level=risk_level or RiskLevel.low,
        status=TicketStatus.pending,
    )
    db.add(ticket)

    # 同时标记订单的售后状态（防止再次申请）
    order.after_sales_status = _type_to_pending_status(after_sales_type)
    db.commit()
    db.refresh(ticket)

    # 写工单日志
    ticket_log_service.write_log(
        db,
        ticket_id=ticket.id,
        actor_type=ActorType.system,
        action="TICKET_CREATED",
        message=f"工单创建：{ticket.ticket_no}",
    )

    # ======= 风控自动分流 =======
    if ticket.risk_level == RiskLevel.low:
        # 低风险：自动执行售后（模拟）→ 标记完成
        simulate_after_sales_execution(db, ticket_id=ticket.id)
        ticket = update_status(
            db,
            ticket_id=ticket.id,
            new_status=TicketStatus.completed,
            actor_type=ActorType.system,
            comment="低风险，自动处理完成",
        )
    else:
        # 高风险：转管理员审核队列
        ticket = update_status(
            db,
            ticket_id=ticket.id,
            new_status=TicketStatus.pending_review,
            actor_type=ActorType.system,
            comment="高风险，等待管理员审核",
        )

    return ticket


# -------------------- 状态流转 --------------------

def update_status(
    db: Session,
    *,
    ticket_id: int,
    new_status: TicketStatus,
    actor_type: ActorType,
    actor_user_id: int | None = None,
    comment: str | None = None,
) -> Ticket:
    """
    通用状态更新入口 —— 所有状态变更都走这里，保证：
      1. 过 STATUS_TRANSITIONS 状态机校验
      2. 自动填充 operation_completed_at（完结时）和 reviewed_by / reviewed_at（管理员操作时）
      3. 写一条 STATUS_CHANGED 日志
    """
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise AppException(message="工单不存在", status_code=404, error_code="NOT_FOUND")

    ensure_valid_transition(ticket.status, new_status)

    old_status = ticket.status
    ticket.status = new_status

    if new_status == TicketStatus.completed and ticket.operation_completed_at is None:
        ticket.operation_completed_at = datetime.utcnow()
    if comment:
        ticket.review_comment = comment
        if actor_type == ActorType.admin:
            ticket.reviewed_by = actor_user_id
            ticket.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(ticket)

    ticket_log_service.write_log(
        db,
        ticket_id=ticket.id,
        actor_type=actor_type,
        action="STATUS_CHANGED",
        message=f"状态 {old_status.value} → {new_status.value}" + (f"，备注：{comment}" if comment else ""),
        actor_user_id=actor_user_id,
    )
    return ticket


def simulate_after_sales_execution(
    db: Session, *, ticket_id: int, actor_user_id: int | None = None
) -> Ticket:
    """
    模拟售后执行 —— 未来接真实退款/退货接口时替换这里的实现。
    当前只做：标记 operation_completed_at + 更新订单终态 + 写日志。

    防重复执行：operation_completed_at 非空即拒绝。
    """
    from app.models.order import Order, AfterSalesStatus

    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise AppException(message="工单不存在", status_code=404, error_code="NOT_FOUND")

    if ticket.operation_completed_at is not None:
        raise AppException(
            message="该工单已执行过售后操作",
            status_code=400,
            error_code="ALREADY_EXECUTED",
        )

    ticket.operation_completed_at = datetime.utcnow()

    # 把订单的售后状态从 pending 态改成最终态（refunded/returned/exchanged）
    order = db.query(Order).filter(Order.id == ticket.order_id).first()
    if order:
        order.after_sales_status = _type_to_final_status(ticket.after_sales_type)

    db.commit()
    db.refresh(ticket)

    ticket_log_service.write_log(
        db,
        ticket_id=ticket.id,
        actor_type=ActorType.system,
        action="AFTERSALES_SIMULATED",
        message=f"模拟售后执行（类型={ticket.after_sales_type.value}），将在后续接 Agent 时替换为真实调用",
        actor_user_id=actor_user_id,
    )
    return ticket


# -------------------- 内部映射 --------------------

def _type_to_final_status(after_sales_type) -> "AfterSalesStatus":
    """售后类型 → 订单终态的硬编码映射。"""
    from app.models.order import AfterSalesStatus
    from app.models.ticket import AfterSalesType

    mapping = {
        AfterSalesType.refund_only: AfterSalesStatus.refunded,
        AfterSalesType.return_refund: AfterSalesStatus.returned,
        AfterSalesType.exchange: AfterSalesStatus.exchanged,
    }
    return mapping.get(after_sales_type, AfterSalesStatus.refunded)


def _type_to_pending_status(after_sales_type) -> "AfterSalesStatus":
    """创建工单时先把订单售后状态标记为进行中（和最终态一样，因为 pending 也是一种占用）。"""
    return _type_to_final_status(after_sales_type)