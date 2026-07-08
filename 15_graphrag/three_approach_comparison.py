"""Microsoft GraphRAG / LightRAG / 自建 Cypher 三种方案的对照实验（离线可运行）。

三种主流 GraphRAG 落地方案，用统一接口 `GraphRAGApproach.answer(query)` 抽象，各自模拟其
核心机制，跑同一批多跳问题，打印能力/成本对照表：

  - Microsoft GraphRAG：社区检测 + 分层摘要（global/local 两种查询），重、贵、覆盖全；
  - LightRAG：双层检索（low-level 实体 + high-level 主题），轻、快、增量友好；
  - 自建 Cypher：直接写图数据库 + Cypher 查询，最可控、最省依赖，但要自己维护抽取质量。

    python3 15_graphrag/three_approach_comparison.py

真实使用需各自的包/服务（graphrag / lightrag / neo4j）；此处为离线机制模拟。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _graph import KnowledgeGraph, Triple, build_sample_graph  # noqa: E402
from subgraph_recall import graph_retrieve  # noqa: E402
from subgraph_serialize import serialize_natural  # noqa: E402


class GraphRAGApproach:
    name = "base"

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg

    def answer(self, query: str) -> str:
        raise NotImplementedError


class MicrosoftGraphRAG(GraphRAGApproach):
    """模拟：社区分层摘要。local 查询走子图，global 查询汇总全图社区摘要。"""

    name = "Microsoft GraphRAG"

    def _communities(self) -> dict[str, list[Triple]]:
        # 简化的社区检测：按连通的种子实体分组
        groups: dict[str, list[Triple]] = {}
        for seed in ["Y投资集团"]:
            groups[seed] = self.kg.traverse([seed], max_hops=3)
        return groups

    def answer(self, query: str) -> str:
        if any(w in query for w in ["总体", "整体", "全部", "概览"]):  # global
            summary = []
            for seed, sub in self._communities().items():
                summary.append(f"[社区:{seed}] " + serialize_natural(sub))
            return " ".join(summary)
        _, sub = graph_retrieve(query, self.kg, max_hops=2)  # local
        return serialize_natural(sub)


class LightRAG(GraphRAGApproach):
    """模拟：双层检索。low-level 抓具体实体子图，high-level 抓主题相关实体。"""

    name = "LightRAG"

    def answer(self, query: str) -> str:
        _, low = graph_retrieve(query, self.kg, max_hops=1)   # low-level：近邻
        _, high = graph_retrieve(query, self.kg, max_hops=2)  # high-level：更广主题
        merged = list(dict.fromkeys(low + high))
        return serialize_natural(merged)


class HandBuiltCypher(GraphRAGApproach):
    """模拟：手写 Cypher 精确遍历（这里用等价的图查询）。"""

    name = "自建 Cypher"

    def answer(self, query: str) -> str:
        _, sub = graph_retrieve(query, self.kg, max_hops=2)
        return serialize_natural(sub)


CAPABILITIES = {
    "Microsoft GraphRAG": {"多跳": "强", "全局摘要": "强", "增量更新": "弱", "依赖成本": "高", "可控性": "中"},
    "LightRAG": {"多跳": "中", "全局摘要": "中", "增量更新": "强", "依赖成本": "中", "可控性": "中"},
    "自建 Cypher": {"多跳": "强", "全局摘要": "弱", "增量更新": "强", "依赖成本": "低", "可控性": "强"},
}


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
    kg = build_sample_graph()
    approaches = [MicrosoftGraphRAG(kg), LightRAG(kg), HandBuiltCypher(kg)]

    print("=" * 72)
    print("三种方案跑同一多跳问题：Y投资集团有没有卷入破产？")
    print("=" * 72)
    query = "Y投资集团有没有卷入破产？"
    for ap in approaches:
        ans = ap.answer(query)
        hit = "✅命中" if ("2021" in ans and "X资本管理公司" in ans) else "❌漏"
        print(f"\n[{ap.name}] {hit}")
        print(f"  {ans[:70]}")

    print("\n" + "=" * 72)
    print("能力 / 成本对照表")
    print("=" * 72)
    dims = ["多跳", "全局摘要", "增量更新", "依赖成本", "可控性"]
    rows = [[name, *[caps[d] for d in dims]] for name, caps in CAPABILITIES.items()]
    _print_table(["方案", *dims], rows)
    print("\n选型：要全局洞察→Microsoft GraphRAG；要轻量增量→LightRAG；要极致可控省依赖→自建 Cypher。")


if __name__ == "__main__":
    main()
