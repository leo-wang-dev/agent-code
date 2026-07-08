"""DeepEval —— 类 Pytest 的 LLM 评测用例。

对应文章第四节。DeepEval 的 API 设计像 Pytest，工程师无需学新工具。

真实运行：
    pip install deepeval
    export OPENAI_API_KEY=...          # DeepEval 默认用 GPT 做裁判
    deepeval test run test_deepeval_cases.py
    # 或普通 pytest（会走本文件内的降级断言）：
    pytest test_deepeval_cases.py

本文件对 deepeval 做 try/except 保护：缺依赖 / 缺 key 时，
用零依赖的确定性教学版指标（词汇重叠近似）跑同样的用例，保证可运行。
DeepEval 的特殊价值在 Toxicity / Bias / Hallucination 指标——面向 C 端产品尤其重要。
"""
from __future__ import annotations

import os
import re

try:
    from deepeval import assert_test  # type: ignore
    from deepeval.metrics import (  # type: ignore
        AnswerRelevancyMetric,
        FaithfulnessMetric,
        HallucinationMetric,
    )
    from deepeval.test_case import LLMTestCase  # type: ignore

    _HAS_DEEPEVAL = bool(os.getenv("OPENAI_API_KEY"))
except ImportError:
    _HAS_DEEPEVAL = False

if not _HAS_DEEPEVAL:
    print("[提示] 未安装 deepeval 或未配置 OPENAI_API_KEY，使用确定性教学版断言。")
    print("       生产安装：pip install deepeval  然后 deepeval test run <file>")


# ---------------------------------------------------------------------------
# 零依赖教学版指标（生产请换成 deepeval 的真实 LLM 指标）
# ---------------------------------------------------------------------------
def _tokens(text: str) -> set[str]:
    zh = set(re.findall(r"[一-鿿]", text))
    en = set(re.findall(r"[a-zA-Z0-9]+", text.lower()))
    return zh | en


def _overlap(a: str, b: str) -> float:
    ta = _tokens(a)
    return len(ta & _tokens(b)) / len(ta) if ta else 0.0


def _mock_answer_relevancy(inp: str, out: str) -> float:
    return min(1.0, _overlap(out, inp) + 0.4)


def _mock_faithfulness(out: str, ctx: list[str]) -> float:
    return min(1.0, _overlap(out, " ".join(ctx)) + 0.3)


def _mock_hallucination(out: str, ctx: list[str]) -> float:
    # 幻觉率 = 答案中未被 context 支撑的比例
    return round(1.0 - _mock_faithfulness(out, ctx), 2)


def _check(name: str, value: float, threshold: float, higher_is_better: bool = True) -> None:
    ok = value >= threshold if higher_is_better else value <= threshold
    op = ">=" if higher_is_better else "<="
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}={value:.2f} (要求 {op}{threshold})")
    assert ok, f"{name}={value:.2f} 未满足阈值 {op}{threshold}"


# ---------------------------------------------------------------------------
# 用例
# ---------------------------------------------------------------------------
def test_kb_qa() -> None:
    """知识库问答：答案相关性 / 忠实度 / 幻觉率。"""
    inp = "什么是 RAG？"
    actual_output = "RAG 是检索增强生成，把检索系统和 LLM 结合的工程模式"
    retrieval_context = [
        "RAG (Retrieval-Augmented Generation)：在 LLM 生成前先检索相关文档",
        "RAG 的核心是把检索系统和 LLM 串起来",
    ]

    if _HAS_DEEPEVAL:
        test_case = LLMTestCase(
            input=inp,
            actual_output=actual_output,
            retrieval_context=retrieval_context,
        )
        assert_test(
            test_case,
            [
                AnswerRelevancyMetric(threshold=0.8),
                FaithfulnessMetric(threshold=0.85),
                HallucinationMetric(threshold=0.2),  # 幻觉率上限
            ],
        )
        return

    # 教学版阈值经过对 mock 词汇重叠指标的标定，低于真实 deepeval 的 0.8/0.85；
    # 真实运行请以上方 _HAS_DEEPEVAL 分支的 LLM 指标阈值为准。
    print("test_kb_qa（教学版）：")
    _check("AnswerRelevancy", _mock_answer_relevancy(inp, actual_output), 0.5)
    _check("Faithfulness", _mock_faithfulness(actual_output, retrieval_context), 0.5)
    _check(
        "Hallucination",
        _mock_hallucination(actual_output, retrieval_context),
        0.6,
        higher_is_better=False,
    )


def test_annual_leave() -> None:
    """HR 场景：答案是否忠实于员工手册。"""
    inp = "员工年假怎么算？"
    actual_output = "入职满 1 年可以休 5 天带薪年假"
    retrieval_context = [
        "员工手册第三章：入职满 1 年（含）至 5 年享有 5 天带薪年假",
    ]

    if _HAS_DEEPEVAL:
        test_case = LLMTestCase(
            input=inp, actual_output=actual_output, retrieval_context=retrieval_context
        )
        assert_test(
            test_case,
            [AnswerRelevancyMetric(threshold=0.7), FaithfulnessMetric(threshold=0.8)],
        )
        return

    print("test_annual_leave（教学版）：")
    _check("AnswerRelevancy", _mock_answer_relevancy(inp, actual_output), 0.5)
    _check("Faithfulness", _mock_faithfulness(actual_output, retrieval_context), 0.7)


if __name__ == "__main__":
    test_kb_qa()
    test_annual_leave()
    print("\n全部用例通过。")
