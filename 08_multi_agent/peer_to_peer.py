"""Peer-to-Peer 拓扑：对等讨论，没有明确总控。

对应文章第 08 篇「三、三种经典拓扑 · Peer-to-Peer」。

demo 里最像「群体智能」，生产里最容易乱：没人拍板、不知何时结束、成本失控。
文章结论：对等协作慎用；若一定要辩论，外面要套一层 Orchestrator 强制收敛。

本文件演示两点：
1. 裸 P2P（复用 src/agent_code/multi_agent.py 的 PeerToPeer）容易停不下来。
2. 加一个 Orchestrator 兜底：设最大轮数 + 收敛判断，强制结束。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.multi_agent import PeerToPeer


def build_debate_agents() -> dict[str, object]:
    # 两个观点会逐步趋同，触发 PeerToPeer 的收敛判断而提前结束。
    return {
        "proposer": lambda text: "方案 A 更稳",
        "critic": lambda text: "方案 A 更稳",
    }


def main() -> None:
    p2p = PeerToPeer(build_debate_agents(), max_rounds=3)
    messages = p2p.run("选 A 还是 B 方案")
    print("Peer-to-Peer 消息流（外层 max_rounds + 收敛判断强制收束）:")
    for message in messages:
        print(f"  {message.sender} -> {message.recipient}: {message.content}")
    print(f"\n共 {len(messages)} 条消息后收束（未套 Orchestrator 时同样话题可能无限打转）")


if __name__ == "__main__":
    main()
