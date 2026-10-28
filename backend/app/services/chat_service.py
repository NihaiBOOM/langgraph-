from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage


def get_or_create_session(db: Session, user_id: int) -> ChatSession:
    session = db.query(ChatSession).filter(ChatSession.user_id == user_id).first()
    if session:
        return session

    thread_id = f"thread-{user_id}"
    session = ChatSession(user_id=user_id, thread_id=thread_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_history(db: Session, session_id: int, viewer_user_id: int) -> list[ChatMessage]:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != viewer_user_id:
        raise HTTPException(status_code=404, detail="会话不存在")
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


def save_message(
    db: Session, session_id: int, role: str, content: str
) -> ChatMessage:
    msg = ChatMessage(session_id=session_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg