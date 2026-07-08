"""终止防护：工业级至少要有四层，让 Agent「会安全地停」。

对应文章第 07 篇「五、终止条件是硬骨头」。

- 第一层：最大迭代次数    -> 不让 Agent 无限跑
- 第二层：总 token 预算   -> 整个任务预算，不是每轮预算
- 第三层：重复动作检测    -> 同工具同参数反复调 = 循环卡住
- 第四层：业务状态机      -> 只允许合法状态跳转（本文件用 allowed_transitions 演示）

前三层复用 src/agent_code/agent_loop.py 的 TerminationGuard；
第四层是业务约束，作为具名产物在这里补齐并可离线运行。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.agent_loop import TerminationGuard


@dataclass
class BusinessStateMachine:
    """第四层：业务状态机。只能按合法状态跳转，不让模型自由发挥。"""

    allowed_transitions: dict[str, set[str]]
    state: str = "start"
    history: list[str] = field(default_factory=list)

    def transition(self, target: str) -> bool:
        if target in self.allowed_transitions.get(self.state, set()):
            self.history.append(target)
            self.state = target
            return True
        return False  # 非法跳转 -> 终止/拒绝


def demo_layer_1_and_2() -> None:
    print("=== 第一层 max_iterations / 第二层 token_budget ===")
    guard = TerminationGuard(max_iterations=3, token_budget=200, repeated_action_limit=99)
    trace = []
    for i in range(1, 6):
        reason = guard.check(trace)
        if reason:
            print(f"  第 {i} 轮前触发终止: {reason}")
            break
        trace.append({"step": i, "payload": "x" * 60, "action_signature": f"tool:{i}"})
    else:
        print("  未触发终止")


def demo_layer_3() -> None:
    print("\n=== 第三层 重复动作检测 ===")
    guard = TerminationGuard(max_iterations=99, token_budget=10_000, repeated_action_limit=2)
    trace = [
        {"action_signature": "get_weather:{'city':'SH'}"},
        {"action_signature": "get_weather:{'city':'SH'}"},
    ]
    print(f"  连续两次相同动作 -> {guard.check(trace)}")


def demo_layer_4() -> None:
    print("\n=== 第四层 业务状态机 ===")
    machine = BusinessStateMachine(
        allowed_transitions={
            "start": {"collect_info"},
            "collect_info": {"quote", "start"},
            "quote": {"pay"},
            "pay": {"done"},
        }
    )
    for target in ["collect_info", "quote", "done"]:
        ok = machine.transition(target)
        note = "允许" if ok else "非法跳转 -> 拒绝并终止"
        print(f"  {machine.history[-1] if ok else target}: {note}")
    print(f"  最终状态: {machine.state}  轨迹: {machine.history}")


def main() -> None:
    demo_layer_1_and_2()
    demo_layer_3()
    demo_layer_4()


if __name__ == "__main__":
    main()
