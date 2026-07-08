"""事实校验：拦截「幻觉传播」这个多 Agent 头号杀手。

对应文章第 08 篇「五、多 Agent 的几个生产杀手 · 幻觉传播」。

一个 Agent 编错事实，后面的 Agent 当真，错误被包装得越来越像真的。
治法：跨 Agent 事实校验——关键事实必须带来源，汇总前做验证。
复用 src/agent_code/multi_agent.py 的 FactVerifier。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.multi_agent import FactVerifier


def main() -> None:
    # 可信事实库（真实系统里来自 RAG / 数据库 / 带来源的检索结果）。
    verifier = FactVerifier(
        trusted_facts={
            "Agent 循环是一个 while 循环",
            "多 Agent 需要明确的协作协议",
        }
    )

    # researcher 汇报的一组声明，其中夹了一条编造的。
    claims = [
        "Agent 循环是一个 while 循环",
        "多 Agent 需要明确的协作协议",
        "多 Agent 一定比单 Agent 便宜",  # 幻觉
    ]

    results = verifier.verify(claims)
    print("汇总前逐条校验:")
    for claim, ok in results.items():
        mark = "通过" if ok else "未通过来源核验 -> 拦截，不进入汇总"
        print(f"  [{mark}] {claim}")

    verified = [claim for claim, ok in results.items() if ok]
    print(f"\n仅 {len(verified)}/{len(claims)} 条带来源事实进入下游 Agent，阻断幻觉传播。")


if __name__ == "__main__":
    main()
