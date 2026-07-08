"""手写 Agent 主体（基础版 · 文件 2/2）：不用任何 Agent 框架。

对应文章第 10 篇「三、消息管理」「四、ReAct 主循环」「五、错误处理」「六、Trace」。

只用原生 Python + 同目录 tools.py，串起工业级雏形该有的东西：
- 消息管理：自己维护 system/user/assistant/tool 四类 messages（LLM 是无状态的）
- ReAct 主循环：模型要么给最终答案，要么请求工具调用
- 终止条件：最大轮数 / 重复动作检测（显式控制，不是裸 while True）
- 错误处理：工具异常分类（临时/权限/参数/未知），而不是 except: pass
- Trace：每步为什么这么做、调了什么、返回什么，全部记录

这里的「模型」是一个确定性替身 decide_next()，真实系统换成一次 LLM 调用即可，
循环骨架完全不变。无需 API key，离线可跑。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from tools import ToolRegistry, build_registry


def classify_error(error: Exception) -> dict[str, str]:
    """错误分类：告诉模型该重试、放弃还是改参数。"""
    if isinstance(error, TimeoutError):
        return {"type": "temporary", "message": "工具超时，可稍后重试"}
    if isinstance(error, PermissionError):
        return {"type": "permission", "message": "权限不足，需要审批"}
    if isinstance(error, (KeyError, ValueError, TypeError)):
        return {"type": "bad_request", "message": str(error)}
    return {"type": "unknown", "message": str(error)}


def extract_expression(text: str) -> str:
    candidates = re.findall(r"[0-9+\-*/().\s]+", text)
    numeric = [c.strip() for c in candidates if any(ch.isdigit() for ch in c)]
    return max(numeric, key=len).strip() if numeric else "0"


def decide_next(user_input: str, observations: list[str]) -> dict[str, Any]:
    """模型替身：一轮决策。返回 {"final": str} 或 {"tool": name, "arguments": {...}}。"""
    if observations:  # 已有工具结果 -> 收束成最终答案
        return {"thought": "工具已返回结果，可以回答了", "final": observations[-1]}
    lowered = user_input.lower()
    if any(word in lowered for word in ["weather", "天气"]):
        city = "Dubai" if "dubai" in lowered else "Shanghai"
        return {"thought": "需要查天气", "tool": "get_weather", "arguments": {"city": city}}
    return {"thought": "需要算术工具", "tool": "calculate", "arguments": {"expression": extract_expression(user_input)}}


@dataclass
class HandwrittenAgent:
    registry: ToolRegistry = field(default_factory=build_registry)
    system_prompt: str = "你是一个小而可靠的 Agent，需要时才调用工具。"
    max_iterations: int = 5

    def run(self, user_input: str) -> dict[str, Any]:
        # 消息管理：LLM 无状态，历史必须自己塞回去。
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]
        observations: list[str] = []
        trace: list[dict[str, Any]] = []
        seen_signatures: list[str] = []

        for step in range(1, self.max_iterations + 1):
            decision = decide_next(user_input, observations)

            if "final" in decision:  # 模型给最终答案 -> 结束
                messages.append({"role": "assistant", "content": decision["final"]})
                return {"status": "finished", "answer": decision["final"], "messages": messages, "trace": trace}

            tool, arguments = decision["tool"], decision["arguments"]
            signature = f"{tool}:{json.dumps(arguments, sort_keys=True, ensure_ascii=False)}"

            # 终止条件：重复动作检测。
            if seen_signatures.count(signature) >= 2:
                return {"status": "stopped", "reason": "repeated_action", "messages": messages, "trace": trace}
            seen_signatures.append(signature)

            # 错误处理：工具是远程依赖，异常要分类回填，不能吞掉。
            try:
                result = self.registry.call(tool, arguments)
                observation = str(result)
                error_class = None
            except Exception as error:  # noqa: BLE001 - 分类后回填给模型。
                error_class = classify_error(error)
                observation = f"ERROR[{error_class['type']}]: {error_class['message']}"

            observations.append(observation)
            messages.append({"role": "assistant", "content": f"call {tool} {arguments}"})
            messages.append({"role": "tool", "content": observation})

            # Trace：每步为什么这么做、调了什么、返回什么。
            trace.append(
                {
                    "step": step,
                    "thought": decision.get("thought"),
                    "tool": tool,
                    "arguments": arguments,
                    "observation": observation,
                    "error_class": error_class,
                }
            )

        # 终止条件：最大轮数兜底。
        return {"status": "stopped", "reason": "max_iterations", "messages": messages, "trace": trace}


def main() -> None:
    agent = HandwrittenAgent()
    for task in ["请计算 (3+5)*2", "What is the weather in Dubai?"]:
        result = agent.run(task)
        print(f"\n=== 任务: {task} ===")
        print(f"状态: {result['status']}  答案: {result.get('answer')}")
        for step in result["trace"]:
            print(f"  step{step['step']} [{step['thought']}] {step['tool']}{step['arguments']} -> {step['observation']}")


if __name__ == "__main__":
    main()
