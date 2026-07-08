"""多租户隔离 —— ContextVar 存当前 tenant_id，查询自动加过滤。

对应文章第 46 篇 六、多租户隔离的 ORM 实现。

纯标准库演示核心机制（ContextVar + 强制过滤），不依赖 SQLAlchemy；
app/ 里的中间件复用这里的 contextvar。SQLAlchemy 版见 app/multitenancy.py。

离线可运行：`python3 multitenancy.py`
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field

# 每个请求进来时由中间件从 JWT 里 set，业务代码只管读。
current_tenant_id: ContextVar[int | None] = ContextVar("current_tenant_id", default=None)


class TenantIsolationError(Exception):
    """未设置租户上下文却访问受租户约束的数据。"""


@dataclass
class InMemoryTable:
    """演示用内存表——模拟"所有查询自动加 tenant 过滤"。"""

    rows: list[dict] = field(default_factory=list)

    def insert(self, row: dict) -> dict:
        tenant_id = current_tenant_id.get()
        if tenant_id is None:
            raise TenantIsolationError("插入前必须设置 tenant 上下文")
        stored = {**row, "tenant_id": tenant_id}
        self.rows.append(stored)
        return stored

    def query_tenant(self) -> list[dict]:
        """自动加 tenant 过滤——业务代码"无脑写"也不会跨租户漏数据。"""
        tenant_id = current_tenant_id.get()
        if tenant_id is None:
            raise TenantIsolationError("查询前必须设置 tenant 上下文")
        return [r for r in self.rows if r["tenant_id"] == tenant_id]

    def query_all_admin(self) -> list[dict]:
        """跨租户查询必须显式调用（应极少，且需 admin 审计）。"""
        return list(self.rows)


def set_tenant_from_jwt(payload: dict) -> None:
    """中间件调用：从 decode 后的 JWT payload 提取 tenant_id 写入上下文。"""
    if "tenant_id" in payload:
        current_tenant_id.set(payload["tenant_id"])


def _demo() -> None:
    agents = InMemoryTable()

    # 租户 t1 写入两个 Agent
    current_tenant_id.set(1)
    agents.insert({"name": "客服 Agent"})
    agents.insert({"name": "销售 Agent"})

    # 租户 t2 写入一个
    current_tenant_id.set(2)
    agents.insert({"name": "研究 Agent"})

    print("=== 自动租户过滤 ===")
    current_tenant_id.set(1)
    print("  t1 可见:", [r["name"] for r in agents.query_tenant()])
    current_tenant_id.set(2)
    print("  t2 可见:", [r["name"] for r in agents.query_tenant()])

    print("\n=== 跨租户需显式 admin 查询 ===")
    print("  全部:", [(r["tenant_id"], r["name"]) for r in agents.query_all_admin()])

    print("\n=== 未设上下文时拒绝访问 ===")
    current_tenant_id.set(None)
    try:
        agents.query_tenant()
    except TenantIsolationError as e:
        print(f"  被拒: {e}")


if __name__ == "__main__":
    _demo()
