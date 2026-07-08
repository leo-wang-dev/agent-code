"""RAGAS 四大指标完整 demo。

对应文章《RAGAS / Promptfoo / DeepEval —— 评测框架横评》第二节。

四个核心指标覆盖 RAG 的两个独立环节：
  - 检索环节：Context Precision（召回内容有多少真相关）+ Context Recall（该召回的是否都召回）
  - 生成环节：Faithfulness（答案是否严格基于召回内容）+ Answer Relevancy（答案是否切题）

真实生产：安装 `ragas`（`pip install ragas datasets`）并配置评测 LLM
（建议 GPT-4o，中英文判别一致性最好）。RAGAS 每个指标都靠 LLM 判别，
所以跑一次 = 大量 LLM 调用 = 不便宜。

本文件在缺少 ragas / 缺少 API key 时，回退到零依赖的**确定性教学版**
（用词汇重叠近似 LLM 判别），保证 demo 始终可运行、输出稳定可复现。
"""
from __future__ import annotations

import os
import re
from typing import Sequence

# ---------------------------------------------------------------------------
# 评测数据集（取自文章示例，可继续追加用例）
# ---------------------------------------------------------------------------
TEST_DATA = [
    {
        "question": "员工年假怎么算？",
        "ground_truth": "入职满 1 年至 5 年享有 5 天带薪年假",
        "answer": "您入职满 1 年的话，可以休 5 天年假",
        "contexts": [
            "员工手册第三章：年假天数 - 入职满 1 年（含）至 5 年享有 5 天带薪年假",
            "员工福利政策概述",
        ],
    },
    {
        "question": "什么是 RAG？",
        "ground_truth": "RAG 是检索增强生成，先检索相关文档再交给 LLM 生成",
        "answer": "RAG 是检索增强生成，把检索系统和 LLM 结合的工程模式",
        "contexts": [
            "RAG（Retrieval-Augmented Generation）：在 LLM 生成前先检索相关文档",
            "RAG 的核心是把检索系统和 LLM 串起来",
        ],
    },
]

METRIC_NAMES = ["context_precision", "context_recall", "faithfulness", "answer_relevancy"]


def _try_real_ragas(test_data: list[dict]) -> dict | None:
    """尝试用真实 ragas 跑评测；缺依赖或缺 key 返回 None 走 mock。"""
    try:
        from datasets import Dataset  # type: ignore
        from ragas import evaluate  # type: ignore
        from ragas.metrics import (  # type: ignore
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError:
        print("[提示] 未安装 ragas，回退到确定性教学版。")
        print("       生产安装：pip install ragas datasets")
        return None

    if not os.getenv("OPENAI_API_KEY"):
        print("[提示] 未检测到 OPENAI_API_KEY，ragas 需要评测 LLM，回退到教学版。")
        return None

    ds = Dataset.from_list(test_data)
    result = evaluate(
        ds,
        metrics=[context_precision, context_recall, faithfulness, answer_relevancy],
    )
    return {k: float(v) for k, v in dict(result).items()}


# ---------------------------------------------------------------------------
# 确定性教学版：用词汇重叠近似 LLM 判别（生产请务必换成真实 ragas）
# ---------------------------------------------------------------------------
def _tokens(text: str) -> set[str]:
    # 中文按字、英文/数字按词，简单混合分词
    zh = set(re.findall(r"[一-鿿]", text))
    en = set(re.findall(r"[a-zA-Z0-9]+", text.lower()))
    return zh | en


def _overlap(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta:
        return 0.0
    return len(ta & tb) / len(ta)


def _mock_metrics(case: dict) -> dict:
    ctx = " ".join(case["contexts"])
    # Context Precision：召回内容里多少真的与问题相关
    precision = _overlap(ctx, case["question"] + case["ground_truth"])
    # Context Recall：ground_truth 的内容是否被 context 覆盖
    recall = _overlap(case["ground_truth"], ctx)
    # Faithfulness：答案是否基于 context（答案里的信息能在 context 找到）
    faithfulness = _overlap(case["answer"], ctx)
    # Answer Relevancy：答案是否回答了问题
    relevancy = _overlap(case["answer"], case["question"] + case["ground_truth"])
    return {
        "context_precision": round(min(1.0, precision + 0.15), 2),
        "context_recall": round(min(1.0, recall + 0.1), 2),
        "faithfulness": round(min(1.0, faithfulness + 0.1), 2),
        "answer_relevancy": round(min(1.0, relevancy + 0.1), 2),
    }


def _mock_evaluate(test_data: list[dict]) -> dict:
    agg = {m: 0.0 for m in METRIC_NAMES}
    for case in test_data:
        for m, v in _mock_metrics(case).items():
            agg[m] += v
    n = len(test_data)
    return {m: round(v / n, 2) for m, v in agg.items()}


def evaluate_dataset(test_data: Sequence[dict] | None = None) -> dict:
    data = list(test_data) if test_data is not None else TEST_DATA
    real = _try_real_ragas(data)
    if real is not None:
        print("[模式] 真实 ragas")
        return real
    print("[模式] 确定性教学版（词汇重叠近似）")
    return _mock_evaluate(data)


def main() -> None:
    print("=" * 60)
    print("RAGAS 四大指标评测 demo")
    print("=" * 60)
    scores = evaluate_dataset()
    print("\n评测结果（聚合）：")
    labels = {
        "context_precision": "Context Precision（检索精度）",
        "context_recall": "Context Recall（检索召回）",
        "faithfulness": "Faithfulness（答案忠实）",
        "answer_relevancy": "Answer Relevancy（答案相关）",
    }
    for m in METRIC_NAMES:
        print(f"  {labels[m]:<32} {scores[m]:.2f}")
    overall = round(sum(scores.values()) / len(scores), 2)
    print(f"\n  综合分：{overall:.2f}")
    print("\n工业级用法：CI 中任一指标下降 >3% 阻断 PR；线上 bad case 回灌评测集永不回退。")


if __name__ == "__main__":
    main()
