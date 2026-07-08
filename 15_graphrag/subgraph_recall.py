"""子图召回（离线可运行）。

GraphRAG 的检索：从 query 抽实体 → 定位图中种子节点 → N 跳遍历得到相关子图。没匹配到
实体则降级到向量 RAG。对照原文 `graph_retrieve`。

    python3 15_graphrag/subgraph_recall.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _graph import (  # noqa: E402
    KnowledgeGraph,
    Triple,
    build_sample_graph,
    extract_query_entities,
)


def graph_retrieve(query: str, kg: KnowledgeGraph, max_hops: int = 2, max_nodes: int = 50):
    # 1. 从 query 抽取实体
    query_entities = extract_query_entities(query, kg.nodes)
    # 2. 定位种子节点
    seed_nodes = [n for n in (kg.find_node(e) for e in query_entities) if n]
    if not seed_nodes:
        return None, []  # 降级信号：交给向量 RAG
    # 3. N 跳遍历得到子图
    subgraph = kg.traverse(seed_nodes, max_hops=max_hops, max_nodes=max_nodes)
    return seed_nodes, subgraph


def main() -> None:
    kg = build_sample_graph()
    print("=" * 72)
    print("子图召回：query 实体识别 → 种子节点 → N 跳遍历")
    print("=" * 72)

    queries = [
        "Y投资集团有没有卷入什么破产？",   # 需 2 跳：Y→X→破产
        "张伟所在的公司破产了吗？",         # 需 2 跳：张伟→X→破产
        "今天上海天气怎么样？",             # 无图实体 → 降级
    ]
    for query in queries:
        seeds, sub = graph_retrieve(query, kg, max_hops=2)
        print(f"\nquery：{query}")
        if seeds is None:
            print("  未匹配到图实体 → 降级到向量 RAG（fallback_vector_retrieve）")
            continue
        print(f"  种子节点：{seeds}")
        print(f"  召回子图（{len(sub)} 条边）：")
        for t in sub:
            print(f"    ({t.subject}, {t.relation}, {t.object})")

    print("\n为什么向量 RAG 做不到：破产信息和『Y投资集团』分散在不同句子/chunk，")
    print("余弦相似度分不清『逻辑相关』；图遍历顺着控股关系一跳就到了。")


if __name__ == "__main__":
    main()
