"""工具级 RBAC 实现。

对应文章第三节。光做"用户身份穿透"不够，还要工具级细粒度权限：
不是所有用户都能用所有工具（销售能查、不能删）。

每次调用 = 用户权限 ∩ Agent 工具池 ∩ Tool 自身权限要求（+ 高危走 HITL）。

零依赖。复用 jwt_chain 的 ToolContext/UserClaims。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from jwt_chain import ToolContext, UserClaims


class PermissionError_(Exception):
    """权限错误（避免覆盖内置 PermissionError 语义，单列）。"""


@dataclass
class Tool:
    name: str
    func: Callable
    required_permission: str | None = None
    requires_hitl: bool = False


@dataclass
class Agent:
    name: str
    tools: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 工具注册表（元数据中声明所需权限）
# ---------------------------------------------------------------------------
def _noop(**kwargs):  # noqa: ANN003
    return {"ok": True}


TOOLS = {
    "query_customer": Tool("query_customer", _noop, required_permission="customer.read"),
    "query_contracts": Tool("query_contracts", _noop, required_permission="contract.read"),
    "create_lead": Tool("create_lead", _noop, required_permission="lead.create"),
    "delete_customer": Tool("delete_customer", _noop, required_permission="customer.delete", requires_hitl=True),
    "modify_contract": Tool("modify_contract", _noop, required_permission="contract.write", requires_hitl=True),
}

AGENTS = {
    "sales_assistant": Agent("sales_assistant", ["query_customer", "query_contracts", "create_lead"]),
    "admin_assistant": Agent("admin_assistant", ["query_customer", "delete_customer", "modify_contract"]),
}

# 用户能用哪些 Agent
USER_AGENT_ACCESS = {
    "sales": {"sales_assistant"},
    "admin": {"sales_assistant", "admin_assistant"},
}


def can_use_agent(user: UserClaims, agent_name: str) -> bool:
    return any(agent_name in USER_AGENT_ACCESS.get(role, set()) for role in user.roles)


def check_call_permission(user: UserClaims, agent: Agent, tool: Tool, args: dict) -> str:
    """四步双向校验，返回 'allow' 或 'require_hitl'，失败抛异常。"""
    # 1. Agent 是否有这个工具
    if tool.name not in agent.tools:
        raise PermissionError_(f"Agent {agent.name} 没有工具 {tool.name}")
    # 2. 用户是否能用该 Agent
    if not can_use_agent(user, agent.name):
        raise PermissionError_(f"用户无权使用 {agent.name}")
    # 3. 用户是否有该 Tool 的权限
    if tool.required_permission and tool.required_permission not in user.permissions:
        raise PermissionError_(f"用户缺少权限 {tool.required_permission}（{tool.name}）")
    # 4. 高危操作走 HITL
    if tool.requires_hitl:
        return "require_hitl"
    return "allow"


def main() -> None:
    print("=" * 60)
    print("工具级 RBAC 演示（用户 ∩ Agent ∩ Tool）")
    print("=" * 60)

    sales_user = UserClaims("u_sales", ["sales"], ["customer.read", "contract.read", "lead.create"], "acme")
    admin_user = UserClaims("u_admin", ["admin"], ["customer.read", "customer.delete", "contract.write"], "acme")

    trials = [
        (sales_user, "sales_assistant", "query_customer"),
        (sales_user, "sales_assistant", "delete_customer"),  # Agent 没这个工具
        (sales_user, "admin_assistant", "delete_customer"),  # 用户无权用该 Agent
        (admin_user, "admin_assistant", "delete_customer"),  # 允许但走 HITL
    ]
    for user, agent_name, tool_name in trials:
        agent = AGENTS[agent_name]
        tool = TOOLS[tool_name]
        try:
            result = check_call_permission(user, agent, tool, {})
            print(f"  [{result:<12}] {user.user_id} → {agent_name} → {tool_name}")
        except PermissionError_ as e:
            print(f"  [DENY        ] {user.user_id} → {agent_name} → {tool_name}: {e}")


if __name__ == "__main__":
    main()
