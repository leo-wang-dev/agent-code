"""Delegation 路由准确率监控。

对应文章第四节"Delegation 的稳定性问题"里的生产经验：
"配合 Callbacks 做路由审计，统计 transfer 准确率"。

本脚本用一组带"期望目标"标注的样例集，跑 mock 路由，统计：
    整体准确率 / 每个 sub_agent 的混淆情况 / 误判样例。
mock 路由故意在"明天出差怎么准备"这类模糊 query 上误判（对齐文章例子），
以展示监控如何暴露 Delegation 的不稳定点。
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from dataclasses import dataclass

try:  # google-adk 导入 try/except 保护
    from google.adk.agents import LlmAgent  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


@dataclass
class Sample:
    query: str
    expected: str


# mock LLM 路由：关键词命中即 transfer；顺序敏感以复现"天气"误判
ROUTES = [
    ("weather_agent", ("天气", "下雨", "气温", "出差")),  # "出差"含"天气"直觉 -> 会误判
    ("greeting_agent", ("你好", "在吗", "hi")),
    ("order_agent", ("订单", "退货", "物流", "发货")),
    ("farewell_agent", ("再见", "拜拜", "bye")),
]


def mock_route(query: str) -> str:
    for target, keywords in ROUTES:
        if any(k in query for k in keywords):
            return target
    return "fallback"


SAMPLES = [
    Sample("今天天气怎么样", "weather_agent"),
    Sample("明天要下雨吗", "weather_agent"),
    Sample("你好在吗", "greeting_agent"),
    Sample("我的订单到哪了", "order_agent"),
    Sample("这个商品能退货吗", "order_agent"),
    Sample("好的再见", "farewell_agent"),
    Sample("明天我要出差，怎么准备", "trip_planner"),  # 应多 agent 协作，却被路由到 weather
    Sample("帮我催一下发货", "order_agent"),
]


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock 演示路由准确率监控。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    total = len(SAMPLES)
    correct = 0
    confusion: dict[str, Counter] = defaultdict(Counter)
    misroutes: list[tuple[str, str, str]] = []

    for s in SAMPLES:
        got = mock_route(s.query)
        confusion[s.expected][got] += 1
        if got == s.expected:
            correct += 1
        else:
            misroutes.append((s.query, s.expected, got))

    print(f"== 路由准确率：{correct}/{total} = {correct / total:.0%} ==\n")

    print("== 混淆矩阵（expected -> got 计数） ==")
    for expected, counter in confusion.items():
        detail = ", ".join(f"{g}×{n}" for g, n in counter.items())
        print(f"  {expected:<14} -> {detail}")

    print("\n== 误判样例（需要优化 description / 加 fallback） ==")
    for query, expected, got in misroutes:
        print(f"  {query!r}: 期望 {expected}，实际 {got}")

    print("\n生产建议：把本统计接到 Callbacks 里持续采集，准确率下降即告警。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
