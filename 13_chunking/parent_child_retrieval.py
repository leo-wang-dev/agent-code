"""父子文档检索完整 demo（离线可运行）。

目前工业级 RAG 的「金本位」：**检索小、生成大**。用小的子 chunk 做精准向量检索，命中后
取出对应的大父 chunk 注入 prompt，兼顾召回精度和上下文完整。对照原文 `ParentChildStore`。

    python3 13_chunking/parent_child_retrieval.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import stable_id  # noqa: E402
from agent_examples.text import cosine, term_counts  # noqa: E402

from _common import SAMPLE_HANDBOOK  # noqa: E402


def _split(text: str, size: int, by: str) -> list[str]:
    if by == "paragraph":
        raw = re.split(r"(?<=。)", text)
    else:  # sentence
        raw = re.split(r"(?<=[。！？])", text)
    out: list[str] = []
    buffer = ""
    for piece in raw:
        if len(buffer) + len(piece) <= size:
            buffer += piece
        else:
            if buffer:
                out.append(buffer)
            buffer = piece
    if buffer:
        out.append(buffer)
    return [s for s in out if s.strip()]


class ParentChildStore:
    def __init__(self, parent_size: int = 90, child_size: int = 28):
        self.parent_size = parent_size
        self.child_size = child_size
        self.parents: dict[str, str] = {}
        self.children: dict[str, tuple[str, str]] = {}  # child_id -> (text, parent_id)
        self.child_vectors: list[tuple[str, object]] = []

    def index(self, document: str) -> None:
        parents = _split(document, size=self.parent_size, by="paragraph")
        for p_text in parents:
            p_id = stable_id(p_text, "parent")
            self.parents[p_id] = p_text
            for c_text in _split(p_text, size=self.child_size, by="sentence"):
                c_id = stable_id(c_text, "child")
                self.children[c_id] = (c_text, p_id)
                self.child_vectors.append((c_id, term_counts(c_text)))

    def retrieve(self, query: str, k: int = 4) -> tuple[list[str], list[str]]:
        qv = term_counts(query)
        scored = sorted(
            ((cid, cosine(qv, vec)) for cid, vec in self.child_vectors),
            key=lambda x: x[1], reverse=True,
        )[:k]
        top_children = [self.children[cid][0] for cid, _ in scored]
        parent_ids: list[str] = []
        for cid, _ in scored:
            pid = self.children[cid][1]
            if pid not in parent_ids:
                parent_ids.append(pid)
        return top_children, [self.parents[pid] for pid in parent_ids]


def main() -> None:
    store = ParentChildStore()
    store.index(SAMPLE_HANDBOOK)

    print("=" * 72)
    print("父子文档检索：子 chunk 精准命中 → 返回父 chunk 完整上下文")
    print("=" * 72)
    print(f"父 chunk 数：{len(store.parents)}   子 chunk 数：{len(store.children)}\n")

    for query in ["10 年以上年假多少", "病假工资怎么发"]:
        children, parents = store.retrieve(query, k=3)
        print(f"query：{query}")
        print("  命中的子 chunk（精准、短）：")
        for c in children:
            print(f"    · {c}")
        print("  返回的父 chunk（完整、注入 prompt）：")
        for p in parents:
            print(f"    ▶ {p}")
        print()

    print("对照：如果直接检索大父 chunk，向量会被无关句稀释，召回精度下降；")
    print("如果只返回子 chunk，生成时又缺上下文。父子结构两头都要。")


if __name__ == "__main__":
    main()
