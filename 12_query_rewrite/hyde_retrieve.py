"""HyDE（Hypothetical Document Embeddings）完整实现（离线可运行）。

HyDE 的核心：**用户问题和答案文档语言差距大，但假设性答案和真答案语言接近**。所以
先让模型编一段假答案，再用假答案去检索，比拿原问题直接搜更容易命中。

    python3 12_query_rewrite/hyde_retrieve.py

对照原文正文 `hyde_retrieve`：这里把 `llm.generate` 换成在线优先/离线兜底的 `hyde()`，
向量库换成 `agent_examples.rag.InMemoryVectorStore`，其余流程一致。
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

from _llm import hyde  # noqa: E402


def hyde_retrieve(user_query: str, vector_store: InMemoryVectorStore, k: int = 3):
    # 1. 让 LLM 编一段假答案
    hypothetical_answer = hyde(user_query)
    # 2. 用假答案去检索
    return hypothetical_answer, vector_store.search(hypothetical_answer, k=k)


def main() -> None:
    store = InMemoryVectorStore(build_chunks(sample_corpus(), "structure"))
    queries = ["这手机充满电大概用多久", "在家办公需要什么手续", "我今年能休几天假"]

    print("=" * 72)
    print("HyDE 检索：原问题直搜 vs 先编假答案再搜")
    print("=" * 72)
    for q in queries:
        print(f"\n用户问题：{q}")
        direct = store.search(q, k=3)
        hypo, hyde_hits = hyde_retrieve(q, store, k=3)
        print(f"  假设性答案：{hypo}")
        print("  [直搜 top1]  ", direct[0].text[:40] if direct else "(空)",
              f"  score={direct[0].score:.3f}" if direct else "")
        print("  [HyDE top1] ", hyde_hits[0].text[:40] if hyde_hits else "(空)",
              f"  score={hyde_hits[0].score:.3f}" if hyde_hits else "")


if __name__ == "__main__":
    main()
