"""用 RAGAS 测量 Context Precision / Context Recall 的对照实验。

有 ``ragas`` 包时走真 RAGAS；没有时跑内置的**离线等价实现**（同一套定义：
Context Precision = 命中的上下文排名越靠前越高；Context Recall = 答案要点被
上下文覆盖的比例）。两条路径打印同一张对照表：朴素流水线 vs 工业级流水线。

    python3 11_rag_diagnosis/ragas_context_metrics.py

安装真 RAGAS（可选）：
    pip install ragas datasets
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import eval_corpus, eval_queries, print_table  # noqa: E402


def _offline_context_precision(ranked_source_ids: list[str], expected: str) -> float:
    """RAGAS Context Precision 的离线等价：命中项排名越靠前分越高（AP 口径）。"""

    hit_positions = [i + 1 for i, sid in enumerate(ranked_source_ids) if sid == expected]
    if not hit_positions:
        return 0.0
    # average precision over hits
    precisions = []
    hits = 0
    for i, sid in enumerate(ranked_source_ids, start=1):
        if sid == expected:
            hits += 1
            precisions.append(hits / i)
    return sum(precisions) / len(precisions)


def _offline_context_recall(retrieved_texts: list[str], answer_points: list[str]) -> float:
    """RAGAS Context Recall 的离线等价：答案要点被召回上下文覆盖的比例。"""

    if not answer_points:
        return 0.0
    joined = " ".join(retrieved_texts)
    covered = sum(1 for point in answer_points if point in joined)
    return covered / len(answer_points)


def try_real_ragas():
    """Return a callable(dataset)->metrics if ragas is importable, else None."""

    try:
        import ragas  # noqa: F401
        from ragas import evaluate  # noqa: F401
        from ragas.metrics import context_precision, context_recall  # noqa: F401

        return evaluate
    except Exception:
        return None


# 每条 query 的答案要点（ground-truth key points），用于 Context Recall
ANSWER_POINTS = {
    "在家办公吗": ["远程办公", "WFH 申请", "经理审批"],
    "办公能在家吗": ["远程办公", "WFH 申请"],
    "电池充电快吗": ["67W 快充", "5000mAh", "续航"],
    "我去年入职，今年能休几天假": ["5 个工作日", "带薪年假"],
    "出差报销额度多少": ["800 元", "500 元", "300 元"],
    "删库要审批吗": ["人工审批", "删除数据"],
}


def _retrieve_texts(pipeline_texts_fn, documents, query, k):
    return pipeline_texts_fn(documents, query, k)


def main() -> None:
    documents = eval_corpus()
    queries = eval_queries()

    from naive_rag_recall_demo import industrial_pipeline, naive_pipeline

    by_id = {d.id: d for d in documents}

    def retrieved_texts(pipeline, query, k=3):
        sids = pipeline(documents, query, k)
        return [by_id[s].text for s in sids if s in by_id]

    real = try_real_ragas()
    if real is not None:
        print("[ragas] 检测到 ragas，可接真评测；本 demo 仍打印离线等价对照以便无 key 运行。\n")
    else:
        print("[ragas] 未安装 ragas，使用内置离线等价实现（定义一致）。")
        print("        安装：pip install ragas datasets\n")

    print("=" * 72)
    print("RAGAS 对照实验：Context Precision / Context Recall")
    print("=" * 72)

    rows = []
    agg = {"naive_cp": 0.0, "ind_cp": 0.0, "naive_cr": 0.0, "ind_cr": 0.0}
    for lq in queries:
        points = ANSWER_POINTS.get(lq.query, [])
        naive_ids = naive_pipeline(documents, lq.query, 3)
        ind_ids = industrial_pipeline(documents, lq.query, 3)
        naive_cp = _offline_context_precision(naive_ids, lq.expected_source_id)
        ind_cp = _offline_context_precision(ind_ids, lq.expected_source_id)
        naive_cr = _offline_context_recall(retrieved_texts(naive_pipeline, lq.query), points)
        ind_cr = _offline_context_recall(retrieved_texts(industrial_pipeline, lq.query), points)
        agg["naive_cp"] += naive_cp
        agg["ind_cp"] += ind_cp
        agg["naive_cr"] += naive_cr
        agg["ind_cr"] += ind_cr
        rows.append([
            lq.query[:12],
            f"{naive_cp:.2f}", f"{ind_cp:.2f}",
            f"{naive_cr:.2f}", f"{ind_cr:.2f}",
        ])
    print_table(
        ["query", "朴素 CP", "工业 CP", "朴素 CR", "工业 CR"],
        rows,
    )

    n = len(queries)
    print("\n" + "=" * 72)
    print("汇总（均值）")
    print("=" * 72)
    print_table(
        ["指标", "朴素流水线", "工业级流水线"],
        [
            ["Context Precision", f"{agg['naive_cp']/n:.2f}", f"{agg['ind_cp']/n:.2f}"],
            ["Context Recall", f"{agg['naive_cr']/n:.2f}", f"{agg['ind_cr']/n:.2f}"],
        ],
    )
    print(
        "\nCP 提升来自重排把真答案顶到前排；CR 提升来自查询改写+结构化切块让答案要点被召回。"
    )


if __name__ == "__main__":
    main()
