"""产物：输出格式控制，结构化远胜文本解析（对应文章 §四）。

工业级和玩具级差距最大的一条。玩具做法：让模型"最后一行用【意图：xxx】标注"，再拿
正则去抠——平均三天崩一次（少括号 / 多字 / 串英文 / 忘标）。

工业级做法按优先级：
  1. Tool Use / Function Calling：定义 JSON Schema，协议层强制吐 JSON；
  2. JSON Mode / Structured Output：解码阶段强制满足 schema；
  3. 文本 + 正则：只在旧模型 / 私有部署用，且必须 few-shot 锁格式、兜底拉满。

本文件复用仓库 prompt_essence 的 classify_ticket_as_tool_call / validate_json_schema /
parse_natural_language_classifier，把"正则脆弱"与"schema 稳定"并排演示（离线）。

    python3 structured_output.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.prompt_essence import (
    classify_ticket_as_tool_call,
    dumps_strict_json,
    parse_natural_language_classifier,
    validate_json_schema,
)


INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": ["finance", "it", "hr", "general"]},
        "urgency": {"type": "string", "enum": ["high", "normal"]},
    },
    "required": ["category", "urgency"],
}

# 模型"心情不好"时会写出的各种正则杀手变体（文章 §四）。
FLAKY_OUTPUTS = [
    "category: it urgency: high",   # 标准，能过
    "意图：it，紧急度：high",        # 中文冒号，正则失配
    "【intent: it】",               # 串英文、缺 urgency
    "这个工单看起来是 IT 相关的问题",  # 干脆忘了标
]


def demo_regex_is_fragile() -> None:
    print("① 玩具做法：文本 + 正则，平均三天崩一次")
    for out in FLAKY_OUTPUTS:
        try:
            parsed = parse_natural_language_classifier(out)
            print(f"    OK   {out!r:<34} → {parsed}")
        except ValueError:
            print(f"    崩   {out!r:<34} → 解析失败（要再加一条正则补丁，永远补不完）")


def demo_tool_call_is_stable() -> None:
    print("\n② 工业做法：Function Calling，协议层就必须吐 JSON")
    tickets = [
        "VPN is blocked and I need access asap",
        "请帮我报销上个月的发票 invoice",
        "onboarding 流程还没走完",
    ]
    for text in tickets:
        call = classify_ticket_as_tool_call(text)
        args = call["arguments"]
        errors = validate_json_schema(
            {"category": {"finance": "finance", "it": "it", "hr": "hr", "general": "general"}.get(args["category"], "general"),
             "urgency": args["urgency"]},
            INTENT_SCHEMA,
        )
        strict = dumps_strict_json({"category": args["category"] if args["category"] in ("finance", "it", "hr") else "general",
                                    "urgency": args["urgency"]}, INTENT_SCHEMA)
        print(f"    {text[:36]:<38} → {strict}  schema_errors={errors}")

    print("\n③ 铁律：任何业务代码要消费的 LLM 输出，必须是结构化的。")
    print("    代码里每一个 split / regex / eval，都是下一次生产事故的种子。")


def main() -> None:
    demo_regex_is_fragile()
    demo_tool_call_is_stable()


if __name__ == "__main__":
    main()
