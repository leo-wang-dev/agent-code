"""escalate 退出循环 demo —— 工具主动向上传递控制权。

对应文章第三节"escalate —— ADK 独家的退出机制"。

真实 ADK 写法：
    def evaluate_quality(state, tool_context) -> dict:
        score = state.get("draft_quality_score", 0)
        if score > 0.9:
            tool_context.actions.escalate = True   # 质量够好，跳出 LoopAgent
        return {"score": score}

escalate = True 让当前控制权向上传递，跳出 LoopAgent 回到父级流程。
本脚本用确定性 mock 复刻：质量分逐轮上升，越过阈值即 escalate 提前退出，
并把每一轮的"控制权转移"记录进事件流（审计可见）。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

try:  # google-adk 导入 try/except 保护
    from google.adk.workflows import LoopAgent  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


@dataclass
class ToolActions:
    escalate: bool = False


@dataclass
class ToolContext:
    state: dict
    actions: ToolActions = field(default_factory=ToolActions)


# ---- 工具：评估质量，达标则 escalate ----
def evaluate_quality(tool_context: ToolContext) -> dict:
    score = tool_context.state.get("draft_quality_score", 0.0)
    if score > 0.9:
        tool_context.actions.escalate = True
    return {"score": score}


@dataclass
class MockLoopAgent:
    name: str
    max_iterations: int = 8
    events: list = field(default_factory=list)

    def run(self, state: dict) -> dict:
        for it in range(1, self.max_iterations + 1):
            # draft -> refine：质量分逐轮提升（确定性）
            state["draft_quality_score"] = round(0.4 + 0.2 * it, 2)
            self.events.append((it, "refine_agent", f"质量分升到 {state['draft_quality_score']}"))

            # critic 用 evaluate_quality 工具判断是否退出
            ctx = ToolContext(state=state)
            result = evaluate_quality(ctx)
            self.events.append((it, "critic_agent", f"评估 score={result['score']}"))
            if ctx.actions.escalate:
                self.events.append((it, "LoopAgent", "收到 escalate=True -> 控制权上交，退出循环"))
                return state
        self.events.append((self.max_iterations, "LoopAgent", "未 escalate，max_iterations 兜底退出"))
        return state


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 演示 escalate 退出循环。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    loop = MockLoopAgent("self_refine", max_iterations=8)
    state: dict = {}
    loop.run(state)

    print("== 事件流（含控制权转移树） ==")
    for it, author, msg in loop.events:
        print(f"  轮{it} [{author}] {msg}")

    exited = any("escalate=True" in m for _, _, m in loop.events)
    print(f"\n退出方式：{'escalate 主动退出' if exited else 'max_iterations 兜底'}"
          f"（最终质量分 {state['draft_quality_score']}）")
    print("要点：退出条件是工具自身语义，不藏在路由函数里；escalate 全程有 Event 记录。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
