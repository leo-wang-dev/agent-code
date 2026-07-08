"""FunctionTool 自动 Schema 示例 —— 类型标注 + docstring -> Function Calling Schema。

对应文章第一节"自动 Schema 生成"。

真实 ADK 里你只写普通函数：
    def search_web(query: str, max_results: int = 5,
                   language: str = "en",
                   tool_context: Optional[ToolContext] = None) -> dict:
        '''搜索网络获取信息。
        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            language: 搜索语言代码
        '''
ADK 背后自动推断出 JSON Schema，并**跳过 tool_context 参数**（运行时注入）。

本脚本用标准库 inspect + typing 真的把这套推断跑出来（无需 google-adk），
产出与 ADK FunctionTool 等价的 schema，直观展示"自动"是怎么发生的。
"""

from __future__ import annotations

import inspect
import re
import sys
import typing
from typing import Optional, get_args, get_origin

try:  # google-adk 导入 try/except 保护
    from google.adk.tools import FunctionTool  # noqa: F401

    HAS_ADK = True
except ImportError:
    HAS_ADK = False


class ToolContext:  # 占位类型：schema 生成时需被识别并跳过
    pass


# ---- 被推断的示例工具（普通函数 + 类型标注 + docstring） ----
def search_web(
    query: str,
    max_results: int = 5,
    language: str = "en",
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """搜索网络获取信息。

    Args:
        query: 搜索关键词
        max_results: 最大返回结果数
        language: 搜索语言代码
    """
    return {"results": []}


_TYPE_MAP = {str: "string", int: "integer", float: "number", bool: "boolean",
             dict: "object", list: "array"}


def _json_type(annotation) -> str:
    if get_origin(annotation) is typing.Union:  # Optional[X] = Union[X, None]
        args = [a for a in get_args(annotation) if a is not type(None)]
        if args:
            return _json_type(args[0])
    return _TYPE_MAP.get(annotation, "string")


def _parse_arg_docs(doc: str) -> dict[str, str]:
    """从 docstring 的 Args: 段解析每个参数的描述。"""
    descriptions: dict[str, str] = {}
    if not doc:
        return descriptions
    in_args = False
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("args:"):
            in_args = True
            continue
        if in_args:
            m = re.match(r"(\w+):\s*(.+)", stripped)
            if m:
                descriptions[m.group(1)] = m.group(2)
            elif stripped == "":
                continue
    return descriptions


def build_schema(fn) -> dict:
    """复刻 ADK FunctionTool 的自动 schema 生成。"""
    sig = inspect.signature(fn)
    # 用 get_type_hints 把注解解析成真实类型（本模块启用了 PEP 563，
    # 注解此时是字符串，必须显式解析）。
    hints = typing.get_type_hints(fn)
    arg_docs = _parse_arg_docs(inspect.getdoc(fn) or "")
    summary = (inspect.getdoc(fn) or "").splitlines()[0] if inspect.getdoc(fn) else ""

    properties: dict = {}
    required: list[str] = []
    for name, param in sig.parameters.items():
        ann = hints.get(name, param.annotation)
        # 跳过 tool_context（含 Optional[ToolContext]）—— 运行时注入，LLM 不可见
        if name == "tool_context" or ann is ToolContext or (
            get_origin(ann) is typing.Union and ToolContext in get_args(ann)
        ):
            continue
        prop: dict = {"type": _json_type(ann)}
        if name in arg_docs:
            prop["description"] = arg_docs[name]
        if param.default is not inspect.Parameter.empty:
            prop["default"] = param.default
        else:
            required.append(name)
        properties[name] = prop

    return {
        "name": fn.__name__,
        "description": summary,
        "parameters": {"type": "object", "properties": properties, "required": required},
    }


def main() -> int:
    if not HAS_ADK:
        print("[提示] 未检测到 google-adk，用标准库 inspect/typing 复刻自动 Schema 生成。")
        print("       安装真实框架： pip install google-adk")
        print("-" * 60)

    import json

    schema = build_schema(search_web)
    print("== 由 search_web 自动生成的 Function Calling Schema ==")
    print(json.dumps(schema, ensure_ascii=False, indent=2))

    props = schema["parameters"]["properties"]
    assert "tool_context" not in props, "tool_context 必须被跳过"
    assert schema["parameters"]["required"] == ["query"], "只有 query 是必填"
    print("\n校验通过：tool_context 已跳过；required 只有 query；默认值/描述已推断。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
