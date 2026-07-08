"""AgentExecutor 重写版：把框架默认的 demo 级循环补成生产级。

对应文章第 07 篇「四、AgentExecutor 替你做了什么」。

框架的 AgentExecutor 帮你维护 messages、解析输出、执行工具、控制最大轮数，
但默认配置多是 demo 级：max_iterations 太大、异常不分类、状态不持久化、
token 无总控、trace 不完整。这里的重写版把这些洞补上：

- 收紧 max_iterations / token_budget / repeated_action_limit（TerminationGuard）
- 工具异常翻译分类（ErrorTranslator：temporary / permission / bad_tool / unknown）
- 状态持久化（JsonStateStore）
- 完整 trace（每步 thought / action / arguments / observation / signature）

复用 src/agent_code 的 rewrite_agent_executor 作为骨架，本文件在外面包上
错误分类、持久化和 trace 落盘，凑齐「AgentExecutor 重写版」这一具名产物。
"""

from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.agent_loop import (
    AgentAction,
    AgentDecision,
    JsonStateStore,
    rewrite_agent_executor,
)
from agent_code.tool_essence import ErrorTranslator, ToolRegistry, default_registry


class ScriptedProductionPlanner:
    """给定一串决策的确定性 planner，用于离线复现循环行为。"""

    def __init__(self, decisions: list[AgentDecision]) -> None:
        self.decisions = decisions

    def decide(self, task: str, observations: list[str]) -> AgentDecision:
        if len(observations) >= len(self.decisions):
            return AgentDecision("信息足够", final_answer=observations[-1])
        return self.decisions[len(observations)]


@dataclass
class ProductionAgentExecutor:
    """生产级 AgentExecutor：守卫 + 错误分类 + 持久化 + trace。"""

    registry: ToolRegistry
    state_store: JsonStateStore
    translator: ErrorTranslator = ErrorTranslator()

    def run(self, task: str, planner: ScriptedProductionPlanner) -> dict[str, Any]:
        # 收紧的默认值，而不是 demo 级的宽松配置。
        agent = rewrite_agent_executor(self.registry, planner)
        result = agent.run(task)

        # 对 trace 里每条错误 observation 做分类，模型才知道该重试还是放弃。
        for step in result.get("trace", []):
            observation = str(step.get("observation", ""))
            if observation.startswith("ERROR:"):
                step["error_class"] = self._classify(observation)

        # 状态持久化：请求断了任务可恢复。
        self.state_store.save({"task": task, "result": result})
        return result

    def _classify(self, observation: str) -> dict[str, str]:
        _, _, name_and_msg = observation.partition("ERROR:")
        name, _, message = name_and_msg.partition(":")
        error_map = {
            "TimeoutError": TimeoutError,
            "PermissionError": PermissionError,
            "KeyError": KeyError,
        }
        error_cls = error_map.get(name, RuntimeError)
        return self.translator.translate(error_cls(message))


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        state_path = Path(tmp) / "executor_state.json"
        executor = ProductionAgentExecutor(
            registry=default_registry(),
            state_store=JsonStateStore(state_path),
        )

        print("=== 正常路径 ===")
        planner = ScriptedProductionPlanner(
            [AgentDecision("先算一下", AgentAction("calculate", {"expression": "(3+5)*2"}))]
        )
        result = executor.run("calculate (3+5)*2", planner)
        print(json.dumps(result, ensure_ascii=False, indent=2))

        print("\n=== 错误分类路径（调不存在的工具）===")
        bad_planner = ScriptedProductionPlanner(
            [AgentDecision("试试未知工具", AgentAction("no_such_tool", {"x": 1}))]
        )
        bad = executor.run("trigger error", bad_planner)
        for step in bad["trace"]:
            print(f"  observation: {step['observation']}")
            print(f"  error_class: {step.get('error_class')}")

        print(f"\n状态已持久化到: {state_path.name}")
        print(f"回读校验: task = {executor.state_store.load().get('task')}")


if __name__ == "__main__":
    main()
