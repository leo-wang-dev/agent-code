"""Markdown 标题路径切块器（离线可运行，纯 stdlib）。

Markdown 文档按 H1/H2/H3 层级切，每个 chunk 保留**完整父标题路径**（如
`产品文档 > API > 认证`）。检索时把标题路径拼进 chunk 文本，消歧能力大幅提升——
「认证」在不同章节下含义不同，路径就是上下文。对照原文 `markdown_chunking`。

    python3 13_chunking/markdown_header_chunker.py
    python3 13_chunking/markdown_header_chunker.py <某个.md文件路径>
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import stable_id  # noqa: E402


SAMPLE_MD = """\
# 产品文档

产品总体介绍。

## API

API 概述。

### 认证

本节描述 OAuth 2.0 鉴权流程。客户端先获取 access_token，再带 token 调用接口。

### 限流

每个 token 每分钟最多 60 次请求，超出返回 429。

## 部署

### 认证

部署环境的认证走内网 mTLS，与 API 认证不同。
"""


@dataclass
class Section:
    title_path: list[str]
    level: int
    content: str = ""


def parse_md_sections(text: str) -> list[Section]:
    heading_re = re.compile(r"^(#{1,6})\s+(.*)$")
    stack: list[tuple[int, str]] = []  # (level, title)
    sections: list[Section] = []
    current: Section | None = None
    for line in text.splitlines():
        m = heading_re.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            # 回退到父层级
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            current = Section([t for _, t in stack], level)
            sections.append(current)
        elif current is not None:
            if line.strip():
                current.content += (line.strip() + " ")
    for s in sections:
        s.content = s.content.strip()
    return sections


def markdown_chunking(text: str) -> list[dict]:
    chunks: list[dict] = []
    for section in parse_md_sections(text):
        if not section.content:
            continue  # 纯标题、无正文，跳过
        path = section.title_path
        # 检索文本 = 标题路径 + 正文，路径参与向量化
        retrievable = "[" + " > ".join(path) + "] " + section.content
        chunks.append({
            "chunk_id": stable_id(" > ".join(path) + section.content, "md"),
            "path": path,
            "level": section.level,
            "content": section.content,
            "text": retrievable,
            "metadata": {"strategy": "markdown_header", "section_path": path},
        })
    return chunks


def main() -> None:
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        text = Path(sys.argv[1]).read_text(encoding="utf-8")
        label = sys.argv[1]
    else:
        text = SAMPLE_MD
        label = "(内置示例 Markdown)"

    print("=" * 72)
    print(f"Markdown 标题路径切块器 — {label}")
    print("=" * 72)
    chunks = markdown_chunking(text)
    for c in chunks:
        print(f"[{' > '.join(c['path'])}]")
        print(f"    {c['content'][:56]}")
    print(f"\n共 {len(chunks)} 个 chunk。注意两个『认证』小节标题路径不同：")
    auths = [c for c in chunks if c["path"][-1] == "认证"]
    for c in auths:
        print(f"  · {' > '.join(c['path'])}  —— 路径消歧，检索不会混淆")


if __name__ == "__main__":
    main()
