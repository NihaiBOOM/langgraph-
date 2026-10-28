"""
聊天路由 —— 后端唯一的 AI 对话入口

核心接口：POST /api/chat/message
  一次完整的 LangGraph run：拿到用户消息 → graph.invoke() → 落库 → 返回 AI 回复

  LangGraph 的持久化（PostgresSaver）和用户会话绑定（ChatSession.thread_id）在 graph_multi_agent.py 里处理，
  这里只负责：
    1. 通过 JWT 认证拿到 current_user
    2. 确保该用户有一个 ChatSession（没有就创建，里面存 LangGraph thread_id）
    3. 把 user_id 和 thread_id 注入 graph.invoke 的 configurable 配置里
    4. 落库用户消息 + AI 消息（除了 LangGraph checkpoint 之外的备份，方便前端历史查询）

另还有一个流式接口 POST /api/chat/stream（SSE），用 graph.stream() 逐 chunk 输出。
"""

import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessageChunk

from app.db.session import get_db
from app.models.user import User
from app.core.auth import get_current_user
from app.services import chat_service
from app.services.graph_multi_agent import get_graph
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatSessionResponse,
    ChatMessageResponse,
    ChatMessageRequest,
    ChatMessageResponseFull,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _to_session_response(s) -> ChatSessionResponse:
    """ChatSession ORM → API 响应 Schema。"""
    return ChatSessionResponse(
        id=s.id,
        thread_id=s.thread_id,
        created_at=s.created_at.isoformat(),
    )


def _to_msg_response(m) -> ChatMessageResponse:
    """ChatMessage ORM → API 响应 Schema。"""
    return ChatMessageResponse(
        id=m.id,
        role=m.role,
        content=m.content,
        created_at=m.created_at.isoformat(),
    )


@router.get("/history")
def get_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """拉取当前用户的完整对话历史（落库的 ChatMessage，不是 LangGraph checkpoint）。"""
    session = chat_service.get_or_create_session(db, current_user.id)
    messages = chat_service.get_history(db, session.id, current_user.id)
    return {
        "success": True,
        "data": ChatHistoryResponse(
            session=_to_session_response(session),
            messages=[_to_msg_response(m) for m in messages],
        ).model_dump(),
        "message": "ok",
    }


@router.post("/message")
def send_message(
    req: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    用户发送消息 → LangGraph run 一轮 → 返回 AI 回复。

    graph.invoke 的 configurable 配置同时注入 thread_id 和 user_id：
      - thread_id: PostgresSaver 按这个 ID 读写 checkpoint（状态持久化的关键）
      - user_id:    ToolRuntime 会把它传给所有 @tool 函数（LLM 无法伪造身份）
    """
    # 确保用户有会话（thread_id 不存在就创建一个新的 UUID）
    session = chat_service.get_or_create_session(db, current_user.id)

    # 先落库用户消息
    user_msg = chat_service.save_message(db, session.id, "user", req.content)

    graph = get_graph()
    config = {
        "configurable": {
            "thread_id": session.thread_id,
            "user_id": current_user.id,
        }
    }

    # ====== 核心：跑一轮 LangGraph ======
    # graph.invoke 内部会：
    #   1. PostgresSaver 按 thread_id 恢复上一轮的 State（如果有的话）
    #   2. supervisor → 路由到某个 Agent → ticket_post（可能）
    #   3. 整张 State 被 PostgresSaver 存回 PostgreSQL
    result = graph.invoke(
        {"messages": [HumanMessage(content=req.content)]},
        config,
    )

    # AI 回复是 State messages 列表里最后一条 AIMessage
    ai_content = result["messages"][-1].content
    assistant_msg = chat_service.save_message(db, session.id, "assistant", ai_content)

    return {
        "success": True,
        "data": ChatMessageResponseFull(
            user_message=_to_msg_response(user_msg),
            assistant_message=_to_msg_response(assistant_msg),
        ).model_dump(),
        "message": "ok",
    }


@router.post("/stream")
def send_message_stream(
    req: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    流式版：用 Server-Sent Events 逐 chunk 推给前端。

    和 /message 的区别：用 graph.stream(stream_mode="messages") 代替 graph.invoke，
    前端每收到一个 SSE delta 事件就追加到气泡里。
    """
    session = chat_service.get_or_create_session(db, current_user.id)
    chat_service.save_message(db, session.id, "user", req.content)

    graph = get_graph()
    config = {
        "configurable": {
            "thread_id": session.thread_id,
            "user_id": current_user.id,
        }
    }

    def _sse(event: str, data) -> str:
        """SSE 格式：event 行 + data 行 + 空行分隔。"""
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def generate():
        """生成器：graph.stream 逐 chunk 产出 AIMessageChunk，累加成完整回复。"""
        full_content = ""
        try:
            for chunk in graph.stream(
                {"messages": [HumanMessage(content=req.content)]},
                config,
                stream_mode="messages",
            ):
                msg, meta = chunk
                if isinstance(msg, AIMessageChunk):
                    text = msg.content or ""
                    # AIMessageChunk.content 可能是 str 也可能是 list（多模态场景），两种都处理
                    if isinstance(text, str) and text:
                        full_content += text
                        yield _sse("delta", {"content": text})
                    elif isinstance(text, list):
                        for item in text:
                            if isinstance(item, dict) and item.get("type") == "text":
                                t = item.get("text", "")
                                if t:
                                    full_content += t
                                    yield _sse("delta", {"content": t})

            # 流结束：落库完整消息，发 done 事件
            final_msg = chat_service.save_message(db, session.id, "assistant", full_content or "(无回复)")
            yield _sse("done", {
                "content": full_content,
                "message_id": final_msg.id,
            })
        except Exception as e:
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )