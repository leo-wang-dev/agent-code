"""完整评测套件示例 —— AgentEvaluator + 标准 .test.json 评测集。

对应文章第一节"ADK 内置 Evaluation 框架"。

真实 ADK 写法：
    from google.adk.evaluation import AgentEvaluator
    result = AgentEvaluator.evaluate(
        agent=my_agent,
        eval_set_file="research_eval.test.json",
        criteria=composite_criteria,
    )
    result.print_report()

评测集是标准 JSON：每个用例含多轮 Invocation，每轮有 query /
expected_tool_use / reference。本脚本：
  1. 生成一个标准格式的 .test.json（写到本目录，不覆盖已有文件）；
  2. 用确定性 mock Agent + mock AgentEvaluator 跑完套件并打印结构化报告。
无需 google-adk / 模型 / 网络。
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field

try:  # google-adk 导入 try/except 保护
    from google.adk.evaluation import AgentEvaluator as _Real  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False

EVAL_SET = [
    {
        "name": "search_ai_trends",
        "data": [
            {
                "query": "Research AI trends in 2025",
                "expected_tool_use": [
                    {"tool_name": "search_web", "tool_input": {"query": "latest AI trends 2025"}}
                ],
                "reference": "Based on research, trends include agentic AI...",
            },
            {
                "query": "Continue with adoption rates",
                "expected_tool_use": [
                    {"tool_name": "search_web", "tool_input": {"query": "AI adoption rates"}}
                ],
                "reference": "AI adoption is growing across enterprises...",
            },
        ],
    }
]


# ---- mock 被测 Agent：确定性地"调工具 + 生成回答" ----
def mock_agent_run(query: str) -> dict:
    q = "latest AI trends 2025" if "trends" in query.lower() else "AI adoption rates"
    tool_calls = [{"tool_name": "search_web", "tool_input": {"query": q}}]
    if "trends" in query.lower():
        answer = "Based on research, trends include agentic AI and multimodal."
    else:
        answer = "AI adoption is growing across enterprises quickly."
    return {"tool_calls": tool_calls, "answer": answer}


def _bigrams(s: str) -> set[str]:
    s = re.sub(r"\s+", "", s.lower())
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _text_sim(a: str, b: str) -> float:
    ga, gb = _bigrams(a), _bigrams(b)
    if not ga or not gb:
        return 0.0
    return round(len(ga & gb) / len(ga | gb), 3)


@dataclass
class EvalReport:
    rows: list = field(default_factory=list)

    def add(self, case, turn, traj_ok, resp_sim):
        self.rows.append((case, turn, traj_ok, resp_sim))

    def print_report(self) -> None:
        print("== 评测报告 ==")
        print(f"{'case':<20}{'turn':<6}{'trajectory':<12}{'response_sim'}")
        traj_scores, resp_scores = [], []
        for case, turn, traj_ok, resp in self.rows:
            traj_scores.append(1.0 if traj_ok else 0.0)
            resp_scores.append(resp)
            print(f"{case:<20}{turn:<6}{'PASS' if traj_ok else 'FAIL':<12}{resp}")
        n = len(self.rows)
        print("-" * 50)
        print(f"trajectory 通过率: {sum(traj_scores)}/{n} = {sum(traj_scores) / n:.0%}")
        print(f"response 平均相似: {sum(resp_scores) / n:.3f}")


class MockAgentEvaluator:
    @staticmethod
    def evaluate(eval_set: list) -> EvalReport:
        report = EvalReport()
        for case in eval_set:
            for i, turn in enumerate(case["data"], 1):
                out = mock_agent_run(turn["query"])
                expected_tools = [t["tool_name"] for t in turn["expected_tool_use"]]
                actual_tools = [t["tool_name"] for t in out["tool_calls"]]
                traj_ok = expected_tools == actual_tools
                resp_sim = _text_sim(turn["reference"], out["answer"])
                report.add(case["name"], i, traj_ok, resp_sim)
        return report


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，使用确定性 mock AgentEvaluator 跑评测套件。")
        print("       安装： pip install google-adk")
        print("-" * 60)

    # 1. 生成标准 .test.json（不覆盖已有文件）
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "research_eval.test.json")
    if os.path.exists(out_path):
        print(f"[跳过] {out_path} 已存在，不覆盖。")
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(EVAL_SET, f, ensure_ascii=False, indent=2)
        print(f"[生成] 标准评测集: {out_path}")

    # 2. 跑评测
    report = MockAgentEvaluator.evaluate(EVAL_SET)
    print()
    report.print_report()

    print("\n工业级用法：CI 集成防回归 / A-B 测试 / Bad Case 闭环 / 模型升级评估。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
