"""Agent-to-Agent 权限传递与降级。

对应文章第五节。多 Agent 系统里一个 Agent 调另一个时，身份和权限怎么传：

  错误：用 Agent 服务账号 → sub_agent 不知道是哪个用户（身份断链）。
  正确：用户身份通过 ToolContext 透传 → 每个 sub_agent/Tool 都能做正确权限判断。
  但要"权限降级"：orchestrator 高权限，调 sub_agent 时只传必要权限（最小权限原则）。

零依赖。复用 jwt_chain 的 ToolContext/UserClaims。
"""
from __future__ import annotations

from dataclasses import replace

from jwt_chain import ToolContext, UserClaims


def with_limited_permissions(ctx: ToolContext, only: list[str]) -> ToolContext:
    """派生一个降权 context：权限收窄到 only 与原权限的交集。"""
    allowed = [p for p in ctx.user.permissions if p in set(only)]
    limited_user = replace(ctx.user, permissions=allowed)
    return replace(ctx, user=limited_user)


def sub_agent_invoke(name: str, query: str, tool_context: ToolContext) -> dict:
    """sub_agent 拿到透传的用户身份，按 context 里的权限行事。"""
    return {
        "sub_agent": name,
        "acting_for_user": tool_context.user.user_id,  # 身份没断
        "effective_permissions": tool_context.user.permissions,
        "query": query,
    }


def orchestrator(query: str, tool_context: ToolContext) -> dict:
    # 1. 透传：调只读检索 sub_agent，但只给 read_only 权限（降级）
    limited = with_limited_permissions(tool_context, only=["contract.read", "customer.read"])
    retrieval = sub_agent_invoke("retrieval_agent", query, limited)

    # 2. 全权透传：调需要完整权限的执行 sub_agent
    execution = sub_agent_invoke("execution_agent", query, tool_context)

    return {"retrieval": retrieval, "execution": execution}


def main() -> None:
    print("=" * 60)
    print("Agent-to-Agent 权限透传与降级演示")
    print("=" * 60)

    user = UserClaims(
        "u_2001",
        ["admin"],
        ["contract.read", "customer.read", "contract.write", "customer.delete"],
        tenant_id="acme",
    )
    ctx = ToolContext(user=user, user_jwt="<jwt>", acting_agent="orchestrator")

    result = orchestrator("处理这批合同", ctx)
    print("\n原始用户权限：", user.permissions)
    print("\n检索 sub_agent（降级为只读）：")
    print("  身份:", result["retrieval"]["acting_for_user"])
    print("  有效权限:", result["retrieval"]["effective_permissions"])
    print("\n执行 sub_agent（全权透传）：")
    print("  身份:", result["execution"]["acting_for_user"])
    print("  有效权限:", result["execution"]["effective_permissions"])

    print("\n最小权限原则：Agent 互调永远只传必要权限；身份始终指向原始用户。")


if __name__ == "__main__":
    main()
