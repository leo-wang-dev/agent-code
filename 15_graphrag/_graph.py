"""Chapter 15 shared: 一个离线内存知识图谱 + 确定性抽取/遍历/序列化。

不依赖 Neo4j / networkx，纯 stdlib。真实系统里图存 Neo4j/Memgraph，这里用 dict 邻接表
做等价实现，保证离线可复现。导入不发起网络请求。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Triple:
    subject: str
    relation: str
    object: str

    def as_dict(self) -> dict:
        return {"subject": self.subject, "relation": self.relation, "object": self.object}


# 预定义关系类型（对应抽取 Prompt 里的 relation 白名单）
RELATION_TYPES = {
    "全资控股": "subsidiary_of",
    "控股": "subsidiary_of",
    "收购": "acquired",
    "创立": "founded",
    "任职于": "works_at",
    "破产": "bankrupted",
    "破产清算金额": "amount",
    "破产时间": "year",
    "位于": "located_in",
}


# 示例语料：每句话是一个可抽取的事实，句子之间的实体相互勾连成图
SAMPLE_SENTENCES = [
    "Y投资集团全资控股X资本管理公司。",
    "X资本管理公司破产时间是2021年。",
    "X资本管理公司破产清算金额为50亿。",
    "张伟任职于X资本管理公司。",
    "Y投资集团位于上海。",
    "Y投资集团收购了Z科技公司。",
    "李娜创立了Z科技公司。",
]


def extract_triples(sentence: str) -> list[Triple]:
    """确定性规则式三元组抽取（离线）。真实系统这里换成 LLM 抽取。

    对齐 extraction_prompts.py 的 relation 白名单。
    """

    triples: list[Triple] = []
    text = sentence.strip().rstrip("。")
    # 关系词按长度降序，先匹配更具体的（破产清算金额 优先于 破产）
    for keyword in sorted(RELATION_TYPES, key=len, reverse=True):
        idx = text.find(keyword)
        if idx <= 0:
            continue
        subj = text[:idx].strip("，, ")
        obj = text[idx + len(keyword):].strip("，,是为了 ")
        obj = re.sub(r"^(是|为|了)+", "", obj)
        if subj and obj:
            triples.append(Triple(subj, RELATION_TYPES[keyword], obj))
        break  # 每句取第一个（最具体）关系
    return triples


class KnowledgeGraph:
    """内存知识图谱：邻接表 + 反向邻接表，支持 N 跳遍历。"""

    def __init__(self) -> None:
        self.triples: list[Triple] = []
        self.out: dict[str, list[Triple]] = {}
        self.inn: dict[str, list[Triple]] = {}
        self.nodes: set[str] = set()

    def add(self, triple: Triple) -> None:
        self.triples.append(triple)
        self.out.setdefault(triple.subject, []).append(triple)
        self.inn.setdefault(triple.object, []).append(triple)
        self.nodes.add(triple.subject)
        self.nodes.add(triple.object)

    def ingest_sentences(self, sentences: list[str]) -> int:
        count = 0
        for s in sentences:
            for t in extract_triples(s):
                self.add(t)
                count += 1
        return count

    def find_node(self, name: str) -> str | None:
        if name in self.nodes:
            return name
        for node in self.nodes:  # 宽松匹配（子串）
            if name in node or node in name:
                return node
        return None

    def traverse(self, seeds: list[str], max_hops: int = 2, max_nodes: int = 50) -> list[Triple]:
        """从种子节点做无向 N 跳遍历，返回覆盖到的三元组（子图的边集）。"""

        visited: set[str] = set()
        frontier = [s for s in seeds if s in self.nodes]
        sub: list[Triple] = []
        seen_edges: set[Triple] = set()
        for _ in range(max_hops):
            next_frontier: list[str] = []
            for node in frontier:
                if node in visited:
                    continue
                visited.add(node)
                for t in self.out.get(node, []) + self.inn.get(node, []):
                    if t not in seen_edges:
                        seen_edges.add(t)
                        sub.append(t)
                    for nb in (t.subject, t.object):
                        if nb not in visited:
                            next_frontier.append(nb)
                if len(visited) >= max_nodes:
                    return sub
            frontier = next_frontier
        return sub


def extract_query_entities(query: str, known_nodes: set[str]) -> list[str]:
    """从 query 里识别已知实体（离线：子串匹配已知节点名）。"""

    hits = []
    for node in known_nodes:
        if node in query and node not in hits:
            hits.append(node)
    return hits


def build_sample_graph() -> KnowledgeGraph:
    kg = KnowledgeGraph()
    kg.ingest_sentences(SAMPLE_SENTENCES)
    return kg
