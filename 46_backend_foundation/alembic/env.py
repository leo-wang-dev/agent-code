"""Alembic 迁移环境 —— 对应文章第 46 篇 补强5。

online/offline 两种模式；target_metadata 指向 app.database.Base 以支持 autogenerate。
连接串优先取环境变量 DATABASE_URL（去掉 async 驱动后缀，迁移用同步驱动）。
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# 让 alembic 能 import 到 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 用环境变量覆盖连接串（把 asyncpg 换成同步 psycopg2 供迁移用）
_env_url = os.environ.get("DATABASE_URL")
if _env_url:
    config.set_main_option("sqlalchemy.url", _env_url.replace("+asyncpg", ""))

try:
    from app.database import Base  # noqa: E402
    import app.models  # noqa: F401,E402  确保模型被注册
    target_metadata = Base.metadata
except Exception:
    # 缺依赖时仍允许 alembic 命令行加载本文件（例如查看 help）
    target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
