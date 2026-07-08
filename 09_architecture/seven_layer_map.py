"""7 层架构图谱：一张图看懂工业级 Agent 系统全貌。

对应文章第 09 篇「三、7 层架构的完整心智模型」。

L1 模型层 / L2 记忆与检索层 / L3 执行层 / L4 编排层 / L5 交互层 /
L6 安全治理层 / L7 评估反馈层。前 5 层决定能不能跑，后 2 层决定敢不敢上线。
复用 src/agent_code/seven_layer.py 的 LAYERS。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.seven_layer import LAYERS


def render_map() -> str:
    lines = []
    for layer in LAYERS:
        gate = "能不能跑" if layer.id in {"L1", "L2", "L3", "L4", "L5"} else "敢不敢上线"
        lines.append(f"┌─ {layer.id} {layer.name}  [{gate}]")
        lines.append(f"│   职责: {layer.responsibility}")
        lines.append(f"│   常见故障: {', '.join(layer.common_failures)}")
        lines.append(f"└   代表工具: {', '.join(layer.example_tools)}")
    return "\n".join(lines)


def main() -> None:
    print("Agent 的 7 层架构图谱\n")
    print(render_map())
    print("\n心智模型：L1 让模型说话 → L2 让它知道该知道的 → L3 让决策变动作")
    print("           → L4 让动作组成任务 → L5 让用户稳定交互")
    print("           → L6 不越权不泄密 → L7 持续变好且知道有没有变差")


if __name__ == "__main__":
    main()
