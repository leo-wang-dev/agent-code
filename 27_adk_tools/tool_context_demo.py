"""ToolContext 完整用法 demo —— 工具的"运行时入口"。

对应文章第二节"ToolContext"。演示 ToolContext 的四大能力：
    1. 读写 state（带 4 作用域：无前缀 / user: / app: / temp:）
    2. actions 影响流程（escalate / skip_summarization / state_delta /
       artifact_delta / transfer_to_agent）
    3. save_artifact 保存版本化产物
    4. search_memory 跨会话搜索长期记忆

真实 ADK 里 tool_context 由运行时自动注入到工具函数最后一个参数。
本脚本用确定性 mock ToolContext 复刻这套接口，无需 google-adk / 网络。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

try:  # google-adk 导入 try/except 保护
    from google.adk.tools import ToolContext as _RealToolContext  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


@dataclass
class Actions:
    escalate: bool = False
    skip_summarization: bool = False
    transfer_to_agent: str | None = None
    state_delta: dict = field(default_factory=dict)
    artifact_delta: dict = field(default_factory=dict)


class ToolContext:
    """mock ADK ToolContext。"""

    def __init__(self, state: dict, memory: list[str]) -> None:
        self.state = state
        self.actions = Actions()
        self._artifacts: dict[str, list[str]] = {}
        self._memory = memory

    def save_artifact(self, name: str, content: str) -> int:
        versions = self._artifacts.setdefault(name, [])
        versions.append(content)
        version = len(versions)  # 每次调用创建新版本
        self.actions.artifact_delta[name] = version
        return version

    def search_memory(self, query: str) -> list[str]:
        return [m for m in self._memory if query in m]


# ---- 示例工具们 ----
def search_with_history(query: str, tool_context: ToolContext) -> dict:
    past = tool_context.state.get("user:search_history", [])
    results = {"results": [f"关于 {query} 的结果"]}
    tool_context.state["user:search_history"] = past + [query]  # user: 跨 session
    tool_context.state["session_notes"] = f"用户最近搜了：{query}"   # session 级
    tool_context.state["temp:raw"] = "中间态"                       # temp: 不持久化
    return results


def quality_gate(tool_context: ToolContext) -> dict:
    quality = tool_context.state.get("draft_quality_score", 0.0)
    if quality > 0.9:
        tool_context.actions.escalate = True          # 退出 LoopAgent
    if tool_context.state.get("critical_error"):
        tool_context.actions.skip_summarization = True  # 不让 LLM 再总结
    return {"quality": quality}


def generate_report(tool_context: ToolContext) -> dict:
    v1 = tool_context.save_artifact("report.md", "# 报告 v1")
    v2 = tool_context.save_artifact("report.md", "# 报告 v2（修订）")
    return {"latest_version": v2, "history_kept": v1}


def search_user_history(query: str, tool_context: ToolContext) -> dict:
    hits = tool_context.search_memory(query)
    return {"historical": hits}


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock ToolContext 演示。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    memory = ["用户上月投诉过物流慢", "用户偏好中文回复", "用户是 VIP"]
    ctx = ToolContext(state={"draft_quality_score": 0.95}, memory=memory)

    print("== 1. 读写 state（4 作用域） ==")
    print("  ", search_with_history("ADK Callbacks", ctx))
    print("   user:search_history =", ctx.state["user:search_history"])
    print("   session_notes       =", ctx.state["session_notes"])

    print("\n== 2. actions 影响流程 ==")
    quality_gate(ctx)
    print("   escalate           =", ctx.actions.escalate)
    print("   skip_summarization =", ctx.actions.skip_summarization)

    print("\n== 3. save_artifact 版本化 ==")
    print("  ", generate_report(ctx))
    print("   artifact_delta =", ctx.actions.artifact_delta)

    print("\n== 4. search_memory 跨会话搜索 ==")
    print("  ", search_user_history("物流", ctx))

    print("\n结论：ToolContext 让工具从无状态函数升级成有运行时入口的能力单元。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
