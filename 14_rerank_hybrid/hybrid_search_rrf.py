"""Hybrid Search + RRF 融合实现（离线可运行）。

向量检索擅长语义、BM25 擅长精确关键词/罕见词，二者互补。Hybrid = 两路并行召回 → RRF
融合 → 再交给 Reranker 精排。对照原文 `rrf_fuse`（k=60 业界经验值）。

    python3 14_rerank_hybrid/hybrid_search_rrf.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import (  # noqa: E402
    InMemoryVectorStore,
    bm25_like_search,
    build_chunks,
    reciprocal_rank_fusion,
    sample_corpus,
)
from agent_examples.text import ScoredText  # noqa: E402


def rrf_fuse(rankings: list[list[ScoredText]], k: int = 60, top_n: int = 5) -> list[ScoredText]:
    """RRF：多路检索结果按 1/(k+rank) 累加分数后重排。"""

    return reciprocal_rank_fusion(rankings, k=k, top_n=top_n)


def hybrid_search(store: InMemoryVectorStore, chunks, query: str, k_each: int = 5, top_n: int = 5):
    vector_hits = store.search(query, k=k_each)             # 语义
    keyword_hits = bm25_like_search(chunks, query, k=k_each)  # 关键词
    fused = rrf_fuse([vector_hits, keyword_hits], k=60, top_n=top_n)
    return vector_hits, keyword_hits, fused


def _src(hits):
    out = []
    for h in hits:
        s = h.metadata.get("source_id")
        if s and s not in out:
            out.append(s)
    return out


def main() -> None:
    chunks = build_chunks(sample_corpus(), "structure")
    store = InMemoryVectorStore(chunks)

    print("=" * 72)
    print("Hybrid Search：向量 + BM25 → RRF 融合")
    print("=" * 72)
    for query in ["67W 快充续航", "远程办公 WFH 申请"]:
        vec, kw, fused = hybrid_search(store, chunks, query)
        print(f"\nquery：{query}")
        print(f"  向量召回 source 顺序：{_src(vec)}")
        print(f"  BM25 召回 source 顺序：{_src(kw)}")
        print(f"  RRF 融合后 source 顺序：{_src(fused)}")
        print(f"  融合 top1：{fused[0].text[:40] if fused else '(空)'}")

    print("\n结论：向量漏掉的精确词 BM25 补上，BM25 漏掉的语义向量补上，RRF 让两路优势叠加。")


if __name__ == "__main__":
    main()
