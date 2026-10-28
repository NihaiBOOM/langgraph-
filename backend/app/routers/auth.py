from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    ApiResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.user_service import user_service

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=ApiResponse)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    user = user_service.create(db, req)
    return ApiResponse(
        success=True,
        data={"user": UserResponse.model_validate(user)},
        message="注册成功",
    )


@router.post("/login", response_model=ApiResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    user = user_service.authenticate(db, req.username, req.password)
    token = create_access_token(user.id)
    return ApiResponse(
        success=True,
        data={"token": TokenResponse(access_token=token, user=UserResponse.model_validate(user))},
        message="登录成功",
    )


@router.get("/me", response_model=ApiResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return ApiResponse(
        success=True,
        data={"user": UserResponse.model_validate(current_user)},
        message="ok",
    )


@router.get("/admin-only", response_model=ApiResponse)
def admin_only(current_user: User = Depends(require_admin)):
    return ApiResponse(
        success=True,
        data={"user": UserResponse.model_validate(current_user)},
        message="ok",
    )