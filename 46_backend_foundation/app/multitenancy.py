"""多租户中间件（SQLAlchemy 版）—— 从 JWT 提 tenant_id 写入 ContextVar。

对应文章第 46 篇 六、多租户隔离。复用章根 multitenancy.py 的 contextvar，
提供 FastAPI 中间件 + ORM 查询辅助。
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.sql import Select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from multitenancy import (  # noqa: E402
    TenantIsolationError,
    current_tenant_id,
)

from app.security import JWTError, decode_token  # noqa: E402


async def tenant_context_middleware(request, call_next):  # noqa: ANN001
    """FastAPI HTTP 中间件：解析 Authorization，写入当前 tenant 上下文。"""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else ""
    if token:
        try:
            payload = decode_token(token)
            current_tenant_id.set(payload.get("tenant_id"))
        except JWTError:
            pass  # 无效 token 交给鉴权依赖返回 401
    return await call_next(request)


def scoped(model) -> Select:
    """返回自动带 tenant 过滤的 SELECT。业务代码"无脑写"也不跨租户漏数据。"""
    tenant_id = current_tenant_id.get()
    if tenant_id is None:
        raise TenantIsolationError("tenant 上下文未设置")
    return select(model).where(model.tenant_id == tenant_id)
