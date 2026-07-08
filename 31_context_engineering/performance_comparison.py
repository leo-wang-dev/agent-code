"""Context Engineering 性能对比脚本。

对应文章第 31 篇「四、整个过程的工程量化」表格：
    没有三大模式  ->  50 次工具调用全在主上下文、messages 30 万 token、中段遗忘
    有了三大模式  ->  大部分在子 Agent、结果存文件、主 Agent < 2 万 token

用确定性 token 估算（4 字符≈1 token）对比两种做法，纯标准库：
    python3 31_context_engineering/performance_comparison.py
"""

from __future__ import annotations

CHARS_PER_TOOL_RESULT = 8000   # 每次工具调用返回的原始数据（网页/PDF/SQL）
SUMMARY_CHARS = 120            # 卸载后 messages 里只留的摘要
TOOL_CALLS = 50               # Manus 研究：长任务平均 50 次工具调用
SUBAGENTS = 3                 # 拆成 3 个隔离子 Agent
CHARS_PER_TOKEN = 4


def _tok(chars: int) -> int:
    return chars // CHARS_PER_TOKEN


def naive_baseline() -> dict[str, int]:
    """无三大模式：所有工具结果全塞主上下文 messages。"""

    main_context_chars = TOOL_CALLS * CHARS_PER_TOOL_RESULT
    return {
        "main_context_tokens": _tok(main_context_chars),
        "tool_calls_in_main": TOOL_CALLS,
        "topics_share_context": 1,  # 三个主题挤在同一窗口
    }


def with_three_patterns() -> dict[str, int]:
    """有三大模式：调用分散到子 Agent，原文卸载到文件，主上下文只留摘要 + TODO。"""

    calls_per_sub = TOOL_CALLS // SUBAGENTS
    # 子 Agent 内部：每次调用原文进文件，messages 只留摘要。
    sub_context_chars = calls_per_sub * SUMMARY_CHARS
    # 主 Agent：只看到每个子 Agent 的结论摘要 + TODO 复述。
    main_context_chars = SUBAGENTS * SUMMARY_CHARS + 400  # 400 ≈ TODO 列表复述
    return {
        "main_context_tokens": _tok(main_context_chars),
        "peak_subagent_tokens": _tok(sub_context_chars),
        "tool_calls_in_main": 0,
        "topics_share_context": 0,  # 三主题各自隔离
    }


def main() -> None:
    base = naive_baseline()
    opt = with_three_patterns()
    print("=== Context Engineering 性能对比（50 次工具调用长任务）===\n")
    print(f"{'指标':22}{'无三大模式':>16}{'有三大模式':>16}")
    print("-" * 54)
    print(f"{'主上下文 token':20}{base['main_context_tokens']:>16,}{opt['main_context_tokens']:>16,}")
    print(f"{'主上下文工具调用数':16}{base['tool_calls_in_main']:>16}{opt['tool_calls_in_main']:>16}")
    print(f"{'子Agent峰值 token':18}{'-':>16}{opt['peak_subagent_tokens']:>16,}")

    ratio = base["main_context_tokens"] / max(1, opt["main_context_tokens"])
    print(f"\n主上下文 token 压缩倍数：约 {ratio:.0f}x")
    print("结论：三大模式不是让 LLM 变聪明，是让主上下文不溢出、长任务能稳定完成。")
    print("\n定性差异：")
    print("  无：中段大量信息被遗忘 / 三主题互相干扰 / 失败率高")
    print("  有：TODO 定期复述常驻 / 三子Agent隔离 / 稳定完成")


if __name__ == "__main__":
    main()
