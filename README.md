# 智能售后工单系统

基于 **LangGraph + FastAPI + Vue 3** 的 AI 智能售后工单系统，支持多 Agent 协作、RAG 知识库问答、工单自动处理等功能。

## 🛠 技术栈

| 层级 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn |
| AI 框架 | LangGraph |
| LLM | 阿里云 DashScope (qwen-plus) |
| Embedding | 阿里云 DashScope (text-embedding-v3) |
| 向量数据库 | ChromaDB |
| 关系数据库 | SQLite（默认）/ PostgreSQL |
| ORM | SQLAlchemy + Alembic |
| 前端框架 | Vue 3 + Vite + Vue Router + Axios |
| 认证 | JWT |

## 📂 目录结构

```
langgraph/
├── backend/                  # 后端代码
│   ├── app/
│   │   ├── ai/              # LLM 调用、Prompt、工具定义
│   │   ├── core/            # 配置、安全、认证核心模块
│   │   ├── db/              # 数据库连接与 Base
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── rag/             # RAG 检索增强生成
│   │   ├── routers/        # API 路由
│   │   ├── schemas/         # Pydantic 请求/响应模型
│   │   └── services/        # 业务逻辑（含 LangGraph 多 Agent）
│   ├── knowledge/           # 知识库文档
│   ├── scripts/             # 数据初始化脚本
│   ├── alembic/             # 数据库迁移
│   └── tests/               # 测试用例
├── frontend/                # 前端代码 (Vue 3)
│   └── src/
│       ├── views/           # 页面组件
│       ├── router/          # 路由配置
│       └── utils/           # 工具函数
└── .gitignore
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/NihaiBOOM/langgraph-.git
cd langgraph
```

### 2. 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate   # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env，填入你的 DashScope API Key 等配置

# 初始化数据库
alembic upgrade head

# 初始化知识库（首次运行）
python scripts/ingest_policy.py

# 启动后端服务
uvicorn app.main:app --reload --port 8000
```

后端 API 文档访问：http://localhost:8000/docs

### 3. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端页面访问：http://localhost:5173

## ⚙️ 环境变量配置

复制 `backend/.env.example` 为 `backend/.env` 并修改：

| 变量 | 说明 | 必填 |
|---|---|---|
| `DASHSCOPE_API_KEY` | 阿里云百炼平台 API Key | 是（使用 AI 功能时） |
| `LLM_MODEL` | LLM 模型名称，默认 `qwen-plus` | 否 |
| `EMBEDDING_MODEL` | Embedding 模型名称，默认 `text-embedding-v3` | 否 |
| `DATABASE_URL` | 数据库连接串，默认 SQLite | 否 |
| `JWT_SECRET_KEY` | JWT 签名密钥 | 否 |

## ✨ 功能特性

- 🤖 **多 Agent 协作** — LangGraph 编排，不同任务由不同 Agent 处理
- 📚 **RAG 知识库** — 售后政策文档向量化检索，AI 精准回答
- 🎫 **工单管理** — 创建、查询、处理、日志记录全流程
- 💬 **智能对话** — AI 客服自动响应售后问题
- 🔐 **用户认证** — JWT 注册/登录，角色区分（用户/管理员）
- 🧠 **向量存储** — ChromaDB 本地持久化向量索引

## 📝 License

MIT