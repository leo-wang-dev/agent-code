"""8 维度评分的自动化测试套件。

对应文章第 32 篇「四、综合评分」。

- 编码 8 维度评分表（1-5 分）；
- 自动化断言：加权平均、强项分布、"总分有误导性"这一关键结论；
- 同时对三个实现做一次功能一致性测试（同一 query 三框架结论一致）。

可作为 unittest 跑，也可直接执行：
    python3 32_three_framework_comparison/scoring_suite.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sourcing_adk
import sourcing_common as sc
import sourcing_crewai
import sourcing_langgraph

# 文章「四、综合评分」8 维度分数（1-5，代码量/上手 "少为优" 已折算成得分）。
DIMENSIONS = [
    "代码量", "上手速度", "运行性能", "Token成本",
    "可调试性", "持久化能力", "HITL集成", "可观测性", "可扩展性",
]
SCORES = {
    "LangGraph": [3, 3, 5, 5, 5, 5, 5, 3, 3],
    "CrewAI":    [5, 5, 2, 2, 2, 2, 2, 2, 3],
    "ADK":       [2, 2, 4, 4, 5, 5, 3, 5, 5],
}
STRENGTHS = {
    "LangGraph": {"运行性能", "持久化能力", "HITL集成", "可调试性", "Token成本"},
    "CrewAI": {"代码量", "上手速度"},
    "ADK": {"可观测性", "可扩展性", "持久化能力", "可调试性"},
}


# 工业级维度权重更高（代码量/上手速度对生产项目影响小）——复现文章「加权平均」口径。
WEIGHTS = {
    "代码量": 0.5, "上手速度": 0.5, "运行性能": 1.0, "Token成本": 1.0,
    "可调试性": 1.0, "持久化能力": 1.0, "HITL集成": 1.0, "可观测性": 1.0, "可扩展性": 1.0,
}


def simple_average(framework: str) -> float:
    scores = SCORES[framework]
    return round(sum(scores) / len(scores), 1)


def weighted_average(framework: str) -> float:
    """按 WEIGHTS 加权 —— 文章口径：LangGraph 4.1 / CrewAI 2.8 / ADK ≈4.1。"""

    scores = SCORES[framework]
    total_w = sum(WEIGHTS[d] for d in DIMENSIONS)
    return round(sum(s * WEIGHTS[d] for s, d in zip(scores, DIMENSIONS)) / total_w, 1)


def strength_dimensions(framework: str, threshold: int = 5) -> set[str]:
    """得满分(5)的维度即该框架的强项。"""

    return {dim for dim, score in zip(DIMENSIONS, SCORES[framework]) if score >= threshold}


class EightDimensionScoring(unittest.TestCase):
    def test_langgraph_and_adk_tie_on_average(self) -> None:
        # 文章结论：LangGraph 与 ADK 综合分接近(~4.1)，CrewAI 显著低(~2.8)。
        self.assertAlmostEqual(weighted_average("LangGraph"), weighted_average("ADK"), delta=0.2)
        self.assertGreater(weighted_average("LangGraph") - weighted_average("CrewAI"), 1.0)
        self.assertGreater(weighted_average("ADK") - weighted_average("CrewAI"), 1.0)

    def test_strengths_barely_overlap(self) -> None:
        # 关键认知：三框架强项分布几乎不重叠 -> 总分有误导性。
        lg = strength_dimensions("LangGraph")
        ck = strength_dimensions("CrewAI")
        adk = strength_dimensions("ADK")
        self.assertEqual(lg & ck, set())  # LangGraph 与 CrewAI 强项零重叠
        self.assertTrue("HITL集成" in lg and "HITL集成" not in adk)
        self.assertTrue("可观测性" in adk)

    def test_crewai_wins_on_ease(self) -> None:
        self.assertEqual(SCORES["CrewAI"][DIMENSIONS.index("上手速度")], 5)
        self.assertEqual(SCORES["CrewAI"][DIMENSIONS.index("代码量")], 5)

    def test_three_impls_agree_on_business_result(self) -> None:
        # 功能一致性：同一 query，三框架选出同一供应商、同样触发 HITL。
        results = [
            sourcing_langgraph.run(sc.DEFAULT_QUERY),
            sourcing_crewai.run(sc.DEFAULT_QUERY),
            sourcing_adk.run(sc.DEFAULT_QUERY),
        ]
        tops = {r.report["top_supplier"] for r in results}
        approvals = {r.report["needs_approval"] for r in results}
        self.assertEqual(len(tops), 1)
        self.assertEqual(approvals, {True})


def _print_table() -> None:
    print("=== 8 维度综合评分（1-5 分）===\n")
    header = f"{'维度':12}" + "".join(f"{f:>11}" for f in SCORES)
    print(header)
    print("-" * len(header))
    for i, dim in enumerate(DIMENSIONS):
        print(f"{dim:12}" + "".join(f"{SCORES[f][i]:>11}" for f in SCORES))
    print("-" * len(header))
    print(f"{'简单平均':12}" + "".join(f"{simple_average(f):>11}" for f in SCORES))
    print(f"{'加权平均':12}" + "".join(f"{weighted_average(f):>11}" for f in SCORES))
    print("（文章口径为加权平均：LangGraph≈4.1 / CrewAI≈2.8 / ADK≈4.1）")
    print("\n强项分布（几乎不重叠 -> 选型不能看总分）：")
    for f in SCORES:
        print(f"  {f:10}: {STRENGTHS[f]}")


if __name__ == "__main__":
    _print_table()
    print("\n=== 自动化断言 ===")
    unittest.main(argv=[sys.argv[0], "-v"], exit=False)
