"""Orchestrator-Worker 拓扑：总控拆解分派汇总，Worker 干具体活。

对应文章第 08 篇「三、三种经典拓扑 · Orchestrator-Worker」。

生产里最常见也最稳：决策权集中在 Orchestrator，容易收敛。
复用 src/agent_code/multi_agent.py 的 OrchestratorWorker（按关键词路由到 Worker）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.multi_agent import OrchestratorWorker, demo_agents


def main() -> None:
    orchestrator = OrchestratorWorker(demo_agents())

    for task in [
        "research and check the risks of the Agent loop",
        "find background on multi-agent systems",
        "just write something",
    ]:
        print(f"\n=== 任务: {task} ===")
        print(f"路由到的 Worker: {orchestrator.route(task)}")
        outputs = orchestrator.run(task)
        for name, output in outputs.items():
            label = "汇总" if name == "orchestrator" else f"Worker[{name}]"
            print(f"  {label}: {output}")


if __name__ == "__main__":
    main()
