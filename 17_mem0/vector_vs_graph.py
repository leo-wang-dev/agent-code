"""17 章配套：Vector 模式 vs Graph 模式对照实验。

对应文章第四节"Mem0 Graph 模式 —— 当记忆本身就是图"。

普通模式（Vector-only）：每条事实 = 一段文本 + 向量，检索 = 向量相似度。
Graph 模式：每条事实 = 三元组（实体, 关系, 实体），检索 = 实体识别 + 图遍历 + 向量召回。

本文件用离线等价复现两种模式在同一批对话上的存储形态与检索差异：
- Vector 模式擅长"直接命中"，找不到"沿关系间接相关"的记忆；
- Graph 模式能沿边传播，回答"关系性"问题（"你提过我老婆的工作吗"）。

结论对齐文章：绝大多数项目 Vector 够用，Graph 适合社交 / CRM / 关系密集场景。

离线可运行：`python3 17_mem0/vector_vs_graph.py`
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.text import cosine, term_counts  # noqa: E402


# 同一批对话抽出的信息
FACTS_TEXT = [
    "用户的妻子叫王芳",
    "用户在某互联网公司工作",
    "王芳是产品经理",
    "某互联网公司在杭州",
]

TRIPLES = [
    ("用户", "妻子", "王芳"),
    ("用户", "工作于", "某互联网公司"),
    ("王芳", "职业", "产品经理"),
    ("某互联网公司", "位于", "杭州"),
]


class VectorMode:
    """普通模式：每条事实独立向量，检索 = 相似度 Top-K。"""

    def __init__(self, facts: list[str]) -> None:
        self.facts = facts

    def search(self, query: str, k: int = 2) -> list[tuple[float, str]]:
        q = term_counts(query)
        scored = [(cosine(q, term_counts(f)), f) for f in self.facts]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [(round(s, 3), f) for s, f in scored[:k] if s > 0]


@dataclass
class GraphMode:
    """Graph 模式：三元组建图，检索 = 实体识别 + 图遍历。"""

    edges: dict[str, list[tuple[str, str]]] = field(default_factory=lambda: defaultdict(list))
    entities: set[str] = field(default_factory=set)

    def load(self, triples: list[tuple[str, str, str]]) -> None:
        for h, r, t in triples:
            self.edges[h].append((r, t))
            self.entities.add(h)
            self.entities.add(t)

    def _entities_in(self, query: str) -> list[str]:
        return [e for e in self.entities if e in query]

    def traverse(self, query: str, hops: int = 2) -> list[str]:
        """从 query 命中的实体出发，图遍历若干跳收集关系事实。"""
        seeds = self._entities_in(query) or ["用户"]
        visited: set[str] = set()
        frontier = list(seeds)
        collected: list[str] = []
        for _ in range(hops):
            nxt: list[str] = []
            for node in frontier:
                if node in visited:
                    continue
                visited.add(node)
                for rel, tgt in self.edges.get(node, []):
                    collected.append(f"({node})-[{rel}]->({tgt})")
                    nxt.append(tgt)
            frontier = nxt
        return collected


def _demo() -> None:
    query = "你提过我老婆的工作吗"

    print("=== Vector 模式 ===")
    print("存储形态：4 条独立文本 + 向量")
    vec = VectorMode(FACTS_TEXT)
    print(f"查询：{query}")
    hits = vec.search(query, k=2)
    for score, fact in hits:
        print(f"  {score}  {fact}")
    if all("产品经理" not in f for _, f in hits):
        print("  ⚠️ 直接向量检索命中『妻子』相关，但『妻子→职业』的间接关系需要二跳才拿到")

    print("\n=== Graph 模式 ===")
    print("存储形态：5 节点 + 4 条边（三元组）")
    graph = GraphMode()
    graph.load(TRIPLES)
    print(f"查询：{query}（命中实体：{graph._entities_in(query) or ['用户(默认种子)']}）")
    for path in graph.traverse(query, hops=2):
        print(f"  {path}")
    print("  ✓ 沿 (用户)-[妻子]->(王芳)-[职业]->(产品经理) 两跳到达答案")

    print("\n=== 选型对照 ===")
    rows = [
        ("人/公司/关系密集", "Graph"),
        ("常回答关系性问题", "Graph"),
        ("事实主要是稳定属性", "Vector"),
        ("数据规模小", "Vector"),
    ]
    for scene, choice in rows:
        print(f"  {scene:20s} → {choice}")
    print("\n生产经验：绝大多数 Agent 项目 Vector 模式就够，Graph 适合社交/CRM/关系密集领域。")


if __name__ == "__main__":
    _demo()
