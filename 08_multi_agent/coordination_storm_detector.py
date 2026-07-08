"""协调风暴检测器：识别 Worker 不停回询 Orchestrator 的失控状态。

对应文章第 08 篇「五、多 Agent 的几个生产杀手 · 协调风暴」。

Worker 遇到问题不断问 Orchestrator，Orchestrator 又不断补充，
协调成本超过执行成本。治法：一次性下发足够上下文 + 限制回询次数。
复用 src/agent_code/multi_agent.py 的 CoordinationStormDetector
（按消息里的问号统计每个 Agent 的提问次数）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.multi_agent import AgentMessage, CoordinationStormDetector


def main() -> None:
    detector = CoordinationStormDetector(max_questions_per_agent=2)

    healthy = [
        AgentMessage("worker_a", "orchestrator", "开始执行子任务"),
        AgentMessage("worker_a", "orchestrator", "需要确认输出格式吗?"),
        AgentMessage("worker_b", "orchestrator", "已完成，无疑问"),
    ]
    print("=== 正常协作 ===")
    print(f"  风暴 Agent: {detector.detect(healthy) or '无'}")

    storm = [
        AgentMessage("worker_a", "orchestrator", "参数是哪个?"),
        AgentMessage("worker_a", "orchestrator", "路径在哪?"),
        AgentMessage("worker_a", "orchestrator", "还要再确认一下?"),
        AgentMessage("worker_a", "orchestrator", "这个也不清楚?"),
    ]
    print("\n=== 协调风暴 ===")
    flagged = detector.detect(storm)
    print(f"  被标记的 Agent: {flagged}")
    print("  处置：切断回询，一次性补齐上下文重发，或降级为人工介入。")


if __name__ == "__main__":
    main()
