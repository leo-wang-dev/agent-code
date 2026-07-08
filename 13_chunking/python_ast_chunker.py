"""Python AST 切块器（离线可运行，纯 stdlib）。

代码文档不能按字数切——函数体被切断就废了。正确做法是按**语法单元**切：用 `ast` 把
源码解析成语法树，按函数/类为边界切块，每块带上名字、行号、docstring。对照原文
`python_ast_chunking`。

    python3 13_chunking/python_ast_chunker.py
    python3 13_chunking/python_ast_chunker.py <某个.py文件路径>
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_examples.rag import stable_id  # noqa: E402


SAMPLE_SOURCE = '''\
import os


class UserService:
    """用户服务。"""

    def __init__(self, db):
        self.db = db

    def process_user_data(self, user_id: int, options: dict) -> dict:
        """处理用户数据并返回结构化结果。"""
        user = self.db.fetch_user(user_id)
        if not user:
            raise ValueError("user not found")
        profile = user.profile
        if options.get("include_history"):
            profile["history"] = self.db.fetch_history(user_id)
        return profile


def top_level_helper(x: int) -> int:
    """一个模块级函数。"""
    return x * 2
'''


def python_ast_chunking(source: str) -> list[dict]:
    tree = ast.parse(source)
    chunks: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            code = ast.get_source_segment(source, node) or ""
            chunks.append({
                "chunk_id": stable_id(f"{node.name}:{node.lineno}", "ast"),
                "type": type(node).__name__,
                "name": node.name,
                "code": code,
                "lineno": node.lineno,
                "end_lineno": getattr(node, "end_lineno", None),
                "docstring": ast.get_docstring(node),
                "metadata": {"strategy": "python_ast", "unit": type(node).__name__, "name": node.name},
            })
    chunks.sort(key=lambda c: c["lineno"])
    return chunks


def main() -> None:
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        source = Path(sys.argv[1]).read_text(encoding="utf-8")
        label = sys.argv[1]
    else:
        source = SAMPLE_SOURCE
        label = "(内置示例源码)"

    print("=" * 72)
    print(f"Python AST 切块器 — {label}")
    print("=" * 72)
    chunks = python_ast_chunking(source)
    for c in chunks:
        indent = "  " if c["type"] != "ClassDef" else ""
        doc = (c["docstring"] or "").splitlines()[0] if c["docstring"] else "(无)"
        print(f"{indent}[{c['type']:<16}] {c['name']:<20} L{c['lineno']}-{c['end_lineno']}  docstring: {doc}")
    print(f"\n共 {len(chunks)} 个语法单元；每块都是完整函数/类，绝不切断函数体。")
    print("每个 chunk 自带 name / lineno / docstring，检索命中后可精确定位到源码位置。")


if __name__ == "__main__":
    main()
