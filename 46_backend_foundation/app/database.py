"""数据库引擎/会话 —— SQLAlchemy 2.0 async。

对应文章第 46 篇三层结构的 Repository/Model 层基础设施。
依赖由 main.py 入口守护；本模块被导入时才需要 sqlalchemy。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """FastAPI 依赖：每请求一个 session。"""
    async with SessionLocal() as session:
        yield session
