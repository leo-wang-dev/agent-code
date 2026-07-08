"""initial core tables (tenants / users / agents)

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00

对应文章第 46 篇 补强5、数据库迁移管理。
这是首个迁移，创建后端骨架直接用到的三张表；其余 13 张表 DDL 见 ../schema.sql，
可用 `alembic revision --autogenerate` 从 app.models 增量生成。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("plan", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, sa.ForeignKey("tenants.id")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255)),
        sa.Column("role", sa.String(20), server_default="user"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_users_tenant", "users", ["tenant_id"])
    op.create_table(
        "agents",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, sa.ForeignKey("tenants.id")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("system_prompt", sa.Text),
        sa.Column("model", sa.String(50)),
        sa.Column("temperature", sa.Float, server_default="0.2"),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_agents_tenant", "agents", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("idx_agents_tenant", table_name="agents")
    op.drop_table("agents")
    op.drop_index("idx_users_tenant", table_name="users")
    op.drop_table("users")
    op.drop_table("tenants")
