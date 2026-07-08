"""双阶段检索完整 demo（离线可运行）。

标准工程形态：阶段 1 Bi-Encoder 向量召回 Top-K_recall（宁滥勿缺）→ 阶段 2 Cross-Encoder
逐一重排精选 Top-K_final。对照原文 `two_stage_retrieve`。

    python3 14_rerank_hybrid/two_stage_retrieval.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import (  # noqa: E402
    InMemoryVectorStore,
    build_chunks,
    sample_corpus,
)
from agent_examples.text import ScoredText  # noqa: E402

from reranker_adapters import BgeReranker  # noqa: E402


def two_stage_retrieve(store, reranker, query, k_recall=8, k_final=3):
    # 阶段 1：Bi-Encoder 向量检索（毫秒级，召回宽）
    candidates = store.search(query, k=k_recall)
    # 阶段 2：Cross-Encoder 重排（秒级，精选窄）
    reranked = reranker.rerank(query, candidates, top_n=k_final)
    return candidates, reranked


def _fmt(hits, n):
    return [f"{h.metadata.get('source_id','?')}:{h.text[:16]}" for h in hits[:n]]


def main() -> None:
    store = InMemoryVectorStore(build_chunks(sample_corpus(), "structure"))
    reranker = BgeReranker()  # 无 SDK 时自动离线打分

    print("=" * 72)
    print("双阶段检索：Bi 召回 Top-8 → Cross 重排 Top-3")
    print("=" * 72)
    for query in ["我今年能休几天假", "这手机充电快不快"]:
        candidates, reranked = two_stage_retrieve(store, reranker, query)
        print(f"\nquery：{query}")
        print(f"  阶段1 召回({len(candidates)})：{_fmt(candidates, 4)}")
        print(f"  阶段2 精排(3)  ：{_fmt(reranked, 3)}")
        print(f"  最终 top1：{reranked[0].text[:40] if reranked else '(空)'}")

    print("\n为什么要两阶段：Cross-Encoder 对每个候选逐一算太贵，不能对全库跑；")
    print("先用便宜的 Bi-Encoder 把范围缩到 Top-K，再让贵的 Cross-Encoder 在小集合上精算。")


if __name__ == "__main__":
    main()
