"""ParallelAgent —— 并行模式（A // B // C 同时执行）。

对应文章第二节"Parallel —— 并行模式"。

真实 ADK 写法：
    from google.adk.workflows import ParallelAgent
    parallel = ParallelAgent(
        name="multi_source_research",
        agents=[search_agent, supplier_agent, web_agent],
    )
每个并行 Agent 写不同 output_key，下游 aggregator 同时引用三个结果。

工程权衡：并发顺序不确定，若写同一字段会 race condition ——
本脚本既演示"各写不同 output_key（安全）"，也复现"共写一字段的竞态"。
"""

from __future__ import annotations

import random
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

try:  # google-adk 导入 try/except 保护
    from google.adk.workflows import ParallelAgent  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


@dataclass
class MockLlmAgent:
    name: str
    output_key: str
    payload: str

    def run(self) -> tuple[str, str]:
        # 确定性内容，但完成顺序不确定（模拟真并发）
        return self.output_key, f"[{self.name}] {self.payload}"


class MockParallelAgent:
    def __init__(self, name: str, agents: list) -> None:
        self.name = name
        self.agents = agents

    def run(self, state: dict) -> dict:
        with ThreadPoolExecutor(max_workers=len(self.agents)) as pool:
            for key, value in pool.map(lambda a: a.run(), self.agents):
                state[key] = value
        return state


def demo_safe() -> None:
    print("== 安全用法：各写不同 output_key ==")
    parallel = MockParallelAgent(
        "multi_source_research",
        [
            MockLlmAgent("search_agent", "search_results", "站内搜索命中 3 条"),
            MockLlmAgent("supplier_agent", "supplier_results", "供应商报价 2 家"),
            MockLlmAgent("web_agent", "web_results", "全网资讯 5 条"),
        ],
    )
    state: dict = {}
    parallel.run(state)
    for key, value in state.items():
        print(f"  {key} = {value}")

    aggregator_instruction = (
        "综合以下信息：{search_results} {supplier_results} {web_results}"
    )
    print("  aggregator 可同时引用：", aggregator_instruction)


def demo_race() -> None:
    print("\n== 反面教材：并行 Agent 共写同一字段 -> race condition ==")
    outcomes = set()
    for _ in range(200):
        state: dict = {}
        agents = [
            MockLlmAgent("fast_agent", "shared", "FAST 的值"),
            MockLlmAgent("slow_agent", "shared", "SLOW 的值"),
        ]
        random.shuffle(agents)  # 完成顺序不确定
        MockParallelAgent("bad", agents).run(state)
        outcomes.add(state["shared"])
    print(f"  200 次运行，state['shared'] 出现过 {len(outcomes)} 种不同结果：")
    for value in sorted(outcomes):
        print(f"    - {value}")
    print("  -> 生产经验：写不同 output_key，或在 aggregator 统一合并 / 上锁。")


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 演示 ParallelAgent。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    demo_safe()
    demo_race()
    print("\n结论：并行整体延迟由最慢 Agent 决定；独立任务写独立字段最安全。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
