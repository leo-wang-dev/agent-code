"""ReAct 循环：一边想(Thought)，一边动(Action)，一边看结果(Observation)。

对应文章第 07 篇「二、ReAct 的本质」「三、Thought 为什么有用」。

ReAct = Reason + Act。每一轮模型先产出一段 Thought（改变下一步输出分布），
再产出一个 Action（工具调用），代码执行后把 Observation 回填，进入下一轮，
直到模型给出 final_answer 或触发终止防护。

底层复用 src/agent_code/agent_loop.py 的 ReactAgent / TerminationGuard，
本文件负责把「ReAct 循环」这一具名产物单独讲清楚并可离线运行。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.agent_loop import (
    AgentAction,
    AgentDecision,
    ReactAgent,
    TerminationGuard,
)
from agent_code.tool_essence import default_registry, extract_math_expression


class WeatherOrMathPlanner:
    """一个确定性的「模型替身」：看任务先想，再决定调哪个工具。

    真实系统里 decide() 是一次 LLM 调用；这里用规则替代，
    保证离线、无 key、可复现，但循环骨架与生产完全一致。
    """

    def decide(self, task: str, observations: list[str]) -> AgentDecision:
        # 已经拿到观察结果 -> 收束成最终答案（对应"模型判断信息够了"）。
        if observations:
            return AgentDecision(
                thought="工具已返回结果，信息足够，直接回答",
                final_answer=observations[-1],
            )

        lowered = task.lower()
        if any(word in lowered for word in ["weather", "天气", "temperature"]):
            city = "Dubai" if "dubai" in lowered else "Shanghai"
            # Thought 不是废话：它先声明"为什么"要调这个工具，降低乱调概率。
            return AgentDecision(
                thought="用户问的是实时天气，需要先调 get_weather 工具",
                action=AgentAction("get_weather", {"city": city}),
            )
        return AgentDecision(
            thought="这是一道算术题，需要 calculate 工具而不是硬算",
            action=AgentAction("calculate", {"expression": extract_math_expression(task)}),
        )


def build_react_agent() -> ReactAgent:
    return ReactAgent(
        registry=default_registry(),
        planner=WeatherOrMathPlanner(),
        guard=TerminationGuard(max_iterations=5, token_budget=1200, repeated_action_limit=2),
    )


def main() -> None:
    agent = build_react_agent()
    for task in ["What is the weather in Dubai?", "calculate (3+5)*2"]:
        result = agent.run(task)
        print(f"\n=== 任务: {task} ===")
        print(f"状态: {result['status']}  答案: {result.get('answer')}")
        for step in result["trace"]:
            print(
                f"  Thought: {step['thought']}\n"
                f"    Action: {step['action']}({json.dumps(step['arguments'], ensure_ascii=False)})\n"
                f"    Observation: {step['observation']}"
            )


if __name__ == "__main__":
    main()
