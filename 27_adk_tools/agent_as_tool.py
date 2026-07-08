"""agent_as_tool 完整封装示例 —— 把整个 Agent 包成工具（AgentTool）。

对应文章第三节"agent_as_tool"。

真实 ADK 写法：
    from google.adk.tools import AgentTool
    reviewer_agent = LlmAgent(name="reviewer", instruction="审核报告…",
                              tools=[fact_check_tool, citation_check_tool])
    reviewer_tool = AgentTool(agent=reviewer_agent)
    coordinator = LlmAgent(name="coordinator",
                           tools=[search_web, reviewer_tool, publish_tool])

调用 reviewer_tool 时 ADK 启动一个完整的 reviewer 子运行，结果作为工具返回值
返回给 coordinator；控制权始终在 coordinator（区别于 Delegation 的整段转移）。

本脚本用确定性 mock 复刻：AgentTool 封装 + 子 Agent 独立上下文 + 隔离性对比。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

try:  # google-adk 导入 try/except 保护
    from google.adk.tools import AgentTool  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


@dataclass
class MockLlmAgent:
    name: str
    instruction: str
    tools: list = field(default_factory=list)
    messages: list = field(default_factory=list)  # 子 Agent 独立 messages（隔离）

    def run(self, task: str) -> str:
        self.messages.append(f"user: {task}")
        # 确定性子运行：按 instruction 加工，调用自己的工具
        tool_notes = [t(task) for t in self.tools]
        reply = f"[{self.name}] 完成「{task}」；工具结论：{'; '.join(tool_notes)}"
        self.messages.append(f"assistant: {reply}")
        return reply


class AgentTool:
    """把一个 Agent 包成工具：对调用方而言与普通工具无异。"""

    def __init__(self, agent: MockLlmAgent) -> None:
        self.agent = agent
        self.__name__ = agent.name  # 让它像普通函数工具一样有 name

    def __call__(self, task: str) -> str:
        # 启动一次完整子运行；只把返回值交回主 Agent（隔离内部对话）
        return self.agent.run(task)


# ---- 子 Agent 的普通工具 ----
def fact_check_tool(text: str) -> str:
    return "事实核查:无明显错误"


def citation_check_tool(text: str) -> str:
    return "引用核查:引用齐全"


# ---- 主 Agent 的普通工具 ----
def search_web(query: str) -> str:
    return f"搜索到关于「{query}」的资料"


def publish_tool(text: str) -> str:
    return "已发布"


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 演示 AgentTool 封装。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    reviewer_agent = MockLlmAgent(
        name="reviewer",
        instruction="审核报告，找出事实性错误",
        tools=[fact_check_tool, citation_check_tool],
    )
    reviewer_tool = AgentTool(agent=reviewer_agent)

    coordinator = MockLlmAgent(
        name="coordinator",
        instruction="协调研究、审核、发布",
        tools=[search_web, reviewer_tool, publish_tool],
    )

    print("== coordinator 的工具列表（reviewer_tool 与普通工具同形） ==")
    for t in coordinator.tools:
        print(f"  - {getattr(t, '__name__', t)}")

    print("\n== 一次协调流程 ==")
    print("  ", search_web("ADK 工具体系"))
    review_result = reviewer_tool("这份 ADK 报告")   # 主 Agent 把审核当工具调用
    print("  ", review_result)
    print("  ", publish_tool("报告"))

    print("\n== 隔离性验证：子 Agent 的内部对话不进主 Agent ==")
    print("   reviewer.messages =", reviewer_agent.messages)
    print("   coordinator.messages =", coordinator.messages, "（未被 reviewer 内部对话污染）")

    print("\n== AgentTool vs Delegation ==")
    print("   AgentTool  : 控制权留在主 Agent，子任务一次完成，上下文隔离")
    print("   Delegation : transfer_to_agent 整段控制权转移，上下文共享")
    return 0


if __name__ == "__main__":
    sys.exit(main())
