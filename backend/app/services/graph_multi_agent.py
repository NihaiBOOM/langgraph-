"""
多 Agent 售后系统核心 —— LangGraph StateGraph 定义

整体架构：
  START ──→ supervisor ──┬─ TICKET ──→ ticket_agent ──→ ticket_post ──→ END
                         ├─ POLICY ──→ policy_agent ─────────────────────→ END
                         └─ CHAT   ──→ chat_agent ──────────────────────→ END

三个专职 Agent（ticket / policy / chat）各自独立，拥有独立的 Prompt、Tool 权限和 temperature。
Supervisor 是手写路由节点，用 LLM 判断用户意图后输出 route 字段，再由条件边跳转到对应 Agent。
PostgresSaver 按 thread_id 持久化整张 State，使 agent 能"记住"上一轮对话状态。
"""

import psycopg
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.db.session import SessionLocal

from app.ai.llm import get_llm
from app.ai.tools import build_all_tools, search_policy
from app.ai.prompts import (
    SUPERVISOR_PROMPT,
    TICKET_AGENT_PROMPT,
    POLICY_AGENT_PROMPT,
    CHAT_AGENT_PROMPT,
)


class MultiAgentState(TypedDict, total=False):
    """
    LangGraph 全局 State —— 整张图在每一轮 run 中共享这份状态。

    messages:    所有对话历史（Annotated[list, add_messages] 让 LangGraph 自动做追加合并）
    route:       Supervisor 输出的路由标签（TICKET / POLICY / CHAT）
    pending_plan: ticket_post 后处理检测到的"待确认方案"文本前 500 字
    confirmation_pending: 用户是否正在等待确认方案（Ticket Agent 创建工单的硬拦截开关）
    task_status:  idle / pending_confirmation / completed / cancelled
    """
    messages: Annotated[list, add_messages]
    route: str
    pending_plan: str
    confirmation_pending: bool
    task_status: str


# -------------------- 工具函数 --------------------

def _get_user_id(config: RunnableConfig) -> int | None:
    """从 graph.invoke 的 configurable 配置里取当前登录用户 ID（由 chat 路由注入）。"""
    return int(config["configurable"]["user_id"]) if "configurable" in config else None


def _get_last_user_text(state: MultiAgentState) -> str:
    """倒序遍历 messages，取最后一条 HumanMessage 的纯文本。"""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            return msg.content.strip()
    return ""


# -------------------- Supervisor 节点 --------------------

def _build_supervisor_node():
    """
    构造 Supervisor 路由节点（手写函数，不是 create_react_agent）。

    工作方式：取最近 6 条消息 → 拼 prompt → LLM 输出 TICKET/POLICY/CHAT → 写入 state["route"]。
    路由失败（LLM 报错或输出不规范）时安全降级为 TICKET（最常用分支）。
    """
    llm = get_llm(temperature=0.0)

    def supervisor(state: MultiAgentState) -> dict:
        history = state.get("messages", [])
        recent = history[-6:] if len(history) > 6 else history

        # 把 LangChain Message 转成 ChatCompletion 格式喂给 LLM
        prompt_msgs = [{"role": "system", "content": SUPERVISOR_PROMPT}]
        for m in recent:
            if isinstance(m, HumanMessage):
                prompt_msgs.append({"role": "user", "content": m.content})
            elif isinstance(m, AIMessage):
                prompt_msgs.append({"role": "assistant", "content": m.content})

        try:
            resp = llm.invoke(prompt_msgs)
            text = resp.content.strip().upper()
        except Exception as e:
            return {"route": "TICKET"}

        if "TICKET" in text:
            return {"route": "TICKET"}
        if "POLICY" in text:
            return {"route": "POLICY"}
        return {"route": "CHAT"}

    return supervisor


# -------------------- 三个专职 Agent --------------------

def _build_agents():
    """
    构建三个 create_react_agent 实例。

    ticket_agent: 拥有全部 7 个 Tool，处理售后工单全流程（查询订单 → 查政策 → 生成方案 → 创建工单）。
    policy_agent: 只有 search_policy 一个 Tool，专门回答政策咨询。
    chat_agent:   零 Tool，纯 LLM 闲聊回复。

    每个 Agent 内部是 ReAct 循环（思考 → 调 Tool → 再思考 ... 直到输出纯文本）。
    """
    llm = get_llm(temperature=0.1)

    all_tools = build_all_tools()
    ticket_tools = all_tools
    policy_tools = [search_policy]

    ticket_agent = create_react_agent(
        model=llm,
        tools=ticket_tools,
        prompt=TICKET_AGENT_PROMPT,
        name="ticket_agent",
    )

    policy_agent = create_react_agent(
        model=llm,
        tools=policy_tools,
        prompt=POLICY_AGENT_PROMPT,
        name="policy_agent",
    )

    chat_agent = create_react_agent(
        model=llm,
        tools=[],
        prompt=CHAT_AGENT_PROMPT,
        name="chat_agent",
    )

    return ticket_agent, policy_agent, chat_agent


# -------------------- 图构建 --------------------

def _build_graph():
    """
    组装 StateGraph：先建 Supervisor 和三个 Agent，再定义 ticket_post 后处理节点和条件路由边。

    ticket_post 的作用：
      - 如果 ticket_agent 这轮调用了 create_ticket → 关门（confirmation_pending=False），标记任务完成
      - 如果 ticket_agent 输出里有"确认""方案"等关键词 → 开门（confirmation_pending=True），等用户下一轮说"确认"
      - 这是 create_ticket Tool 硬拦截的**反向闸门**
    """
    supervisor_fn = _build_supervisor_node()
    ticket_agent, policy_agent, chat_agent = _build_agents()

    def ticket_post_process(state: MultiAgentState) -> dict:
        """Ticket Agent 专属后处理节点 —— 扫描最后一条 AI 输出，更新确认状态闸门。"""
        msgs = state.get("messages", [])
        new_state = {}

        # 倒序找最后一条 AI 消息
        last_ai = None
        for m in reversed(msgs):
            if isinstance(m, AIMessage):
                last_ai = m
                break

        if last_ai is None:
            return new_state

        # Case 1: AI 消息里带了 tool_calls（说明 Agent 真调用了某个 Tool）
        if last_ai.tool_calls:
            called_tools = [tc["name"] for tc in last_ai.tool_calls]
            if "create_ticket" in called_tools:
                # create_ticket 被调了 → 工单已创建 → 关门，任务完成
                new_state["confirmation_pending"] = False
                new_state["pending_plan"] = None
                new_state["task_status"] = "completed"
            else:
                # 调的是 list_my_orders / search_policy 之类的查询工具 → 保持原状
                new_state["confirmation_pending"] = state.get("confirmation_pending", False)
        else:
            # Case 2: 纯文本回复，没有 tool_calls
            text = last_ai.content or ""
            # 关键词检测：Agent 是否正在向用户展示"待确认方案"
            is_plan = any(kw in text for kw in ["确认", "待您", "方案", "是否同意", "请确认", "如果确认", "帮我提交", "确认后"])
            # 排除词：如果 Agent 说"我将为您创建"这种自己要动手的话，不视为待确认方案
            has_tool_recommendation = any(kw in text for kw in ["我将为您创建", "马上为您创建", "立即提交"])
            if is_plan and not has_tool_recommendation:
                # 开门 —— 等用户下一轮说"确认"
                new_state["confirmation_pending"] = True
                new_state["pending_plan"] = text[:500]
                new_state["task_status"] = "pending_confirmation"
            else:
                # 普通回复（比如问清楚订单信息）→ 关着门
                new_state["confirmation_pending"] = False
                new_state["pending_plan"] = None

        return new_state

    def route_after_supervisor(state: MultiAgentState) -> str:
        """条件路由函数 —— 读 state["route"] 决定跳到哪个 Agent 节点。"""
        return state.get("route", "CHAT")

    builder = StateGraph(MultiAgentState)

    # 注册 5 个节点
    builder.add_node("supervisor", supervisor_fn)
    builder.add_node("ticket_agent", ticket_agent)
    builder.add_node("ticket_post", ticket_post_process)
    builder.add_node("policy_agent", policy_agent)
    builder.add_node("chat_agent", chat_agent)

    # 连边：START → supervisor → 条件分支 → 各自 Agent → ticket_agent 多一道后处理
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "TICKET": "ticket_agent",
            "POLICY": "policy_agent",
            "CHAT": "chat_agent",
        },
    )
    builder.add_edge("ticket_agent", "ticket_post")
    builder.add_edge("ticket_post", END)
    builder.add_edge("policy_agent", END)
    builder.add_edge("chat_agent", END)

    return builder


# -------------------- 单例管理 --------------------
# 三个全局变量：PostgreSQL 连接、PostgresSaver 实例、编译好的 CompiledGraph
# FastAPI 启动时在 main.py 调 init_checkpointer_and_graph() 一次性建好

_pg_conn: psycopg.Connection | None = None
_checkpointer: PostgresSaver | None = None
_graph = None


def get_conn_string() -> str:
    """把 SQLAlchemy 的 postgresql+psycopg:// URL 转成 psycopg 原生的 postgresql:// URL。"""
    url = settings.DATABASE_URL
    if url.startswith("postgresql+psycopg://"):
        url = "postgresql://" + url[len("postgresql+psycopg://"):]
    return url


def init_checkpointer_and_graph():
    """
    初始化 PostgresSaver + 编译 Graph（应用启动时调用一次）。

    PostgresSaver 会在 PostgreSQL 里建 checkpoint 表，每次 graph.invoke() 结束后
    整张 State 会被原子化存进去；下次同一个 thread_id 来的时候自动恢复。
    """
    global _pg_conn, _checkpointer, _graph
    if _pg_conn is not None and _graph is not None:
        return _graph

    conn_str = get_conn_string()
    _pg_conn = psycopg.connect(conn_str)
    _pg_conn.autocommit = True

    _checkpointer = PostgresSaver(_pg_conn)
    _checkpointer.setup()  # 创建 checkpoint 表（如果不存在）

    builder = _build_graph()
    _graph = builder.compile(checkpointer=_checkpointer)
    return _graph


def get_graph():
    """懒加载获取编译好的 Graph —— 路由层调 graph.invoke() 前先拿这个。"""
    if _graph is None:
        init_checkpointer_and_graph()
    return _graph


def shutdown_checkpointer():
    """应用关闭时释放 PostgreSQL 连接池（main.py 的 shutdown 事件）。"""
    global _pg_conn, _checkpointer, _graph
    if _pg_conn is not None:
        try:
            _pg_conn.close()
        except Exception:
            pass
        _pg_conn = None
    _checkpointer = None
    _graph = None


def get_current_state(thread_id: str) -> MultiAgentState | None:
    """
    从 PostgresSaver 读取某个 thread_id 的当前 State 快照。

    这个函数被 create_ticket Tool 调用 —— 在 Tool 内部硬拦截：
    如果 confirmation_pending 不是 True，直接拒绝创建工单。
    这是"用户确认闸门"的读侧。
    """
    if _checkpointer is None or not thread_id:
        return None
    try:
        cfg = {"configurable": {"thread_id": thread_id}}
        state = _checkpointer.get_state(cfg)
        if state is None:
            return None
        values = state.values if hasattr(state, "values") else state
        return values
    except Exception:
        return None