"""子图序列化（离线可运行）。

召回的子图（实体+关系集合）要变成 LLM 能读的文本才能注入 prompt。这里给三种序列化格式：
三元组列表、自然语言事实、以实体为中心的邻接描述——不同格式对生成质量影响不同。

    python3 15_graphrag/subgraph_serialize.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _graph import RELATION_TYPES, Triple, build_sample_graph  # noqa: E402
from subgraph_recall import graph_retrieve  # noqa: E402


# 关系英文 → 中文动词，用于自然语言序列化
_ZH = {en: zh for zh, en in RELATION_TYPES.items()}


def serialize_triples(subgraph: list[Triple]) -> str:
    return "\n".join(f"({t.subject}, {t.relation}, {t.object})" for t in subgraph)


def serialize_natural(subgraph: list[Triple]) -> str:
    lines = []
    for t in subgraph:
        verb = _ZH.get(t.relation, t.relation)
        lines.append(f"{t.subject} {verb} {t.object}。")
    return "".join(lines)


def serialize_entity_centric(subgraph: list[Triple]) -> str:
    by_entity: dict[str, list[str]] = {}
    for t in subgraph:
        verb = _ZH.get(t.relation, t.relation)
        by_entity.setdefault(t.subject, []).append(f"{verb} {t.object}")
    return "\n".join(f"- {ent}：{'; '.join(facts)}" for ent, facts in by_entity.items())


def build_prompt(query: str, serialized: str) -> str:
    return (
        f"已知以下知识图谱事实：\n{serialized}\n\n"
        f"请仅依据上述事实回答问题：{query}"
    )


def main() -> None:
    kg = build_sample_graph()
    query = "Y投资集团有没有卷入什么破产？"
    _, subgraph = graph_retrieve(query, kg, max_hops=2)

    print("=" * 72)
    print("子图序列化：同一子图的三种注入格式")
    print("=" * 72)

    print("\n[格式1] 三元组列表（最省 token，结构清晰）")
    print(serialize_triples(subgraph))

    print("\n[格式2] 自然语言事实（LLM 最易读）")
    print(serialize_natural(subgraph))

    print("\n[格式3] 以实体为中心的邻接描述（多跳推理友好）")
    print(serialize_entity_centric(subgraph))

    print("\n" + "=" * 72)
    print("注入 prompt 示例（用格式2）")
    print("=" * 72)
    print(build_prompt(query, serialize_natural(subgraph)))


if __name__ == "__main__":
    main()
