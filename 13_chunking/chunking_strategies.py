"""6 种切块策略的可运行实现（离线可运行）。

第 13 篇的核心：不同文档类型要用不同切块策略，chunk 必带完整 metadata。这里把六种
主流策略统一成 ``chunk(text) -> list[dict]`` 接口，每个 chunk 都带 metadata，方便横向
对比。

    python3 13_chunking/chunking_strategies.py

六种策略：
  1. fixed_size          固定字数 + overlap（最朴素，会切断语义）
  2. recursive_character 递归字符（按段/句/字符层级回退，LangChain 默认思路）
  3. sentence            句子/段落边界切
  4. structure_heading   结构感知（保留章节标题上下文）
  5. semantic            语义切块（相邻句相似度阈值，见 semantic_chunking_tuning.py）
  6. parent_child        父子文档（检索小、生成大，见 parent_child_retrieval.py）
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import (  # noqa: E402
    Document,
    fixed_size_chunks,
    sentence_chunks,
    stable_id,
    structure_aware_chunks,
)

from _common import SAMPLE_HANDBOOK, embed_similarity, print_table  # noqa: E402


def _to_dicts(chunks) -> list[dict]:
    return [
        {"text": c.text, "metadata": c.metadata, "chunk_id": c.id}
        for c in chunks
    ]


# --- 1. 固定字数 ---
def strategy_fixed_size(text: str, size: int = 40, overlap: int = 8) -> list[dict]:
    return _to_dicts(fixed_size_chunks(Document("doc", text), size=size, overlap=overlap))


# --- 2. 递归字符（段落 -> 句子 -> 字符 层级回退）---
def strategy_recursive_character(text: str, size: int = 60) -> list[dict]:
    separators = ["\n\n", "。", "；", "，", ""]

    def _split(segment: str, seps: list[str]) -> list[str]:
        if len(segment) <= size or not seps:
            return [segment]
        sep = seps[0]
        parts = segment.split(sep) if sep else list(segment)
        out: list[str] = []
        buffer = ""
        for part in parts:
            piece = part + (sep if sep else "")
            if len(buffer) + len(piece) <= size:
                buffer += piece
            else:
                if buffer:
                    out.append(buffer)
                if len(piece) > size:
                    out.extend(_split(piece, seps[1:]))
                    buffer = ""
                else:
                    buffer = piece
        if buffer:
            out.append(buffer)
        return out

    pieces = [p.strip() for p in _split(text, separators) if p.strip()]
    return [
        {"text": p, "metadata": {"strategy": "recursive", "source_id": "doc"},
         "chunk_id": stable_id("doc" + p, "chunk")}
        for p in pieces
    ]


# --- 3. 句子/段落 ---
def strategy_sentence(text: str) -> list[dict]:
    return _to_dicts(sentence_chunks(Document("doc", text)))


# --- 4. 结构感知（保留标题上下文）---
def strategy_structure_heading(text: str) -> list[dict]:
    return _to_dicts(structure_aware_chunks(Document("doc", text, {"title": "员工手册"})))


# --- 5. 语义切块（相邻句相似度阈值）---
def strategy_semantic(text: str, threshold: float = 0.12) -> list[dict]:
    sentences = [s.strip() for s in re.split(r"[。！？]+", text) if s.strip()]
    if not sentences:
        return []
    chunks: list[str] = []
    current = [sentences[0]]
    for i in range(1, len(sentences)):
        sim = embed_similarity(sentences[i - 1], sentences[i])
        if sim < threshold:  # 语义跳变，切
            chunks.append("。".join(current) + "。")
            current = [sentences[i]]
        else:
            current.append(sentences[i])
    if current:
        chunks.append("。".join(current) + "。")
    return [
        {"text": c, "metadata": {"strategy": "semantic", "source_id": "doc"},
         "chunk_id": stable_id("doc" + c, "chunk")}
        for c in chunks
    ]


# --- 6. 父子文档 ---
def strategy_parent_child(text: str, parent_size: int = 90, child_size: int = 30) -> list[dict]:
    parents = strategy_recursive_character(text, size=parent_size)
    out: list[dict] = []
    for p in parents:
        children = strategy_recursive_character(p["text"], size=child_size)
        for c in children:
            out.append({
                "text": c["text"],
                "metadata": {"strategy": "parent_child", "source_id": "doc",
                             "parent_text": p["text"]},
                "chunk_id": c["chunk_id"],
            })
    return out


STRATEGIES = {
    "fixed_size": strategy_fixed_size,
    "recursive_character": strategy_recursive_character,
    "sentence": strategy_sentence,
    "structure_heading": strategy_structure_heading,
    "semantic": strategy_semantic,
    "parent_child": strategy_parent_child,
}


def main() -> None:
    text = SAMPLE_HANDBOOK
    print("=" * 72)
    print("6 种切块策略对照（同一份员工手册）")
    print("=" * 72)
    rows = []
    for name, fn in STRATEGIES.items():
        chunks = fn(text)
        avg = sum(len(c["text"]) for c in chunks) / max(1, len(chunks))
        rows.append([name, len(chunks), f"{avg:.0f}", chunks[0]["text"][:26].replace("\n", " ")])
    print_table(["策略", "chunk 数", "平均字数", "首块预览"], rows)

    print("\n结构感知策略的 chunk（注意标题上下文被保留）：")
    for c in strategy_structure_heading(text)[:2]:
        print(f"  - {c['text'][:50]}")


if __name__ == "__main__":
    main()
