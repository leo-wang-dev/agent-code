"""产物：并行 tool_calls（对应文章 §二"tool_calls 可能是多个"）。

模型可能一次决定并行查天气、查日历、查库存——tool_calls 是个数组。你的执行层必须
支持并发执行 + 结果聚合，并且单个工具失败不能拖垮其它工具。

本文件用仓库 execute_tool_calls_parallel（ThreadPoolExecutor）一次并发跑多个 ToolCall，
其中故意混入一个会失败的调用，展示"成功的照常返回、失败的被翻译成结构化错误"。

    python3 parallel_tool_calls.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.tool_essence import ToolCall, execute_tool_calls_parallel, default_registry


def main() -> None:
    registry = default_registry()

    # 模型一次吐出的多个 tool_calls（并行意图）。
    calls = [
        ToolCall("c1", "get_weather", {"city": "Shanghai"}),
        ToolCall("c2", "calculate", {"expression": "sqrt(144)"}),
        ToolCall("c3", "get_weather", {"city": "Dubai"}),
        ToolCall("c4", "no_such_tool", {"x": 1}),  # 故意：未知工具 → 会失败
    ]

    print(f"模型一次返回 {len(calls)} 个 tool_calls，执行层并发跑：\n")
    results = execute_tool_calls_parallel(registry, calls)

    # 结果聚合：按 tool_call_id 对齐，成功/失败分开呈现。
    for r in results:
        if r["ok"]:
            print(f"  ✓ {r['tool_call_id']}  result = {r['result']}")
        else:
            print(f"  ✗ {r['tool_call_id']}  error  = {json.dumps(r['error'], ensure_ascii=False)}")

    ok = sum(1 for r in results if r["ok"])
    print(f"\n聚合：{ok}/{len(results)} 成功。单个工具失败不影响其它工具（隔离执行）。")
    print("要点：并发提速 + 结果按 tool_call_id 对齐 + 失败翻译成模型能懂的结构化错误。")


if __name__ == "__main__":
    main()
