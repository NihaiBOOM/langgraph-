from datetime import datetime, timedelta

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.db.session import get_db
from app.models.user import User, UserRole

security = HTTPBearer(auto_error=False)


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = int(payload.get("sub"))
        return user_id
    except jwt.ExpiredSignatureError:
        raise AppException(message="登录已过期，请重新登录", status_code=401, error_code="TOKEN_EXPIRED")
    except jwt.InvalidTokenError:
        raise AppException(message="无效的令牌", status_code=401, error_code="INVALID_TOKEN")


def _extract_token(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_token(credentials)
    if not token:
        raise AppException(message="请先登录", status_code=401, error_code="NOT_LOGIN")
    user_id = decode_access_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise AppException(message="用户不存在或已禁用", status_code=401, error_code="USER_NOT_FOUND")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise AppException(message="需要管理员权限", status_code=403, error_code="FORBIDDEN")
    return current_user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    token = _extract_token(credentials)
    if not token:
        return None
    try:
        user_id = decode_access_token(token)
        return db.query(User).filter(User.id == user_id, User.is_active == True).first()
    except Exception:
        return None