"""Token 预算：多 Agent 要全局预算，而不是每个 Agent 各管各的。

对应文章第 08 篇「五、多 Agent 的几个生产杀手 · 成本爆炸」。

单 Agent 跑 5 轮，多 Agent 可能是 5 个 Agent 各跑 5 轮，成本瞬间乘起来。
治法：全局 token 预算。复用 src/agent_code/multi_agent.py 的 MultiAgentTokenBudget，
所有 Agent 共享同一个预算池，池空即拒绝后续调用。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.multi_agent import MultiAgentTokenBudget


def main() -> None:
    budget = MultiAgentTokenBudget(total_budget=60)
    workload = [
        ("researcher", "collect three sources about multi agent systems"),
        ("outliner", "build a three section outline from the notes"),
        ("writer", "write a long draft " * 10),
        ("reviewer", "final review pass over the whole draft again"),
    ]

    print(f"全局预算: {budget.total_budget} tokens（所有 Agent 共享一个池）\n")
    for agent, text in workload:
        ok = budget.charge(agent, text)
        status = "已计费" if ok else "预算耗尽 -> 拒绝该 Agent 继续调用"
        print(f"  {agent}: {status}, 全局剩余 {budget.remaining()}")

    print("\n各 Agent 已用量:")
    for agent, used in budget.used_by_agent.items():
        print(f"  {agent}: {used} tokens")


if __name__ == "__main__":
    main()
