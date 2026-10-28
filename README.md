# 智能售后工单系统

基于 **LangGraph + FastAPI + Vue 3** 的 AI 智能售后工单系统，支持多 Agent 协作、RAG 知识库问答、工单自动处理等功能。

## 🛠 技术栈

| 层级 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn |
| AI 框架 | LangGraph |
| LLM | 阿里云 DashScope (qwen-plus) |
| Embedding | 阿里云 DashScope (text-embedding-v3) |
| 向量数据库 | ChromaDB（本地持久化） |
| 关系数据库 | PostgreSQL |
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
│   │   ├── routers/         # API 路由
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
├── .gitignore
├── README.md
└── requirements_full.txt    # 学习环境完整依赖（可选）
```

## 🚀 快速开始

### 前置条件

| 依赖 | 版本 | 安装方式 |
|---|---|---|
| Python | 3.10+ | https://www.python.org/downloads/ |
| Node.js | 18+ | https://nodejs.org/ |
| PostgreSQL | 15+ | https://www.postgresql.org/download/ |

### 1. 克隆项目

```bash
git clone https://github.com/NihaiBOOM/langgraph-.git
cd langgraph
```

### 2. 初始化 PostgreSQL 数据库

```bash
# Windows: 开始菜单搜索 "SQL Shell (psql)" 打开
# Mac/Linux 终端执行
psql -U postgres -c "CREATE DATABASE after_sales;"
```

### 3. 后端启动

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
# 编辑 .env，填入你的 DashScope API Key

# 初始化数据库表
alembic upgrade head

# 初始化知识库（首次运行）
python scripts/ingest_policy.py

# 启动后端服务
uvicorn app.main:app --reload --port 8000
```

后端 API 文档：http://localhost:8000/docs

### 4. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端页面：http://localhost:5173

## ⚙️ 环境变量配置

复制 `backend/.env.example` 为 `backend/.env` 并修改：

| 变量 | 说明 | 必填 |
|---|---|---|
| `DASHSCOPE_API_KEY` | 阿里云百炼平台 API Key | ✅ 是（使用 AI 功能时） |
| `LLM_MODEL` | LLM 模型名称，默认 `qwen-plus` | 否 |
| `EMBEDDING_MODEL` | Embedding 模型名称，默认 `text-embedding-v3` | 否 |
| `DATABASE_URL` | PostgreSQL 连接串，见下方示例 | ✅ 是 |
| `JWT_SECRET_KEY` | JWT 签名密钥，生产环境务必修改 | 否 |

**DATABASE_URL 格式示例：**
```
postgresql+psycopg://用户名:密码@localhost:5432/数据库名
# 默认配置: postgresql+psycopg://postgres:123456@localhost:5432/after_sales
```

## ✨ 功能特性

- 🤖 **多 Agent 协作** — LangGraph 编排，Supervisor 自动路由到 Ticket/Policy/Chat 三个专业 Agent
- 📚 **RAG 知识库** — 售后政策文档向量化存储，Agent 精准检索回答
- 🎫 **工单全流程** — 创建、查询、处理、日志记录
- 💬 **AI 智能对话** — 多轮上下文保留，Agent 状态持久化
- 🔐 **用户认证** — JWT 注册/登录，用户/管理员角色区分
- 🧠 **向量存储** — ChromaDB 本地持久化向量索引
- 🗃️ **Agent Checkpoint** — PostgreSQL 持久化 Agent 对话状态

## 📝 License

MIT