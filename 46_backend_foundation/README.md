# 46 · 后端基座：FastAPI + PostgreSQL + JWT

配套文章：《后端基座：FastAPI + PostgreSQL + JWT》（系列第 46 篇）。

离线入口 `run_demo.py` 纯标准库可跑；完整 FastAPI 骨架需装 `fastapi/sqlalchemy` 等
（缺依赖时入口打印安装指引并退出 0，不报错）。

## 文章"包含"清单 → 文件对照

| 文章承诺的产物 | 位置 | 说明 |
|---|---|---|
| 完整 FastAPI 项目骨架 | `app/` | main/config/deps/database/models/schemas/security + api/v1 + services |
| 16 个核心数据库 schema | `schema.sql` | 16 张表 DDL（PG16 + pgvector），`run_demo.py` 会统计 |
| JWT 全套实现 | `jwt_auth.py` | stdlib hmac HS256 教学版（签发/校验/篡改/过期） |
| 多租户中间件 | `multitenancy.py` + `app/multitenancy.py` | ContextVar 自动过滤；SQLAlchemy 版中间件 |
| 流式 SSE 完整 demo | `sse_streaming.py` + `app/api/v1/chat.py` | 离线生成器 + FastAPI SSE 路由 |
| Alembic 配置 | `alembic.ini` + `alembic/` | env.py + script 模板 + 首个迁移 `0001_initial` |

## 快速验证（离线，无需 Postgres）

```bash
python3 run_demo.py            # JWT + 多租户 + 16 表统计 + app 构造
python3 jwt_auth.py           # JWT 全套
python3 multitenancy.py       # 多租户隔离
python3 sse_streaming.py      # SSE 流式
```

## 完整启动（需依赖 + Postgres）

```bash
pip install fastapi 'uvicorn[standard]' sqlalchemy asyncpg 'pydantic[email]' alembic
export DATABASE_URL=postgresql+asyncpg://agent:agent@localhost:5432/agent_platform
alembic upgrade head           # 建表（首个迁移）
psql "$DATABASE_URL" -f schema.sql   # 或直接用完整 16 表 DDL
uvicorn app.main:app --reload
```

## 生产替换点

- `jwt_auth.py`：stdlib 教学版；生产换 `python-jose[cryptography]`/`PyJWT` + `passlib[bcrypt]`。
- `app/services/agent_service.py`：流式为本地 mock；生产接 LLM Gateway + 真实编排器。
- `schema.sql` 的 `VECTOR(1024)` 需 pgvector 扩展；纯 PG 环境注释相关列/索引。
