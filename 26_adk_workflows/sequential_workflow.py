"""SequentialAgent —— 流水线模式（A -> B -> C 顺序执行）。

对应文章第一节"Sequential —— 流水线模式"。

真实 ADK 写法：
    from google.adk.workflows import SequentialAgent
    pipeline = SequentialAgent(
        name="content_pipeline",
        agents=[researcher, writer, editor],
    )
数据流靠 output_key + {template} 数据总线：上游 output_key 写入 state，
下游 instruction 里的 {key} 自动从 state 读回替换。

本脚本用确定性 mock 复刻这套"顺序执行 + 数据总线"机制，无需 key/网络。
"""

from __future__ import annotations

import string
import sys
from dataclasses import dataclass, field

try:  # google-adk 导入 try/except 保护
    from google.adk.agents import LlmAgent  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


def _resolve(template: str, state: dict) -> str:
    """把 instruction 里的 {key} 用 state 值替换（数据总线）。"""
    fields = [f for _, f, _, _ in string.Formatter().parse(template) if f]
    safe = {f: state.get(f, f"<缺失:{f}>") for f in fields}
    return template.format(**safe)


@dataclass
class MockLlmAgent:
    name: str
    instruction: str
    output_key: str

    def run(self, state: dict) -> str:
        prompt = _resolve(self.instruction, state)
        # 确定性 mock：输出 = 该节点对已解析 prompt 的加工结果
        output = f"[{self.name}产出] 依据「{prompt}」"
        state[self.output_key] = output
        return output


@dataclass
class SequentialAgent:
    name: str
    agents: list
    events: list = field(default_factory=list)

    def run(self, state: dict) -> dict:
        for agent in self.agents:
            out = agent.run(state)
            self.events.append((agent.name, out))
        return state


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 演示 SequentialAgent。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    researcher = MockLlmAgent("researcher", "研究主题：{topic}", "research_notes")
    writer = MockLlmAgent("writer", "基于研究内容写报告：{research_notes}", "draft_report")
    editor = MockLlmAgent("editor", "润色这份草稿：{draft_report}", "final_report")

    pipeline = SequentialAgent("content_pipeline", [researcher, writer, editor])

    state: dict = {"topic": "ADK 事件流编排"}
    print("初始 state:", state)
    pipeline.run(state)

    print("\n== 顺序执行事件流 ==")
    for name, out in pipeline.events:
        print(f"[{name}] {out}")

    print("\n== 最终 state（数据总线自动衔接） ==")
    for key, value in state.items():
        print(f"  {key} = {value}")

    print("\n结论：只需按顺序传 agents，output_key/{template} 自动衔接数据，无胶水代码。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
