"""朴素 RAG 的 ~50% 召回率复现 demo（离线可运行）。

复现第 11 篇的核心事故：**朴素流水线**（固定字数切块 + 纯向量检索 + 拿用户原话
直接搜）在口语化 query 上召回率只有一半左右；把查询改造 + 结构化切块 + 重排叠加
上去，召回率跳到 85%+。

    python3 11_rag_diagnosis/naive_rag_recall_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import (  # noqa: E402
    build_chunks,
    fixed_size_chunks,
    query_rewrite,
    rerank,
    structure_aware_chunks,
)
from agent_examples.text import ScoredText  # noqa: E402

from _common import (  # noqa: E402
    embed_texts,
    eval_corpus,
    eval_queries,
    print_table,
    recall_at_k,
    vec_cosine,
)


def _search(chunks, query: str, k: int) -> list[str]:
    """Rank chunks against a query using (offline) embeddings, return the ordered
    list of source_ids (deduplicated, order preserved)."""

    query_vec = embed_texts([query])[0]
    chunk_vecs = embed_texts([c.text for c in chunks])
    scored = [
        (chunk, vec_cosine(query_vec, vec))
        for chunk, vec in zip(chunks, chunk_vecs)
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    ordered: list[str] = []
    for chunk, _ in scored:
        sid = chunk.metadata.get("source_id")
        if sid and sid not in ordered:
            ordered.append(sid)
        if len(ordered) >= k:
            break
    return ordered


def naive_pipeline(documents, query: str, k: int = 3) -> list[str]:
    """固定字数切块 + 纯向量 + 原始 query。"""

    chunks = [c for doc in documents for c in fixed_size_chunks(doc, size=40, overlap=8)]
    return _search(chunks, query, k)


def industrial_pipeline(documents, query: str, k: int = 3) -> list[str]:
    """结构化切块 + 查询改写 + 重排。"""

    chunks = build_chunks(documents, "structure")
    rewritten = query_rewrite(query)
    # 第一阶段：向量召回 top-8（宁滥勿缺）
    query_vec = embed_texts([rewritten])[0]
    chunk_vecs = embed_texts([c.text for c in chunks])
    scored = [
        ScoredText(c.text, vec_cosine(query_vec, v), c.metadata)
        for c, v in zip(chunks, chunk_vecs)
    ]
    scored.sort(key=lambda item: item.score, reverse=True)
    # 第二阶段：重排 top-8 -> top-k
    reranked = rerank(rewritten, scored[:8], top_n=k)
    ordered: list[str] = []
    for item in reranked:
        sid = item.metadata.get("source_id")
        if sid and sid not in ordered:
            ordered.append(sid)
    return ordered


def evaluate(pipeline, documents, queries, k: int = 3) -> tuple[float, list[list[str]]]:
    rows: list[list[str]] = []
    hits = 0.0
    for lq in queries:
        ranked = pipeline(documents, lq.query, k)
        hit = recall_at_k(ranked, lq.expected_source_id, k)
        hits += hit
        rows.append([lq.query, lq.expected_source_id, "✅" if hit else "❌", ",".join(ranked)])
    return hits / len(queries), rows


def main() -> None:
    documents = eval_corpus()
    queries = eval_queries()
    k = 1  # 头条口径用 Recall@1：口语 query 下朴素纯向量约一半被伪相关抢走

    print("=" * 72)
    print("朴素 RAG 召回率复现（Recall@%d，口语化 query）" % k)
    print("=" * 72)
    naive_recall, naive_rows = evaluate(naive_pipeline, documents, queries, k)
    print_table(["query", "答案文档", "命中", "召回顺序"], naive_rows)
    print(f"\n朴素流水线 Recall@{k} = {naive_recall:.0%}\n")

    print("=" * 72)
    print("工业级流水线（结构化切块 + 查询改写 + 重排）")
    print("=" * 72)
    ind_recall, ind_rows = evaluate(industrial_pipeline, documents, queries, k)
    print_table(["query", "答案文档", "命中", "召回顺序"], ind_rows)
    print(f"\n工业级流水线 Recall@{k} = {ind_recall:.0%}\n")

    print("=" * 72)
    print("对照结论")
    print("=" * 72)
    print_table(
        ["流水线", "切块", "查询", "检索", f"Recall@{k}"],
        [
            ["朴素", "固定 40 字", "原话", "纯向量", f"{naive_recall:.0%}"],
            ["工业级", "结构化", "改写", "向量+重排", f"{ind_recall:.0%}"],
        ],
    )
    print(
        "\n结论：召回率的差距不来自向量库或 Embedding，来自整条流水线的每一环。"
        "\n（离线词频向量下数值可能与线上略有差异，但『朴素低、叠加升』的结构一致。）"
    )


if __name__ == "__main__":
    main()
