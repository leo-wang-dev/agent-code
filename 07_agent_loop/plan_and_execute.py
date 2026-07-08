"""Plan-and-Execute：先规划完整步骤，再逐步执行和校验。

对应文章第 07 篇「六、ReAct 和 Plan-and-Execute 怎么选」。

- ReAct：路径不确定，每步看新观察再决定（见 react_loop.py）。
- Plan-and-Execute：路径清楚，先出计划再执行。适合报告生成、数据分析、代码修改。

真实系统里 Planner 是一次 LLM 调用产出计划；这里用 ScriptedPlanner 给定计划，
执行阶段复用 src/agent_code/agent_loop.py 的 PlanAndExecute（真实调用工具注册表）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.agent_loop import AgentAction, PlanAndExecute
from agent_code.tool_essence import default_registry


def make_plan(goal: str) -> list[AgentAction]:
    """确定性「规划」：把一个目标拆成有序步骤。

    真实场景这里是 LLM 产出的 plan；离线版用规则保证可复现。
    """
    plan = [
        AgentAction("calculate", {"expression": "sqrt(16)"}),
        AgentAction("calculate", {"expression": "(3+5)*2"}),
        AgentAction("get_weather", {"city": "Shanghai"}),
    ]
    print(f"目标: {goal}")
    print("规划出的步骤:")
    for index, action in enumerate(plan, start=1):
        print(f"  {index}. {action.tool} {json.dumps(action.arguments, ensure_ascii=False)}")
    return plan


def main() -> None:
    executor = PlanAndExecute(default_registry())
    plan = make_plan("生成一份包含两次计算和天气的报告")
    result = executor.run(plan)
    print("\n执行结果:")
    for step in result["steps"]:
        print(f"  step {step['step']}: {step['tool']} -> {step['result']}")
    print(f"\n最终状态: {result['status']}")


if __name__ == "__main__":
    main()
