"""
FastAPI 应用入口 —— 注册路由 + CORS + 异常处理 + 生命周期钩子

启动流程（FastAPI lifespan）：
  1. init_checkpointer_and_graph() —— 建 PostgreSQL 连接、初始化 PostgresSaver、编译 LangGraph
  2. 注册 4 个路由模块（auth / orders / tickets / chat）
  3. 关闭时 shutdown_checkpointer() 释放连接池
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models  # noqa: F401 - 确保所有 SQLAlchemy ORM 模型被 import，让 Alembic / create_all 能感知
from app.core.exceptions import AppException
from app.routers import auth as auth_router
from app.routers import orders as orders_router
from app.routers import tickets as tickets_router
from app.routers import chat as chat_router
from app.services.graph_multi_agent import init_checkpointer_and_graph, shutdown_checkpointer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理器 —— 应用启动时初始化 LangGraph + PostgresSaver，关闭时释放。
    这是 LangGraph checkpoint 持久化的关键准备步骤，必须在第一个 graph.invoke() 之前完成。
    """
    init_checkpointer_and_graph()
    print("[lifespan] PostgresSaver + LangGraph initialized")
    try:
        yield
    finally:
        shutdown_checkpointer()
        print("[lifespan] PostgresSaver closed")


app = FastAPI(title="智能售后工单系统 API", version="0.6.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """全局异常处理器 —— 所有 service 层抛出的 AppException 统一返回 JSON 错误响应。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "message": exc.message,
            "error_code": exc.error_code,
        },
    )


# 注册 4 个路由模块
app.include_router(auth_router.router)
app.include_router(orders_router.router)
app.include_router(tickets_router.router)
app.include_router(chat_router.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "智能售后工单系统"}