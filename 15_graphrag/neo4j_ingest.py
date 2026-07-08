"""Neo4j 入图脚本（离线可运行）。

把抽取出的三元组写入 Neo4j。有 `neo4j` 驱动 + `NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD`
时真写库；否则**离线 dry-run**：打印每条三元组对应的 Cypher `MERGE` 语句，并写入内存图，
证明入图逻辑正确。导入不发起网络请求。

    python3 15_graphrag/neo4j_ingest.py

安装真驱动（可选）：
    pip install neo4j
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _graph import KnowledgeGraph, SAMPLE_SENTENCES, Triple, extract_triples  # noqa: E402


def triple_to_cypher(t: Triple) -> str:
    """一条三元组 → 幂等的 Cypher MERGE（节点去重 + 建关系）。"""

    return (
        f"MERGE (s:Entity {{name: '{t.subject}'}}) "
        f"MERGE (o:Entity {{name: '{t.object}'}}) "
        f"MERGE (s)-[:{t.relation.upper()}]->(o)"
    )


def ingest_neo4j(triples: list[Triple]) -> bool:
    """真写 Neo4j。成功返回 True，不可用返回 False。"""

    uri = os.getenv("NEO4J_URI")
    if not uri:
        return False
    try:
        from neo4j import GraphDatabase  # pragma: no cover
    except Exception:
        print("[neo4j] 未安装驱动，pip install neo4j；本次走离线 dry-run。")
        return False
    try:  # pragma: no cover - online path
        driver = GraphDatabase.driver(
            uri,
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
        )
        with driver.session() as session:
            for t in triples:
                session.run(triple_to_cypher(t))
        driver.close()
        return True
    except Exception as exc:
        print(f"[neo4j] 连接/写入失败，走离线 dry-run：{exc}")
        return False


def main() -> None:
    triples: list[Triple] = []
    for s in SAMPLE_SENTENCES:
        triples.extend(extract_triples(s))

    print("=" * 72)
    print("Neo4j 入图（每条三元组 → 幂等 Cypher MERGE）")
    print("=" * 72)
    for t in triples:
        print(triple_to_cypher(t))

    print("\n" + "=" * 72)
    if ingest_neo4j(triples):
        print("已写入真实 Neo4j 实例。")
    else:
        # 离线 dry-run：写内存图，验证节点/边数正确
        kg = KnowledgeGraph()
        for t in triples:
            kg.add(t)
        print("离线 dry-run 完成（未连接 Neo4j）。")
        print(f"  节点数：{len(kg.nodes)}   关系数：{len(kg.triples)}")
        print(f"  节点：{sorted(kg.nodes)}")
    print("=" * 72)
    print("MERGE 保证幂等：重复入图不会产生重复节点/边，适合增量更新。")


if __name__ == "__main__":
    main()
