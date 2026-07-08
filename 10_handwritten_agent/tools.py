"""手写 Agent 的工具层（基础版 · 文件 1/2）。

对应文章第 10 篇「二、第一步：工具层」。

工具层至少包含三样东西：工具函数、工具 schema、工具注册表。
本文件不依赖任何 Agent 框架，纯 stdlib，离线可跑（天气用 mock，
计算用受限 AST 求值而不是裸 eval）。工具实现和描述放在一起管理。
"""

from __future__ import annotations

import ast
import operator
from dataclasses import dataclass
from typing import Any, Callable


def get_weather(city: str) -> str:
    """真实场景调天气 API；demo 用确定性 mock，保证离线可复现。"""
    table = {"shanghai": "31C, clear", "dubai": "40C, sunny", "beijing": "28C, cloudy"}
    return f"{city}: {table.get(city.lower(), '25C, unknown')}"


def calculate(expression: str) -> float:
    """受限表达式求值：只允许四则运算与一元正负，绝不裸 eval。"""
    binary = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
    }
    unary = {ast.UAdd: operator.pos, ast.USub: operator.neg}

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in binary:
            return binary[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in unary:
            return unary[type(node.op)](ev(node.operand))
        raise ValueError(f"unsafe expression: {expression}")

    return ev(ast.parse(expression, mode="eval"))


@dataclass(frozen=True)
class Tool:
    name: str
    description: str  # 告诉模型：何时用、参数是什么、哪些必填。
    parameters: dict[str, Any]
    handler: Callable[..., Any]

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": self.parameters},
        }


class ToolRegistry:
    """工具注册表：登记、给出 schema、按名调用。"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name].handler(**arguments)


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="get_weather",
            description="查询某城市当前天气。仅用于天气类问题。",
            parameters={"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
            handler=get_weather,
        )
    )
    registry.register(
        Tool(
            name="calculate",
            description="计算一个安全的算术表达式。非数学问题不要用。",
            parameters={"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
            handler=calculate,
        )
    )
    return registry


def main() -> None:
    registry = build_registry()
    print("已注册工具 schema:")
    for schema in registry.schemas():
        fn = schema["function"]
        print(f"  {fn['name']}: {fn['description']}")
    print("\n直接调用示例:")
    print(f"  calculate((3+5)*2) -> {registry.call('calculate', {'expression': '(3+5)*2'})}")
    print(f"  get_weather(Dubai) -> {registry.call('get_weather', {'city': 'Dubai'})}")


if __name__ == "__main__":
    main()
