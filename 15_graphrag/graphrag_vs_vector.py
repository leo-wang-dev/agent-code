"""GraphRAG 与向量 RAG 的效果对比脚本（离线可运行）。

用一批**需要多跳关系推理**的问题，对比向量 RAG 和 GraphRAG 的命中情况。向量 RAG 在
「逻辑相关但语义不相似」的多跳问题上力不从心；GraphRAG 顺着关系边遍历就能连起来。

    python3 15_graphrag/graphrag_vs_vector.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import Document, InMemoryVectorStore, sentence_chunks  # noqa: E402

from _graph import SAMPLE_SENTENCES, build_sample_graph  # noqa: E402
from subgraph_recall import graph_retrieve  # noqa: E402
from subgraph_serialize import serialize_natural  # noqa: E402


# 多跳问题 + 期望答案里必须出现的关键事实
CASES = [
    ("Y投资集团有没有卷入破产？", ["X资本管理公司", "2021"]),
    ("张伟所在的公司破产金额多少？", ["50亿"]),
    ("被Y投资集团收购的公司是谁创立的？", ["李娜", "Z科技公司"]),
]


def vector_rag_answer(query: str, store: InMemoryVectorStore) -> str:
    hits = store.search(query, k=3)
    return " ".join(h.text for h in hits)


def graphrag_answer(query: str, kg) -> str:
    _, sub = graph_retrieve(query, kg, max_hops=2)
    return serialize_natural(sub) if sub else ""


def covers(answer: str, facts: list[str]) -> bool:
    return all(f in answer for f in facts)


def _print_table(headers, rows):
    widths = [len(str(h)) for h in headers]
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(str(c)))
    print("  ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)))
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for r in rows:
        print("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)))


def main() -> None:
    # 向量 RAG：把每句话当一个 chunk 建向量库
    docs = [Document(f"s{i}", s) for i, s in enumerate(SAMPLE_SENTENCES)]
    chunks = [c for d in docs for c in sentence_chunks(d)]
    store = InMemoryVectorStore(chunks)
    kg = build_sample_graph()

    print("=" * 72)
    print("多跳关系推理：向量 RAG vs GraphRAG")
    print("=" * 72)
    rows = []
    vec_hits = graph_hits = 0
    for query, facts in CASES:
        v = vector_rag_answer(query, store)
        g = graphrag_answer(query, kg)
        v_ok, g_ok = covers(v, facts), covers(g, facts)
        vec_hits += v_ok
        graph_hits += g_ok
        rows.append([query[:16], "✅" if v_ok else "❌", "✅" if g_ok else "❌"])
    _print_table(["多跳问题", "向量 RAG", "GraphRAG"], rows)

    n = len(CASES)
    print(f"\n向量 RAG 覆盖率：{vec_hits/n:.0%}   GraphRAG 覆盖率：{graph_hits/n:.0%}")
    print("\n结论：GraphRAG 是小众杀器——只在多跳关系推理场景显著胜出；")
    print("单跳事实型问题上向量 RAG 就够了，盲目上 GraphRAG 是增加工程难度而非收益。")


if __name__ == "__main__":
    main()
