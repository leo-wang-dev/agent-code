"""行为白名单引擎 —— 防御层 4（输出端行为监控）。

对应文章第六节。Agent 在某次会话中只能做某些事，超出范围立即告警/阻断。
配合行为异常检测（行为指纹）：单会话工具调用次数、修改类工具次数、Token 消耗
等突破阈值就告警。

零依赖，可运行。
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# 各角色允许的行为（对应文章 ALLOWED_BEHAVIORS）
# ---------------------------------------------------------------------------
ALLOWED_BEHAVIORS = {
    "customer_service_agent": {
        "tools": ["query_order", "query_kb", "create_ticket"],
        "max_calls_per_session": 30,
        "no_modifications": True,  # 不能调任何修改类工具
        "requires_hitl": [],
    },
    "admin_agent": {
        "tools": ["query_order", "query_kb", "delete_data", "refund", "modify_user"],
        "max_calls_per_session": 50,
        "no_modifications": False,
        "requires_hitl": ["delete_data", "refund", "modify_user"],
    },
}

MODIFY_TOOLS = {"delete_data", "refund", "modify_user", "update_profile"}

# 行为异常阈值
THRESHOLDS = {
    "max_calls": 30,
    "max_modify_calls": 3,
    "max_tokens": 100_000,
}


@dataclass
class SessionState:
    agent_role: str
    tool_calls: int = 0
    modify_calls: int = 0
    tokens: int = 0
    alerts: list[str] = field(default_factory=list)


@dataclass
class Decision:
    allowed: bool
    action: str  # allow / block / require_hitl
    reason: str = ""


def validate_action(state: SessionState, tool: str, args: dict | None = None) -> Decision:
    rules = ALLOWED_BEHAVIORS.get(state.agent_role)
    if rules is None:
        return Decision(False, "block", f"未知角色 {state.agent_role}")

    # 1. 工具是否在白名单
    if tool not in rules["tools"]:
        state.alerts.append(f"未授权工具：{tool}")
        return Decision(False, "block", f"Agent 尝试调用未授权工具 {tool}")

    # 2. 是否修改类工具但角色禁止修改
    if rules["no_modifications"] and tool in MODIFY_TOOLS:
        state.alerts.append(f"越权修改：{tool}")
        return Decision(False, "block", f"{state.agent_role} 不允许调用修改类工具")

    # 3. 高危工具需走 HITL
    if tool in rules["requires_hitl"]:
        return Decision(True, "require_hitl", f"{tool} 属高危操作，需人工确认")

    # 4. 频次/指纹阈值
    state.tool_calls += 1
    if tool in MODIFY_TOOLS:
        state.modify_calls += 1
    if state.tool_calls > rules["max_calls_per_session"]:
        state.alerts.append("单会话工具调用超限")
        return Decision(False, "block", "工具调用次数超过会话上限")
    if state.modify_calls > THRESHOLDS["max_modify_calls"]:
        state.alerts.append("修改类工具调用异常")
        return Decision(False, "block", "修改类工具调用次数异常")

    return Decision(True, "allow", "行为在白名单内")


def main() -> None:
    print("=" * 56)
    print("行为白名单引擎演示")
    print("=" * 56)

    print("\n[客服 Agent]")
    cs = SessionState("customer_service_agent")
    for tool in ["query_order", "query_kb", "refund", "create_ticket"]:
        d = validate_action(cs, tool)
        print(f"  {tool:<14} -> {d.action:<12} {d.reason}")

    print("\n[管理员 Agent]")
    admin = SessionState("admin_agent")
    for tool in ["query_order", "refund", "delete_data"]:
        d = validate_action(admin, tool)
        print(f"  {tool:<14} -> {d.action:<12} {d.reason}")

    print(f"\n客服会话告警：{cs.alerts or '无'}")


if __name__ == "__main__":
    main()
