"""LoopAgent —— 循环模式（draft -> critic -> refine -> ... 直到退出）。

对应文章第三节"Loop —— 循环模式"（本文件聚焦 max_iterations 到顶退出；
escalate 主动退出见 escalate_loop_exit.py）。

真实 ADK 写法：
    from google.adk.workflows import LoopAgent
    refine_loop = LoopAgent(
        name="self_refine",
        agents=[draft_agent, critic_agent, refine_agent],
        max_iterations=5,
    )
每轮把上一轮输出作为下一轮输入，直到 max_iterations 或 escalate。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

try:  # google-adk 导入 try/except 保护
    from google.adk.workflows import LoopAgent  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


@dataclass
class Actions:
    escalate: bool = False


@dataclass
class MockAgent:
    name: str
    fn: object  # (state, actions) -> str

    def run(self, state: dict, actions: Actions) -> str:
        return self.fn(state, actions)


@dataclass
class MockLoopAgent:
    name: str
    agents: list
    max_iterations: int = 5
    events: list = field(default_factory=list)

    def run(self, state: dict) -> dict:
        for it in range(1, self.max_iterations + 1):
            actions = Actions()
            for agent in self.agents:
                out = agent.run(state, actions)
                self.events.append((it, agent.name, out))
                if actions.escalate:
                    self.events.append((it, "LoopAgent", "escalate -> 退出循环"))
                    return state
        self.events.append((self.max_iterations, "LoopAgent", "max_iterations 到顶 -> 退出"))
        return state


def _draft(state, actions):
    state["quality"] = state.get("quality", 0.0) + 0.15
    return f"草稿 v{state.get('round', 1)}"


def _critic(state, actions):
    return f"评审：当前质量分 {state['quality']:.2f}"


def _refine(state, actions):
    state["round"] = state.get("round", 1) + 1
    return "已按评审意见改写"


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 演示 LoopAgent。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    loop = MockLoopAgent(
        "self_refine",
        [MockAgent("draft_agent", _draft),
         MockAgent("critic_agent", _critic),
         MockAgent("refine_agent", _refine)],
        max_iterations=3,  # 本例故意不触发 escalate，演示到顶退出
    )
    state: dict = {}
    loop.run(state)

    print("== 循环事件流（max_iterations=3，未 escalate） ==")
    for it, name, out in loop.events:
        print(f"  轮{it} [{name}] {out}")

    print(f"\n最终质量分：{state['quality']:.2f}（3 轮未达标，靠 max_iterations 兜底退出）")
    print("提前退出（质量达标即 escalate）见 escalate_loop_exit.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
