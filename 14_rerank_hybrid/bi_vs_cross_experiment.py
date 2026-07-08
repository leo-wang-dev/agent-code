"""Bi-Encoder vs Cross-Encoder 对照实验（离线可运行）。

Bi-Encoder：query 和 passage 各自独立编码，最后算一次余弦——快、便宜，适合召回。
Cross-Encoder：query 和 passage 拼接进同一个 encoder，直接输出相关性——慢、贵，但准。
本脚本在同一批候选上对比两者的排序质量（谁把真答案排到第一）。

    python3 14_rerank_hybrid/bi_vs_cross_experiment.py

离线实现：Bi-Encoder = 词频向量余弦；Cross-Encoder = agent_examples.rag.rerank
（考虑 query↔passage 词重叠 + 答案型句式加权，作为 cross 交互的确定性代理）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import (  # noqa: E402
    InMemoryVectorStore,
    build_chunks,
    rerank,
    sample_corpus,
)
from agent_examples.text import ScoredText  # noqa: E402


QUERIES = [
    ("这手机充满电大概用多久", "phone"),
    ("在家办公需要什么手续", "remote"),
    ("我今年能休几天假", "hr_leave"),
    ("删库要不要审批", "security"),
]


def _print_table(headers, rows):
    widths = [len(str(h)) for h in headers]
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(str(c)))
    print("  ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)))
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for r in rows:
        print("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)))


def _top1_source(hits: list[ScoredText]) -> str:
    return hits[0].metadata.get("source_id", "?") if hits else "?"


def main() -> None:
    store = InMemoryVectorStore(build_chunks(sample_corpus(), "structure"))

    print("=" * 72)
    print("Bi-Encoder vs Cross-Encoder：谁把真答案排到第一")
    print("=" * 72)
    rows = []
    bi_hits = cross_hits = 0
    for query, expected in QUERIES:
        bi = store.search(query, k=8)              # 阶段1：Bi-Encoder 召回
        cross = rerank(query, bi, top_n=8)         # 阶段2：Cross-Encoder 重排
        bi_top, cross_top = _top1_source(bi), _top1_source(cross)
        bi_ok, cross_ok = bi_top == expected, cross_top == expected
        bi_hits += bi_ok
        cross_hits += cross_ok
        rows.append([query[:12], expected, bi_top, "✅" if bi_ok else "❌",
                     cross_top, "✅" if cross_ok else "❌"])
    _print_table(["query", "答案", "Bi top1", "", "Cross top1", ""], rows)

    n = len(QUERIES)
    print(f"\nBi-Encoder  Top1 命中率：{bi_hits/n:.0%}（快，负责召回）")
    print(f"Cross-Encoder Top1 命中率：{cross_hits/n:.0%}（慢，负责精排）")
    print("\n结论：Bi 和 Cross 是不同岗位——Bi 宁滥勿缺地召回，Cross 逐一精算把真答案顶到最前。")


if __name__ == "__main__":
    main()
