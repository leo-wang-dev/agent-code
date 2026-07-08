"""同义循环检测：识别「换个说法在原地打转」的死循环。

对应文章第 07 篇「五、终止条件是硬骨头 · 第三层：重复动作检测」，
并做一层加强：不只是逐字相同的动作，连语义相近的重复也要拦。

- 精确重复：同工具 + 同参数（复用 src/agent_code/agent_loop.py 的 detect_semantic_loop）
- 同义重复：同工具 + 参数「归一化」后相同（大小写/空白/表达式等价）
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.agent_loop import detect_semantic_loop
from agent_code.tool_essence import ToolCall


def _normalize_args(arguments: dict[str, object]) -> tuple[tuple[str, str], ...]:
    """把参数归一化：小写、去空白，让「同义」调用能对齐。"""
    normalized = []
    for key, value in sorted(arguments.items()):
        text = str(value).lower().replace(" ", "")
        normalized.append((key.lower(), text))
    return tuple(normalized)


def detect_synonym_loop(calls: list[ToolCall], *, limit: int = 3) -> bool:
    """归一化后的重复检测：捕捉逐字不同但语义相同的循环。"""
    if len(calls) < limit:
        return False
    recent = calls[-limit:]
    first_key = (recent[0].name, _normalize_args(recent[0].arguments))
    return all((call.name, _normalize_args(call.arguments)) == first_key for call in recent)


def main() -> None:
    exact = [
        ToolCall("1", "get_weather", {"city": "Shanghai"}),
        ToolCall("2", "get_weather", {"city": "Shanghai"}),
        ToolCall("3", "get_weather", {"city": "Shanghai"}),
    ]
    print("精确重复:")
    print(f"  detect_semantic_loop -> {detect_semantic_loop(exact, limit=3)}")

    synonym = [
        ToolCall("1", "calculate", {"expression": "(3+5)*2"}),
        ToolCall("2", "calculate", {"expression": "(3 + 5) * 2"}),
        ToolCall("3", "calculate", {"expression": "(3+5) * 2"}),
    ]
    print("\n逐字不同但同义:")
    print(f"  detect_semantic_loop(严格) -> {detect_semantic_loop(synonym, limit=3)}")
    print(f"  detect_synonym_loop(归一化) -> {detect_synonym_loop(synonym, limit=3)}")

    progressing = [
        ToolCall("1", "calculate", {"expression": "1+1"}),
        ToolCall("2", "get_weather", {"city": "Dubai"}),
        ToolCall("3", "calculate", {"expression": "2+2"}),
    ]
    print("\n正常推进(不同动作):")
    print(f"  detect_synonym_loop -> {detect_synonym_loop(progressing, limit=3)}")


if __name__ == "__main__":
    main()
