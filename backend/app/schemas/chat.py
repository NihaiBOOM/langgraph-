from pydantic import BaseModel


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class ChatSessionResponse(BaseModel):
    id: int
    thread_id: str
    created_at: str


class ChatHistoryResponse(BaseModel):
    session: ChatSessionResponse
    messages: list[ChatMessageResponse]


class ChatMessageRequest(BaseModel):
    content: str


class ChatMessageResponseFull(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse