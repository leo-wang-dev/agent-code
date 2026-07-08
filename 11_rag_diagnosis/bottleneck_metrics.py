"""每个瓶颈的可观察指标采集脚本（离线可运行）。

第 11 篇把 RAG 召回率低拆成三个可观察的瓶颈层，每一层都给一个能『采集到数字』
的指标，而不是靠感觉：

    瓶颈一 · 查询层   query_doc_lexical_gap   —— 用户原话与答案文档的词面重叠有多低
    瓶颈二 · 切块层   answer_chunk_integrity  —— 答案是否被固定字数切块切散
    瓶颈三 · 检索层   retrieval_precision@k   —— 召回结果里有多少是伪相关

    python3 11_rag_diagnosis/bottleneck_metrics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import (  # noqa: E402
    Document,
    fixed_size_chunks,
    query_rewrite,
    structure_aware_chunks,
)
from agent_examples.text import tokenize  # noqa: E402

from _common import eval_corpus, eval_queries, print_table  # noqa: E402


# ---------------------------------------------------------------------------
# 瓶颈一 · 查询层：query <-> 答案文档 的词面重叠
# ---------------------------------------------------------------------------
def query_doc_lexical_gap(query: str, doc_text: str) -> float:
    """返回 [0,1]，越低说明用户原话越『搜不到』答案文档（纯词面）。"""

    q = set(tokenize(query))
    d = set(tokenize(doc_text))
    if not q:
        return 0.0
    return len(q & d) / len(q)


# ---------------------------------------------------------------------------
# 瓶颈二 · 切块层：答案句是否被切散
# ---------------------------------------------------------------------------
def answer_chunk_integrity(doc: Document, answer_span: str, chunker) -> float:
    """答案完整落在单个 chunk 里 = 1.0；被切成 n 段 = 1/n。"""

    chunks = chunker(doc)
    hits = [c for c in chunks if answer_span in c.text]
    if hits:
        return 1.0
    # 答案被切散：统计答案字符分布到了几个 chunk
    covering = 0
    for c in chunks:
        if any(ch in c.text for ch in answer_span):
            covering += 1
    return 1.0 / max(1, covering)


# ---------------------------------------------------------------------------
# 瓶颈三 · 检索层：precision@k（召回里有多少是对的来源）
# ---------------------------------------------------------------------------
def retrieval_precision(ranked_source_ids: list[str], expected: str, k: int) -> float:
    topk = ranked_source_ids[:k]
    if not topk:
        return 0.0
    return sum(1 for sid in topk if sid == expected) / len(topk)


def main() -> None:
    documents = eval_corpus()
    queries = eval_queries()
    by_id = {d.id: d for d in documents}

    print("=" * 72)
    print("瓶颈一 · 查询层：query_doc_lexical_gap（原话 vs 改写后）")
    print("=" * 72)
    rows = []
    for lq in queries:
        doc = by_id[lq.expected_source_id]
        raw = query_doc_lexical_gap(lq.query, doc.text)
        rewritten = query_doc_lexical_gap(query_rewrite(lq.query), doc.text)
        rows.append([lq.query, f"{raw:.2f}", f"{rewritten:.2f}", "↑" if rewritten > raw else "="])
    print_table(["query", "原话重叠", "改写后重叠", "变化"], rows)
    print("观测点：原话重叠低 = 瓶颈一存在；改写把重叠拉高，就是查询层的可量化收益。\n")

    print("=" * 72)
    print("瓶颈二 · 切块层：answer_chunk_integrity（固定切块 vs 结构化切块）")
    print("=" * 72)
    # 以年假文档为例，完整答案跨越三档年限，固定小切块会把它切散
    leave = by_id["hr_leave"]
    answer = "入职满 1 年至 5 年的员工享有 5 个工作日带薪年假，5 年至 10 年享有 10 个工作日，10 年以上享有 15 个工作日"
    fixed = answer_chunk_integrity(leave, answer, lambda d: fixed_size_chunks(d, size=20, overlap=4))
    struct = answer_chunk_integrity(leave, answer, structure_aware_chunks)
    print_table(
        ["切块策略", "答案完整度", "解读"],
        [
            ["固定 20 字", f"{fixed:.2f}", "答案被切散，检索到残片"],
            ["结构化", f"{struct:.2f}", "答案+标题上下文完整保留"],
        ],
    )
    print("观测点：完整度 < 1.0 就是瓶颈二——再好的检索器也召不回被切碎的答案。\n")

    print("=" * 72)
    print("瓶颈三 · 检索层：precision@3（伪相关占比）")
    print("=" * 72)
    from naive_rag_recall_demo import industrial_pipeline, naive_pipeline

    rows = []
    for lq in queries:
        naive = retrieval_precision(naive_pipeline(documents, lq.query, 3), lq.expected_source_id, 3)
        ind = retrieval_precision(industrial_pipeline(documents, lq.query, 3), lq.expected_source_id, 3)
        rows.append([lq.query, f"{naive:.2f}", f"{ind:.2f}"])
    print_table(["query", "朴素 P@3", "工业级 P@3"], rows)
    print("观测点：precision@k 低 = 召回里塞满伪相关，正是重排要解决的问题。")


if __name__ == "__main__":
    main()
