"""Callback 设在 Agent 上 vs 工具上的对照。

对应文章第四节末"Callback 设在 Agent 上的设计意义"。

关键点：Callback 挂在 Agent 上，不在 Tool 上。原因——同一个工具被多个 Agent
使用，但不同 Agent 需要不同策略。文章例子：
    search_web 工具被两个 Agent 用：
      内部研究 Agent -> 无限制
      客户对话 Agent -> 必须敏感词过滤
把策略写在 Agent 上，让工具保持纯粹，策略按使用场景注入。

本脚本用确定性 mock 复刻两种设计：
    (A) 策略写死在工具里 -> 无法按 Agent 区分（反面）
    (B) 策略作为 Agent 的 callback 注入 -> 同一工具、两套行为（ADK 正解）
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

try:  # google-adk 导入 try/except 保护
    from google.adk.agents import LlmAgent  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False

SENSITIVE = ["身份证", "银行卡", "密码"]


# ---- 纯粹的工具：不含任何策略 ----
def search_web(query: str) -> dict:
    return {"query": query, "results": [f"关于「{query}」的公开资料"]}


# ---- 策略作为 Agent 级 callback ----
def no_op_before_tool(tool_name, tool_args, ctx):
    return None  # 内部研究 Agent：不拦截


def sensitive_filter_before_tool(tool_name, tool_args, ctx):
    q = tool_args.get("query", "")
    if any(s in q for s in SENSITIVE):
        return {"blocked": True, "reason": "查询含敏感词，已拦截"}  # 短路
    return None


@dataclass
class MockAgent:
    name: str
    tools: list
    before_tool_callback: object = None  # 策略挂在 Agent 上
    trace: list = field(default_factory=list)

    def call_tool(self, fn, tool_name, tool_args):
        if self.before_tool_callback:
            short = self.before_tool_callback(tool_name, tool_args, self)
            if short is not None:
                self.trace.append((tool_name, "SHORT-CIRCUIT", short))
                return short
        result = fn(**tool_args)
        self.trace.append((tool_name, "EXECUTED", result))
        return result


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 演示 Callback 挂载位置对照。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    # 同一个 search_web 工具，被两个 Agent 复用，策略各异
    internal = MockAgent("internal_research", tools=[search_web],
                         before_tool_callback=no_op_before_tool)
    customer = MockAgent("customer_chat", tools=[search_web],
                         before_tool_callback=sensitive_filter_before_tool)

    queries = ["ADK 架构", "帮我查身份证归属地"]
    for agent in (internal, customer):
        print(f"== Agent: {agent.name} ==")
        for q in queries:
            r = agent.call_tool(search_web, "search_web", {"query": q})
            print(f"   query={q!r} -> {r}")
        print()

    print("对照结论：")
    print("  同一个纯粹的 search_web，internal 无限制、customer 敏感词拦截；")
    print("  策略挂在 Agent 的 before_tool_callback 上 -> 工具零改动，关注点分离。")
    print("  若把过滤写进工具本身，则无法让 internal 免检 —— 这正是反面。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
