"""
RAG 检索层 —— 售后政策知识库查询

调用链：retrieve_policy(query) → DashScope Embedding → Chroma 向量相似度 → 返回 top_k 条政策片段

知识库来源：knowledge/after_sales_policy.md（Markdown 文件，按章节切分后向量化存入 Chroma）
"""