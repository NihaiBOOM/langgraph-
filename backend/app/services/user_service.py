from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserRegisterRequest


class UserService:
    @staticmethod
    def create(db: Session, req: UserRegisterRequest) -> User:
        existing = db.query(User).filter(User.username == req.username).first()
        if existing:
            raise AppException(message="用户名已存在", status_code=400, error_code="USERNAME_TAKEN")

        user = User(
            username=req.username,
            password_hash=hash_password(req.password),
            role=UserRole.user,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate(db: Session, username: str, password: str) -> User:
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password_hash):
            raise AppException(message="用户名或密码错误", status_code=400, error_code="LOGIN_FAILED")
        if not user.is_active:
            raise AppException(message="账号已被禁用", status_code=400, error_code="USER_DISABLED")
        return user


user_service = UserService()