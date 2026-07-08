"""完整 metadata schema 设计（离线可运行，纯 stdlib）。

chunk 只有 text 一个字段是玩具级；工业级 chunk 必带完整 metadata——来源、版本、标题路径、
权限、语言、切块策略、父子关系……它决定了过滤、权限隔离、引用溯源、增量更新能不能做。
对照原文正文里的 metadata 字典。

    python3 13_chunking/metadata_schema.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import stable_id  # noqa: E402


@dataclass
class ChunkMetadata:
    """一个 chunk 的完整 metadata schema。

    字段分四组：溯源(source_*) / 结构(section_path, parent_chunk_id, chunk_strategy) /
    治理(doc_version, indexed_at, permissions, lang) / 标识(chunk_id)。
    """

    chunk_id: str
    text: str
    source_doc: str
    source_url: str
    section_path: list[str] = field(default_factory=list)
    doc_version: str = "v1.0"
    indexed_at: str = ""
    permissions: list[str] = field(default_factory=lambda: ["all_employees"])
    lang: str = "zh-CN"
    chunk_strategy: str = "parent_child"
    parent_chunk_id: str | None = None

    def __post_init__(self):
        if not self.indexed_at:
            self.indexed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


REQUIRED_FIELDS = ["chunk_id", "text", "source_doc", "chunk_strategy"]


def validate(meta: dict) -> list[str]:
    """返回缺失/非法字段的问题列表，空列表 = 合法。"""

    problems: list[str] = []
    for f in REQUIRED_FIELDS:
        if not meta.get(f):
            problems.append(f"缺少必填字段：{f}")
    if meta.get("permissions") is not None and not isinstance(meta["permissions"], list):
        problems.append("permissions 必须是 list")
    if meta.get("section_path") is not None and not isinstance(meta["section_path"], list):
        problems.append("section_path 必须是 list")
    return problems


def example_chunk() -> ChunkMetadata:
    parent_id = stable_id("第三章 假期制度 年假", "parent")
    return ChunkMetadata(
        chunk_id=stable_id("年假天数正文", "chunk"),
        text="入职满 1 年至 5 年的员工享有 5 个工作日带薪年假。",
        source_doc="员工手册-v2.1.pdf",
        source_url="https://docs.company.com/handbook",
        section_path=["第三章", "假期制度", "年假"],
        doc_version="v2.1",
        permissions=["all_employees"],
        lang="zh-CN",
        chunk_strategy="parent_child",
        parent_chunk_id=parent_id,
    )


def main() -> None:
    print("=" * 72)
    print("完整 metadata schema 示例")
    print("=" * 72)
    meta = example_chunk()
    print(meta.to_json())

    print("\n" + "=" * 72)
    print("schema 校验")
    print("=" * 72)
    good = asdict(meta)
    print("合法 chunk：", validate(good) or "✅ 通过")

    bad = {"text": "缺 source_doc 和 chunk_id", "permissions": "all"}
    print("非法 chunk：", validate(bad))

    print("\n每个字段的用途：")
    usage = [
        ("source_doc / source_url", "引用溯源，答案能标注来自哪份文档"),
        ("section_path", "标题路径，消歧 + 展示面包屑"),
        ("doc_version / indexed_at", "增量更新与过期清理"),
        ("permissions", "多租户/权限隔离，检索时按用户角色过滤"),
        ("lang", "多语言库按语言路由"),
        ("chunk_strategy / parent_chunk_id", "父子检索、按策略回溯"),
    ]
    for field_name, purpose in usage:
        print(f"  · {field_name:<34} {purpose}")


if __name__ == "__main__":
    main()
