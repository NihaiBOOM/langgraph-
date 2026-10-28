import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.user import UserRole


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="用户名，3-64位")
    password: str = Field(..., min_length=6, max_length=128, description="密码，至少6位")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("用户名只能包含字母、数字和下划线")
        return v


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ApiResponse(BaseModel):
    success: bool
    data: dict | None = None
    message: str = "ok"