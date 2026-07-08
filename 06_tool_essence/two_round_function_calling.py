"""产物：两轮 Function Calling demo（对应文章 §二）。

Function Calling 是两轮交互：
  第一轮：把用户问题 + 工具 schema 发给模型 → 模型不直接答，返回 tool_calls；
  中间  ：你的代码解析 tool_calls、校验参数/权限、执行真实函数、处理错误；
  第二轮：把工具结果发回模型 → 模型基于结果生成最终回答。

模型负责决策，代码负责执行，模型再负责解释。本文件用仓库 FunctionCallingDemo +
default_registry 把这三步逐步打印出来（离线、确定性 mock 模型决策）。

    python3 two_round_function_calling.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.tool_essence import FunctionCallingDemo, default_registry, tool_result_message


def main() -> None:
    registry = default_registry()
    demo = FunctionCallingDemo(registry)

    for user_input in ["今天上海天气怎么样？", "帮我算 (3+5)*2 等于多少"]:
        print("=" * 60)
        print(f"用户: {user_input}")

        # 第一轮：模型返回 tool_calls，而不是直接回答。
        call = demo.first_model_turn(user_input)
        print(f"  ① 第一轮 → 模型决定调用工具（不是自己动手）")
        print(f"     tool_call = {call.name}  args={call.arguments}")

        # 中间：你的代码真的去执行。
        result = registry.call(call.name, call.arguments)
        print(f"  ② 中间执行 → 你的后端跑真实函数")
        print(f"     tool 结果 = {result!r}")
        print(f"     回给模型的 tool message = {json.dumps(tool_result_message(call, result), ensure_ascii=False)}")

        # 第二轮：模型基于结果说人话。
        answer = demo.second_model_turn(user_input, result)
        print(f"  ③ 第二轮 → 模型基于结果生成最终回答")
        print(f"     回答 = {answer}")

    print("=" * 60)
    print("模型像一个不能碰键盘的经理：判断该做什么，真正按按钮的是你的后端。")


if __name__ == "__main__":
    main()
