import os
from langchain_community.chat_models import ChatTongyi

_DEFAULT_MODEL = os.environ.get("LLM_MODEL", "qwen-plus")
_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")


def get_llm(model: str | None = None, temperature: float = 0.1) -> ChatTongyi:
    """
    构造百炼 DashScope Chat LLM。
    默认模型 qwen-plus，可通过环境变量 LLM_MODEL 覆盖。
    API Key 从环境变量 DASHSCOPE_API_KEY 读取（百炼平台 Key）。
    """
    return ChatTongyi(
        model=model or _DEFAULT_MODEL,
        dashscope_api_key=_API_KEY,
        temperature=temperature,
    )