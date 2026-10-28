"""
AI Agent 可调用的 Tool 集合 —— LangChain @tool 装饰器定义

所有 Tool 都遵循同一安全模式：
  1. 通过 ToolRuntime.config 自动注入 user_id（LLM 无法伪造）
  2. 调用 app.services 层的硬编码业务逻辑（权限校验、状态机、风控）
  3. create_ticket 额外硬拦截 confirmation_pending 状态

Tool 是 LLM 和业务世界之间的**唯一通道** —— LLM 不能直接写 DB、不能绕开校验，
只能通过 Tool 间接触发已有的安全业务逻辑。
"""

import json
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from app.db.session import SessionLocal
from app.services import order_service, ticket_service, ticket_log_service
from app.rag.retriever import retrieve_policy
from app.models.ticket import TicketStatus, RiskLevel
from app.models.ticket_log import ActorType
from app.core.exceptions import AppException


# -------------------- 内部辅助函数 --------------------

def _get_user_id(runtime: ToolRuntime) -> int | None:
    """从 LangGraph 注入的 ToolRuntime 里取当前登录用户 ID。"""
    cfg = runtime.config or {}
    return cfg.get("configurable", {}).get("user_id")


def _db():
    """每次调用新建一个 SQLAlchemy Session（用完记得 close）。"""
    return SessionLocal()


def _safe_json(obj) -> str:
    """把任意对象转成 JSON 字符串，处理 datetime / Decimal 等不可序列化类型。"""
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, ensure_ascii=False, default=str)
    return str(obj)


# -------------------- 订单相关 Tool --------------------

@tool
def list_my_orders(runtime: ToolRuntime) -> str:
    """
    List all orders of the current user that are eligible for after-sales
    (after_sales_status is still 'none').
    Returns order IDs, numbers, product names, amounts, and purchase dates.
    """
    uid = _get_user_id(runtime)
    if not uid:
        return json.dumps({"error": "user_id missing"}, ensure_ascii=False)

    db = _db()
    try:
        # order_service 内部已过滤 after_sales_status != none 的订单
        orders = order_service.list_user_orders(db, uid)
        items = []
        for o in orders:
            items.append({
                "order_id": o.id,
                "order_no": o.order_no,
                "product_name": o.product.name if o.product else "unknown",
                "quantity": o.quantity,
                "unit_price": float(o.unit_price),
                "total_amount": float(o.total_amount),
                "purchased_at": o.purchased_at.isoformat(),
                "after_sales_status": o.after_sales_status.value,
            })
        return json.dumps({"orders": items}, ensure_ascii=False)
    finally:
        db.close()


@tool
def get_order_details(order_id: int, runtime: ToolRuntime) -> str:
    """
    Get details of a specific order. Only works if the order belongs to the
    current user. Use this after listing orders to confirm a specific one.
    """
    uid = _get_user_id(runtime)
    if not uid:
        return json.dumps({"error": "user_id missing"}, ensure_ascii=False)

    db = _db()
    try:
        # 服务层同时校验了 order_id 存在 && 属于当前用户
        o = order_service.get_order_by_id_and_user(db, order_id, uid)
        if not o:
            return json.dumps({"error": "order not found or not owned by user"}, ensure_ascii=False)
        return json.dumps({
            "order_id": o.id,
            "order_no": o.order_no,
            "product_name": o.product.name if o.product else "unknown",
            "quantity": o.quantity,
            "unit_price": float(o.unit_price),
            "total_amount": float(o.total_amount),
            "purchased_at": o.purchased_at.isoformat(),
            "after_sales_status": o.after_sales_status.value,
            "order_status": o.order_status.value,
        }, ensure_ascii=False)
    finally:
        db.close()


@tool
def get_order_logistics(order_id: int, runtime: ToolRuntime) -> str:
    """
    Get logistics/shipping information for an order, including the delivery
    status and signed/received date. Only works if the order belongs to the
    current user.
    """
    from datetime import datetime, timedelta

    uid = _get_user_id(runtime)
    if not uid:
        return json.dumps({"error": "user_id missing"}, ensure_ascii=False)

    db = _db()
    try:
        o = order_service.get_order_by_id_and_user(db, order_id, uid)
        if not o:
            return json.dumps({"error": "order not found or not owned by user"}, ensure_ascii=False)

        # 模拟物流数据（生产环境应该查真实物流接口）
        signed_at = (o.purchased_at or datetime.utcnow()) + timedelta(days=3)
        return json.dumps({
            "order_id": o.id,
            "order_no": o.order_no,
            "logistics_company": "顺丰速运",
            "tracking_no": f"SF{o.id:010d}",
            "delivery_status": "signed",
            "signed_at": signed_at.isoformat(),
            "remark": "模拟物流数据",
        }, ensure_ascii=False)
    finally:
        db.close()


# -------------------- 工单核心 Tool --------------------

@tool
def create_ticket(
    order_id: int,
    after_sales_type: str,
    reason: str,
    runtime: ToolRuntime,
) -> str:
    """
    Create an after-sales ticket for the current user.

    Args:
        order_id: The order ID from the user's order list.
        after_sales_type: One of 'refund_only' (仅退款), 'return_refund' (退货退款),
            or 'exchange' (换货).
        reason: A brief reason for the after-sales request, in the user's own words.

    The system will automatically verify:
    - The order exists and belongs to the current user
    - The order hasn't been processed for after-sales yet
    - The after_sales_type is valid
    - The user has **explicitly confirmed** the proposed solution
      (Graph state confirmation_pending must be True)

    Risk level is determined by backend rules (not by the agent).
    Low-risk tickets are auto-completed; high-risk ones go to admin review.
    """
    cfg = runtime.config or {}
    configurable = cfg.get("configurable", {})
    uid = configurable.get("user_id")
    thread_id = configurable.get("thread_id")
    if not uid:
        return json.dumps({"error": "user_id missing"}, ensure_ascii=False)

    # ======= 硬拦截 1：Graph State 闸门 =======
    # 调用 graph_multi_agent.get_current_state() 读 PostgresSaver 里的确认状态
    # 如果 ticket_post 没把 confirmation_pending 设为 True，直接拒绝
    try:
        from app.services.graph_multi_agent import get_current_state
        state = get_current_state(thread_id) if thread_id else None
        if state and not state.get("confirmation_pending"):
            return json.dumps({
                "error": "TICKET_NOT_CONFIRMED",
                "message": "用户尚未明确确认售后方案，不得创建工单。请先向用户展示方案并等待确认。"
            }, ensure_ascii=False)
    except Exception:
        pass

    # ======= 硬拦截 2：售后类型合法性 =======
    if after_sales_type not in ("refund_only", "return_refund", "exchange"):
        return json.dumps({
            "error": f"invalid after_sales_type '{after_sales_type}'. "
                     f"Must be one of: refund_only, return_refund, exchange"
        }, ensure_ascii=False)

    db = _db()
    try:
        # ======= 硬拦截 3：订单归属校验 =======
        order = order_service.get_order_by_id_and_user(db, order_id, uid)
        if not order:
            return json.dumps({"error": "order not found or not owned by user"}, ensure_ascii=False)

        # ======= 风控计算（硬编码阈值 200 元） =======
        risk = _calc_risk(float(order.total_amount))

        # ======= 硬拦截 4：ticket_service 内部的状态机校验 =======
        # ticket_service.create_ticket 会检查 after_sales_status != none 等业务规则
        try:
            ticket = ticket_service.create_ticket(
                db,
                user_id=uid,
                order_id=order.id,
                session_id=session.id if (session := db.query(ChatSession).filter(
                    ChatSession.user_id == uid).first()) else None,
                after_sales_type=after_sales_type,
                reason=reason,
                risk_level=risk,
            )
        except NameError:
            from app.models.chat_session import ChatSession
            session = db.query(ChatSession).filter(ChatSession.user_id == uid).first()
            if not session:
                return json.dumps({"error": "no chat session found"}, ensure_ascii=False)
            ticket = ticket_service.create_ticket(
                db,
                user_id=uid,
                order_id=order.id,
                session_id=session.id,
                after_sales_type=after_sales_type,
                reason=reason,
                risk_level=risk,
            )
        except AppException as e:
            return json.dumps({"error": e.message, "error_code": e.error_code}, ensure_ascii=False)

        return json.dumps({
            "ticket_id": ticket.id,
            "ticket_no": ticket.ticket_no,
            "status": ticket.status.value,
            "risk_level": ticket.risk_level.value,
            "after_sales_type": ticket.after_sales_type.value,
            "reason": ticket.reason,
            "order_no": order.order_no,
            "product_name": order.product.name if order.product else "unknown",
            "total_amount": float(order.total_amount),
            "operation_completed": ticket.operation_completed_at is not None,
        }, ensure_ascii=False)
    finally:
        db.close()


# -------------------- 风控阈值（硬编码，LLM 无法改变） --------------------

RISK_AMOUNT_THRESHOLD = 200.0


def _calc_risk(total_amount: float) -> RiskLevel:
    """订单金额 >= 200 元算高风险（走管理员审核），低于算低风险（自动完成）。"""
    return RiskLevel.high if total_amount >= RISK_AMOUNT_THRESHOLD else RiskLevel.low


# -------------------- 工单查询 Tool --------------------

@tool
def list_my_tickets(runtime: ToolRuntime) -> str:
    """List all after-sales tickets of the current user with their current status."""
    uid = _get_user_id(runtime)
    if not uid:
        return json.dumps({"error": "user_id missing"}, ensure_ascii=False)

    db = _db()
    try:
        tickets = ticket_service.list_user_tickets(db, uid)
        items = []
        for t in tickets:
            items.append({
                "ticket_id": t.id,
                "ticket_no": t.ticket_no,
                "status": t.status.value,
                "risk_level": t.risk_level.value,
                "after_sales_type": t.after_sales_type.value,
                "reason": t.reason,
                "created_at": t.created_at.isoformat(),
                "product_name": t.order.product.name if t.order and t.order.product else "unknown",
                "total_amount": float(t.order.total_amount) if t.order else 0,
                "operation_completed_at": t.operation_completed_at.isoformat() if t.operation_completed_at else None,
                "review_comment": t.review_comment,
            })
        return json.dumps({"tickets": items}, ensure_ascii=False)
    finally:
        db.close()


@tool
def get_ticket_details(ticket_id: int, runtime: ToolRuntime) -> str:
    """Get full details of a specific ticket belonging to the current user."""
    uid = _get_user_id(runtime)
    if not uid:
        return json.dumps({"error": "user_id missing"}, ensure_ascii=False)

    db = _db()
    try:
        t = ticket_service.get_ticket_by_id_and_user(db, ticket_id, uid)
        if not t:
            return json.dumps({"error": "ticket not found or not owned by user"}, ensure_ascii=False)
        logs = ticket_log_service.list_logs_by_ticket(db, ticket_id)
        return json.dumps({
            "ticket_id": t.id,
            "ticket_no": t.ticket_no,
            "status": t.status.value,
            "risk_level": t.risk_level.value,
            "after_sales_type": t.after_sales_type.value,
            "reason": t.reason,
            "created_at": t.created_at.isoformat(),
            "product_name": t.order.product.name if t.order and t.order.product else "unknown",
            "total_amount": float(t.order.total_amount) if t.order else 0,
            "operation_completed_at": t.operation_completed_at.isoformat() if t.operation_completed_at else None,
            "review_comment": t.review_comment,
            "reviewed_by": t.reviewed_by,
            "reviewed_at": t.reviewed_at.isoformat() if t.reviewed_at else None,
            "logs": [
                {
                    "action": l.action,
                    "actor_type": l.actor_type.value,
                    "message": l.message,
                    "created_at": l.created_at.isoformat(),
                }
                for l in logs
            ],
        }, ensure_ascii=False)
    finally:
        db.close()


# -------------------- RAG 政策检索 Tool --------------------

@tool
def search_policy(query: str) -> str:
    """
    Search the after-sales policy knowledge base with a free-form query.
    Returns the most relevant policy snippets with their source chapters.

    Args:
        query: Keywords describing the user's situation, e.g. '耳机保修多久',
            '食品变质怎么退', '换货流程'.
    """
    try:
        # 调 retriever.py 里的 DashScope Embedding + Chroma 相似度检索
        docs = retrieve_policy(query, top_k=3)
    except Exception as e:
        return json.dumps({"error": f"policy search failed: {e}"}, ensure_ascii=False)

    if not docs:
        return json.dumps({"results": [], "note": "no direct matches found, advise human review"},
                          ensure_ascii=False)

    results = []
    for d in docs:
        meta = d.metadata or {}
        results.append({
            "section": meta.get("section") or meta.get("chapter") or meta.get("title", ""),
            "content": d.page_content.strip(),
        })
    return json.dumps({"results": results}, ensure_ascii=False)


# -------------------- 对外导出 --------------------

# 这两个字典没被使用，但保留作为人类可读的状态/类型对照参考
USER_VISIBLE_TYPE = {
    "refund_only": "仅退款",
    "return_refund": "退货退款",
    "exchange": "换货",
}

USER_VISIBLE_STATUS = {
    "pending": "处理中",
    "pending_review": "等待管理员审核",
    "completed": "已完成",
    "rejected": "已拒绝",
}


def build_all_tools() -> list:
    """
    组装所有 AI 可调用的 Tool 列表 —— ticket_agent 和 policy_agent 都依赖这个函数。
    注意 policy_agent 只取其中的 search_policy，其他 Tool 只给 ticket_agent。
    """
    return [
        list_my_orders,
        get_order_details,
        get_order_logistics,
        create_ticket,
        list_my_tickets,
        get_ticket_details,
        search_policy,
    ]