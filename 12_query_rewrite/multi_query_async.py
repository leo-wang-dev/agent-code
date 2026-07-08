"""Multi-Query 异步并发版（离线可运行）。

一个问题 → LLM 生成多种问法 → **并行**检索 → 按 chunk_id 合并去重（保留最高分）。
对照原文正文 `multi_query_retrieve`：这里用 `asyncio.gather` 真并发，检索函数包成
async；离线时问法由规则式 `paraphrases` 生成。

    python3 12_query_rewrite/multi_query_async.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import (  # noqa: E402
    InMemoryVectorStore,
    build_chunks,
    sample_corpus,
)
from agent_examples.text import ScoredText  # noqa: E402

from _llm import paraphrases  # noqa: E402


async def _search_async(store: InMemoryVectorStore, query: str, k: int) -> list[ScoredText]:
    # 包成协程：真实系统里每个 similarity_search 是一次网络/DB 调用，适合并发
    await asyncio.sleep(0)
    return store.search(query, k=k)


async def multi_query_retrieve(
    user_query: str, store: InMemoryVectorStore, k_per_query: int = 3, top_n: int = 5
) -> tuple[list[str], list[ScoredText]]:
    # 1. 生成多种问法（含原问题）
    queries = paraphrases(user_query, n=4)
    # 2. 并行检索
    batches = await asyncio.gather(*[_search_async(store, q, k_per_query) for q in queries])
    # 3. 按 chunk_id 合并去重，保留最高分
    merged: dict[str, ScoredText] = {}
    for batch in batches:
        for chunk in batch:
            cid = chunk.metadata.get("chunk_id", chunk.text)
            if cid not in merged or chunk.score > merged[cid].score:
                merged[cid] = chunk
    ranked = sorted(merged.values(), key=lambda x: x.score, reverse=True)[:top_n]
    return queries, ranked


def main() -> None:
    store = InMemoryVectorStore(build_chunks(sample_corpus(), "structure"))
    print("=" * 72)
    print("Multi-Query 异步并发检索")
    print("=" * 72)
    for q in ["我们公司允许远程办公吗", "我今年能休几天假"]:
        queries, ranked = asyncio.run(multi_query_retrieve(q, store))
        print(f"\n原问题：{q}")
        print("  生成问法：")
        for variant in queries:
            print(f"    - {variant}")
        print("  合并去重后 top 结果：")
        for item in ranked[:3]:
            print(f"    [{item.score:.3f}] {item.text[:44]}")


if __name__ == "__main__":
    main()
