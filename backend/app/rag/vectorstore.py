"""
Chroma 向量库管理 —— 提供两个入口：
  get_vectorstore()    读取已有的持久化向量库（正常运行时用）
  build_vectorstore()  把新文档写进去（ingest_policy.py 初始化用）

持久化目录默认 backend/chroma_db，collection 名固定 "after_sales_policy"。
"""

import os
from pathlib import Path
from langchain_chroma import Chroma
from app.core.config import settings
from app.rag.embeddings import get_embeddings


def _get_persist_dir() -> str:
    """决定 Chroma 数据存在哪：优先读 settings，其次读环境变量，最后默认 chroma_db/。"""
    persist_dir = getattr(settings, "CHROMA_PERSIST_DIR", None) or os.getenv(
        "CHROMA_PERSIST_DIR", str(Path(__file__).resolve().parent.parent.parent / "chroma_db")
    )
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    return persist_dir


def get_vectorstore() -> Chroma:
    """拿到已持久化的 Chroma 实例（政策已向量化并落盘，直接读）。"""
    persist_dir = _get_persist_dir()
    embeddings = get_embeddings()
    return Chroma(
        collection_name="after_sales_policy",
        persist_directory=persist_dir,
        embedding_function=embeddings,
    )


def build_vectorstore(documents: list) -> Chroma:
    """把一批 Document 向量化并写入 Chroma（ingest_policy.py 首次初始化用）。"""
    persist_dir = _get_persist_dir()
    embeddings = get_embeddings()
    return Chroma.from_documents(
        documents=documents,
        collection_name="after_sales_policy",
        embedding=embeddings,
        persist_directory=persist_dir,
    )