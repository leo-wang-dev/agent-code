"""产物：Token 的本质与上下文预算（对应文章 §三 "Token 的本质"）。

两件事：
  1. 文字 → 数字：中文一段 prompt 的 token 数约为字符数的 1.3~2 倍，比英文贵一截。
  2. 128k 窗口是 input+output 的总和，扣掉 system/历史/RAG/工具描述/输出预留后，
     真正留给用户提问的空间可能只剩 20~30k。

无 tiktoken 依赖，用仓库内的启发式 estimate_tokens 估算（离线、确定性）。

    python3 token_budget.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_code.llm_call import ChatMessage, estimate_message_tokens, estimate_tokens


def show_tokenization() -> None:
    samples = ["什么是 BPE？", "What is BPE?", "指数退避 + Jitter + 多 Key 轮询"]
    print("① 文字 → 数字（估算，真实值请用 tiktoken）")
    for text in samples:
        print(f"    {text!r:<30} ≈ {estimate_tokens(text):>3} tokens  ({len(text)} 字符)")


def show_context_budget() -> None:
    window = 128_000
    # 一个 128k 窗口真正能给用户的空间要扣掉这些固定/动态开销。
    reserved = {
        "system prompt (固定开销)": 800,
        "历史对话 (随轮数增长)": 12_000,
        "RAG 注入文档 (几个 chunk)": 6_000,
        "工具描述 (每个几十~几百)": 1_500,
        "输出预留 (max_tokens)": 4_000,
    }
    used = sum(reserved.values())
    print("\n② 128k 窗口的真实可用空间")
    print(f"    上下文窗口总额        : {window:>8,}  (input + output 合计)")
    for name, cost in reserved.items():
        print(f"    - {name:<26}: {cost:>8,}")
    print(f"    = 留给用户提问的空间   : {window - used:>8,}")


def show_budget_breakdown() -> None:
    messages = [
        ChatMessage("system", "You are a rigorous assistant. Answer in JSON."),
        ChatMessage("user", "从这段话里提取姓名和职位：张伟是产品经理。"),
        ChatMessage("assistant", '{"name": "张伟", "position": "产品经理"}'),
    ]
    print("\n③ 一组 messages 的 token 拆解")
    total = estimate_message_tokens(messages)
    for m in messages:
        print(f"    {m.role:<10}: ≈ {estimate_tokens(m.content):>3} tokens")
    print(f"    合计(含每条 +4 结构开销): ≈ {total} tokens")


def main() -> None:
    show_tokenization()
    show_context_budget()
    show_budget_breakdown()
    print("\n经验法则：中英混合优先英文 system prompt，能省 30%~40% 的固定开销。")


if __name__ == "__main__":
    main()
