"""Delegation —— ADK 招牌的动态 LLM 路由（LlmAgent + sub_agents）。

对应文章第四节"Delegation"。

真实 ADK 写法：
    root_agent = LlmAgent(
        name="orchestrator",
        instruction="根据用户输入决定调用合适的专业 Agent",
        sub_agents=[greeting_agent, weather_agent, farewell_agent],
    )
ADK 自动把每个 sub_agent 的 name+description 注入 root system prompt，
LLM 自主调用 transfer_to_agent(agent_name=...) 转移整段控制权。

本脚本用确定性 mock 路由（关键词匹配代替 LLM 判断）复刻这套委派流程，
并演示自动注入的 system prompt 片段 + fallback 兜底。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

try:  # google-adk 导入 try/except 保护
    from google.adk.agents import LlmAgent  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


@dataclass
class MockSubAgent:
    name: str
    description: str
    keywords: tuple
    reply: str


class MockOrchestrator:
    def __init__(self, name: str, sub_agents: list) -> None:
        self.name = name
        self.sub_agents = sub_agents

    def injected_prompt(self) -> str:
        lines = ["（自动注入到 root_agent 的 system prompt 里）", "你可以委派以下任务："]
        for a in self.sub_agents:
            lines.append(f"  - {a.name}: {a.description}")
        return "\n".join(lines)

    def route(self, message: str) -> tuple[str, str]:
        """mock LLM 决策：命中关键词即 transfer；否则 fallback。"""
        for a in self.sub_agents:
            if any(k in message for k in a.keywords):
                return a.name, a.reply
        return "fallback", "抱歉，我不确定该找谁处理，帮你转人工。"


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 演示 Delegation 路由。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    root = MockOrchestrator(
        "orchestrator",
        [
            MockSubAgent("greeting_agent", "处理用户的问候和闲聊",
                         ("你好", "在吗", "hi"), "你好呀，我在～"),
            MockSubAgent("weather_agent", "查询天气信息",
                         ("天气", "下雨", "气温"), "北京今天多云 22C。"),
            MockSubAgent("farewell_agent", "处理告别",
                         ("再见", "拜拜", "bye"), "再见，祝你顺利！"),
        ],
    )

    print("== 自动注入的委派 system prompt ==")
    print(root.injected_prompt())

    print("\n== 路由演示 ==")
    for msg in ["你好啊", "今天天气怎么样", "好的再见", "帮我算一下贷款利率"]:
        target, reply = root.route(msg)
        arrow = "transfer_to_agent" if target != "fallback" else "fallback 兜底"
        print(f"  用户: {msg}")
        print(f"    -> {arrow}(agent_name={target!r}) -> {reply}")

    print("\n生产经验：description 写清晰、加 fallback、sub_agents 不超过 7-8 个。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
