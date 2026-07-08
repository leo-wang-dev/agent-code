"""FastAPI 入口 —— 装配路由 + 多租户中间件 + 健康检查 + 全局异常。

对应文章第 46 篇 三/七/八 各节。运行：
    uvicorn app.main:app --reload            # 需要 fastapi + uvicorn
    python3 -m app.main                       # 直接跑（缺依赖会打印指引并退出0）

⚠️ 缺 fastapi/sqlalchemy 时不报错，打印安装指引后退出 0。
"""

from __future__ import annotations

import sys

# ---- 依赖守护：缺 fastapi/sqlalchemy 时优雅退出 ----
try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    import sqlalchemy  # noqa: F401
    _DEPS_OK = True
except Exception as _e:  # pragma: no cover
    _DEPS_OK = False
    _IMPORT_ERR = _e


def _print_install_help() -> None:
    print("[缺依赖] 本 FastAPI 骨架需要以下依赖才能启动：")
    print("  pip install fastapi 'uvicorn[standard]' sqlalchemy asyncpg pydantic[email]")
    print("装好后运行：uvicorn app.main:app --reload")
    print(f"（导入错误：{_IMPORT_ERR}）")


def create_app():
    """构造并返回 FastAPI 应用。"""
    from app.api.v1 import agents, auth, chat
    from app.multitenancy import tenant_context_middleware

    app = FastAPI(title="LLMOps Platform API", version="0.1.0")

    # 多租户上下文中间件
    app.middleware("http")(tenant_context_middleware)

    # 路由装配
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(agents.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")

    @app.get("/api/v1/health")
    async def health() -> dict:
        # 生产：真去 ping db/redis/gateway
        return {"status": "ok", "checks": {"db": "skipped", "redis": "skipped"}}

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"error": "Internal error"})

    return app


# 模块级 app（供 uvicorn app.main:app 引用）
app = create_app() if _DEPS_OK else None


if __name__ == "__main__":
    if not _DEPS_OK:
        _print_install_help()
        sys.exit(0)
    print("FastAPI app 已构造成功。启动请用：uvicorn app.main:app --reload")
    print(f"已注册路由数: {len(app.routes)}")
