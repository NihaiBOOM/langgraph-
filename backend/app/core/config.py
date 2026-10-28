from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "智能售后工单系统"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+psycopg://postgres:123456@localhost:5432/after_sales"

    JWT_SECRET_KEY: str = "dev-change-me-in-production-please-use-env"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    class Config:
        env_file = ".env"


settings = Settings()