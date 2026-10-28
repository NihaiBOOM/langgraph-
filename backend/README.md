# 智能售后工单系统 - 后端

## 技术栈

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL 16
- Pydantic Settings

## 数据库配置

### 1. 确保 PostgreSQL 已启动

```powershell
# 检查 postgresql-x64-16 服务
Get-Service -Name postgresql-x64-16
# 如果没启动：Start-Service postgresql-x64-16
```

### 2. 创建数据库

```powershell
$env:PGPASSWORD='123456'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -U postgres -c "CREATE DATABASE after_sales;"
```

如果数据库已存在会报 "already exists"，可以忽略。

### 3. 配置连接

默认连接串已在 `app/core/config.py` 中硬编码，生产环境请复制 `.env.example` 为 `.env` 并填入：

```properties
DATABASE_URL=postgresql+psycopg://postgres:123456@localhost:5432/after_sales
```

## 迁移命令（Alembic）

### 首次迁移（当前仓库已完成）

```powershell
cd backend
D:\pyxuexi\langgraph\.venv\Scripts\python.exe -m alembic upgrade head
```

### 以后修改模型后的流程

```powershell
# 1. 改 models/*.py 里的 ORM 模型

# 2. 自动检测差异，生成迁移脚本
D:\pyxuexi\langgraph\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "描述这次变更"

# 3. 执行迁移
D:\pyxuexi\langgraph\.venv\Scripts\python.exe -m alembic upgrade head

# 4. 回滚到上一个版本（慎用）
D:\pyxuexi\langgraph\.venv\Scripts\python.exe -m alembic downgrade -1

# 5. 查看当前版本
D:\pyxuexi\langgraph\.venv\Scripts\python.exe -m alembic current
```

### 验证迁移结果

```powershell
# 列出所有业务表
$env:PGPASSWORD='123456'
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -U postgres -d after_sales -c "\dt"

# 查看表结构示例
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -U postgres -d after_sales -c "\d users"
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -U postgres -d after_sales -c "\d tickets"
```

## 当前业务表一览

| 表名 | 用途 | 关键约束 |
|---|---|---|
| users | 用户 | username 唯一 |
| products | 商品 | sku 唯一 |
| orders | 订单 | order_no 唯一, FK → users + products |
| chat_sessions | 会话 | user_id 唯一(一对一), thread_id 唯一 |
| chat_messages | 消息历史 | FK → chat_sessions |
| tickets | 工单 | ticket_no 唯一, FK → users + orders + chat_sessions |
| ticket_logs | 工单操作日志 | FK → tickets |

## 启动后端

```powershell
cd backend
D:\pyxuexi\langgraph\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- 健康检查: http://127.0.0.1:8000/api/health
- Swagger 文档: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc