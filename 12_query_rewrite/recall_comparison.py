"""召回率对照实验脚本（离线可运行）。

同一批口语化 query，横向对比四种查询处理策略的 Recall@k：
  1. 原话直搜（baseline）
  2. Query Rewrite（书面化 + 第三人称）
  3. HyDE（假设性答案检索）
  4. Multi-Query（多问法 + RRF 融合）

    python3 12_query_rewrite/recall_comparison.py
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import (  # noqa: E402
    Document,
    InMemoryVectorStore,
    build_chunks,
    reciprocal_rank_fusion,
    sample_corpus,
)

from _llm import hyde, paraphrases, rewrite  # noqa: E402


@dataclass
class LQ:
    query: str
    expected_source_id: str


# 在标准语料上加干扰文档：口语 query 直搜会被表面词重叠的干扰文档抢走，
# 从而拉开『原话直搜』和『改写/HyDE/Multi-Query』的差距。
DISTRACTORS = [
    Document("vpn", "网络工具。公司为在家和外出场景提供 VPN 接入，办公电脑需安装公司统一客户端。",
             {"category": "it", "title": "网络工具"}),
    Document("battery_recycle", "环保制度。废旧电池、充电设备须投放到指定回收点，禁止随意丢弃。",
             {"category": "admin", "title": "环保回收"}),
]

QUERIES = [
    LQ("在家办公吗", "remote"),          # 撞 vpn，需改写为『远程办公 WFH』
    LQ("电池续航怎么样", "phone"),        # 撞 battery_recycle，改写为『电池容量 快充 续航』
    LQ("我今年能休几天假", "hr_leave"),
    LQ("出差住宿一天能报多少", "expense"),
    LQ("删库这种操作要不要审批", "security"),
]


def _sources(hits) -> list[str]:
    out: list[str] = []
    for h in hits:
        sid = h.metadata.get("source_id")
        if sid and sid not in out:
            out.append(sid)
    return out


def recall_at_k(sources: list[str], expected: str, k: int) -> float:
    return 1.0 if expected in sources[:k] else 0.0


def _print_table(headers, rows):
    widths = [len(h) for h in headers]
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(str(c)))
    print("  ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)))
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for r in rows:
        print("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)))


def main() -> None:
    # 用固定字数切块建索引（朴素做法，无标题上下文），放大『原话直搜』的召回缺口
    store = InMemoryVectorStore(build_chunks(sample_corpus() + DISTRACTORS, "fixed"))
    k = 1

    strategies = {
        "原话直搜": lambda q: _sources(store.search(q, k=5)),
        "Query Rewrite": lambda q: _sources(store.search(rewrite(q), k=5)),
        "HyDE": lambda q: _sources(store.search(hyde(q), k=5)),
        "Multi-Query": lambda q: _sources(
            reciprocal_rank_fusion([store.search(v, k=5) for v in paraphrases(q, 4)], top_n=5)
        ),
    }

    print("=" * 72)
    print(f"查询处理策略召回率对照（Recall@{k}）")
    print("=" * 72)
    rows = []
    totals = {name: 0.0 for name in strategies}
    for lq in QUERIES:
        row = [lq.query[:12]]
        for name, fn in strategies.items():
            r = recall_at_k(fn(lq.query), lq.expected_source_id, k)
            totals[name] += r
            row.append("✅" if r else "❌")
        rows.append(row)
    _print_table(["query", *strategies.keys()], rows)

    n = len(QUERIES)
    print("\n汇总 Recall@%d：" % k)
    _print_table(
        ["策略", f"Recall@{k}"],
        [[name, f"{totals[name]/n:.0%}"] for name in strategies],
    )
    print("\n结论：没有最强，只有最合适——不同策略解决不同问题，工业级做法是按场景叠加。")


if __name__ == "__main__":
    main()
