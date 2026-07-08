"""多租户隔离中间件。

对应文章第四节。铁律：

  tenant_id 永远不从用户 prompt 或工具参数里取——永远从 JWT 解析出的
  user_context 里取。做错这条，攻击者通过 Prompt Injection 改 tenant_id
  就能跨租户读数据（SaaS 厂商最大的合规事故源）。

演示：工具查询强制注入 user_context 的 tenant_id；向量库查询强制带 tenant 过滤。
零依赖。复用 jwt_chain 的 ToolContext。
"""
from __future__ import annotations

from dataclasses import dataclass

from jwt_chain import ToolContext, UserClaims


class TenantIsolationError(Exception):
    pass


# ---------------------------------------------------------------------------
# mock 数据存储：所有租户共享表，靠 tenant_id 区分（最弱模式，最依赖应用层正确性）
# ---------------------------------------------------------------------------
_ROWS = [
    {"id": 1, "tenant_id": "acme", "content": "acme 的合同"},
    {"id": 2, "tenant_id": "acme", "content": "acme 的客户"},
    {"id": 3, "tenant_id": "globex", "content": "globex 的机密文档"},
]

_VECTORS = [
    {"chunk": "acme 内部知识库片段", "tenant_id": "acme"},
    {"chunk": "globex 内部知识库片段", "tenant_id": "globex"},
]


def query_data(filters: dict, tool_context: ToolContext) -> list:
    """强制从 context 注入 tenant_id —— 忽略 filters 里任何 tenant_id。"""
    if "tenant_id" in filters:
        # 攻击信号：参数里试图指定 tenant_id
        raise TenantIsolationError(
            f"检测到工具参数携带 tenant_id={filters['tenant_id']}，拒绝（可能是注入攻击）"
        )
    tenant_id = tool_context.user.tenant_id  # 唯一可信来源
    return [r for r in _ROWS if r["tenant_id"] == tenant_id]


def vector_search(query: str, tool_context: ToolContext, k: int = 5) -> list:
    """向量检索强制带 tenant 过滤，漏掉这层 = A 公司搜到 B 公司文档。"""
    tenant_id = tool_context.user.tenant_id
    hits = [v for v in _VECTORS if v["tenant_id"] == tenant_id]
    return hits[:k]


def _ctx(tenant: str) -> ToolContext:
    user = UserClaims(f"u_{tenant}", ["member"], ["data.read"], tenant_id=tenant)
    return ToolContext(user=user, user_jwt="<jwt>", acting_agent="rag_agent")


def main() -> None:
    print("=" * 60)
    print("多租户隔离中间件演示")
    print("=" * 60)

    acme = _ctx("acme")
    globex = _ctx("globex")

    print("\n[正常] acme 用户查询：")
    print("  ", query_data({"status": "active"}, acme))
    print("[正常] globex 用户查询：")
    print("  ", query_data({}, globex))

    print("\n[攻击] 参数里注入 tenant_id=globex（acme 用户想越权）：")
    try:
        query_data({"tenant_id": "globex"}, acme)
    except TenantIsolationError as e:
        print("  已拒绝:", e)

    print("\n[向量库] acme 用户检索（强制 tenant 过滤）：")
    print("  ", vector_search("知识库", acme))

    print("\n铁律：tenant_id 只从 JWT/user_context 取，工具参数携带 tenant_id 一律视为攻击。")


if __name__ == "__main__":
    main()
