"""产物：RAG 评估流水线（对应文章 §四"评估不能省"/§五）。

"RAG 如果没有评测集、没有 faithfulness、没有 bad case 回归，本质上就是凭感觉调参。"

本文件用仓库 RAGEvaluator 给三类答案打分：
  faithfulness       答案有多少落在检索到的上下文里（越高越不像瞎编）
  context_relevance  检索到的上下文和问题有多相关
  hallucination_rate 1 - faithfulness（越低越好）

并跑一个 mini 评测集 + bad case 回归门槛，演示"可运营"阶段怎么把感觉变成指标。

    python3 rag_evaluation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.rag_essence import Document, RAGEvaluator


CONTEXT = [
    Document("leave", "Employees with one to five years of service get five days of annual leave."),
]

# 评测集：同一问题、同一上下文，三种答案质量。
CASES = [
    ("grounded 正确", "Employees get five days of annual leave for one to five years of service."),
    ("partial 部分编", "Employees get ten days of annual leave and a free gym membership."),
    ("hallucination 瞎编", "You are entitled to a company car and unlimited vacation."),
]

QUERY = "how many days of annual leave for one year of service"
FAITHFULNESS_GATE = 0.6  # bad case 回归门槛：低于此判为 bad case


def main() -> None:
    evaluator = RAGEvaluator()
    print(f"查询: {QUERY!r}\n")
    print(f"{'答案类型':<18}{'faithfulness':>13}{'ctx_relev':>11}{'halluc':>9}  判定")
    print("-" * 62)
    bad_cases = []
    for label, answer in CASES:
        m = evaluator.evaluate(QUERY, answer, CONTEXT)
        is_bad = m["faithfulness"] < FAITHFULNESS_GATE
        if is_bad:
            bad_cases.append((label, answer, m))
        verdict = "BAD CASE ✗" if is_bad else "PASS ✓"
        print(f"{label:<18}{m['faithfulness']:>13}{m['context_relevance']:>11}{m['hallucination_rate']:>9}  {verdict}")

    print(f"\nbad case 回归（faithfulness < {FAITHFULNESS_GATE}）：{len(bad_cases)} 条")
    for label, answer, m in bad_cases:
        print(f"    ✗ {label}: faithfulness={m['faithfulness']} → 回灌进测试集，防止再次退化")

    print("\n可运营 RAG = 监控召回率/忠实度/拒答率 + 把用户 bad case 回灌测试集，")
    print("而不是每次改切块参数都靠人眼看几条结果拍脑袋。")


if __name__ == "__main__":
    main()
