"""Embedding 模型工厂 —— 封装 DashScope text-embedding-v3"""

import os
from langchain_community.embeddings import DashScopeEmbeddings


def get_embeddings():
    """
    构造 DashScope Embeddings 实例。
    默认模型 text-embedding-v3，API Key 从环境变量 DASHSCOPE_API_KEY 读取。
    """
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY environment variable is not set")
    return DashScopeEmbeddings(
        model=model,
        dashscope_api_key=api_key,
    )