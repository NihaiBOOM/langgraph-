"""RAG 检索上层 API —— 拼 Embedding + Chroma 相似度检索，返回 top_k 条政策片段。"""

from typing import List
from langchain_core.documents import Document
from app.rag.vectorstore import get_vectorstore


def get_retriever(top_k: int = 3):
    """用 Chroma 的 as_retriever() 构造一个相似度检索器。"""
    vectorstore = get_vectorstore()
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": top_k},
    )


def retrieve_policy(query: str, top_k: int = 3) -> List[Document]:
    """
    主入口：给一个自然语言查询，返回最相关的 top_k 条政策 Document。
    每个 Document 带 metadata（section/chapter 等字段，标注来源章节）。
    """
    retriever = get_retriever(top_k=top_k)
    docs = retriever.invoke(query)
    return docs