"""对话历史分层摘要实现 —— 滑动窗口 / 单层摘要 / 多层分层摘要三种策略。

对应文章第 43 篇 五、对话历史的压缩策略。

摘要用离线确定性实现（抽取式：取每轮关键句 + 截断）。生产替换为一次小模型
调用做抽象式摘要（见 _summarize 注释）。

离线可运行：`python3 history_layered_summary.py`
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _tokens import estimate_tokens  # noqa: E402


@dataclass
class Turn:
    role: str  # user / assistant
    content: str


def _summarize(turns: list[Turn], budget_tokens: int) -> str:
    """离线抽取式摘要：合并、取要点、按 token 预算截断。

    生产替换：
        summary = small_llm.complete(f"把下面对话压成 {budget_tokens} token 摘要:\n{joined}")
    """
    joined = " / ".join(f"{t.role}:{t.content}" for t in turns)
    # 粗暴按预算截断：内容以中文为主，token≈char，直接用 budget 作字符上限。
    max_chars = budget_tokens
    if len(joined) > max_chars:
        joined = joined[:max_chars] + "…"
    return f"[摘要 {len(turns)} 轮] {joined}"


def sliding_window(turns: list[Turn], max_rounds: int = 10) -> list[Turn]:
    """策略1：滑动窗口——只保留最近 N 轮（用户+助手=2 条/轮）。"""
    return turns[-max_rounds * 2:]


def summary_compression(turns: list[Turn], recent_rounds: int = 5, budget: int = 500) -> dict:
    """策略2：摘要压缩——早期对话压成一段摘要，最近若干轮完整保留。"""
    keep = turns[-recent_rounds * 2:]
    old = turns[: len(turns) - len(keep)]
    summary = _summarize(old, budget) if old else ""
    return {"summary": summary, "recent": keep}


def layered_summary(turns: list[Turn]) -> dict:
    """策略3：分层摘要——最近保真，越早层级越粗（类似 RAG 父子文档）。

    分层规则（对齐文章）：
      最近 5 轮   : 完整保留
      第 6-20 轮  : 第一层摘要 (~200 token)
      第 21-50 轮 : 第二层摘要 (~150 token)
      更早        : 第三层摘要 (~100 token)
    """
    rounds = [turns[i:i + 2] for i in range(0, len(turns), 2)]
    n = len(rounds)

    def slice_rounds(lo: int, hi: int) -> list[Turn]:
        chunk = rounds[max(0, n - hi): max(0, n - lo)]
        return [t for pair in chunk for t in pair]

    recent = slice_rounds(0, 5)
    layer1 = slice_rounds(5, 20)
    layer2 = slice_rounds(20, 50)
    layer3 = rounds[: max(0, n - 50)]
    layer3 = [t for pair in layer3 for t in pair]

    return {
        "recent": recent,
        "layer1_summary": _summarize(layer1, 200) if layer1 else "",
        "layer2_summary": _summarize(layer2, 150) if layer2 else "",
        "layer3_summary": _summarize(layer3, 100) if layer3 else "",
    }


def _tokens_of(turns: list[Turn]) -> int:
    return sum(estimate_tokens(f"{t.role}:{t.content}") for t in turns)


def _build_history(rounds: int) -> list[Turn]:
    turns: list[Turn] = []
    for i in range(rounds):
        turns.append(Turn("user", f"第{i + 1}轮：用户询问关于订单{i + 1}的退货政策细节问题。"))
        turns.append(Turn("assistant", f"第{i + 1}轮：助手回答订单{i + 1}在30天内无损坏可退货。"))
    return turns


def _demo() -> None:
    history = _build_history(80)
    full_tokens = _tokens_of(history)
    print(f"完整历史: {len(history)} 条消息, {full_tokens} tokens\n")

    win = sliding_window(history, max_rounds=10)
    print(f"策略1 滑动窗口(10轮): {_tokens_of(win)} tokens  省 {1 - _tokens_of(win) / full_tokens:.0%}")

    comp = summary_compression(history, recent_rounds=5)
    comp_tokens = estimate_tokens(comp["summary"]) + _tokens_of(comp["recent"])
    print(f"策略2 摘要压缩      : {comp_tokens} tokens  省 {1 - comp_tokens / full_tokens:.0%}")

    lay = layered_summary(history)
    lay_tokens = (
        _tokens_of(lay["recent"])
        + estimate_tokens(lay["layer1_summary"])
        + estimate_tokens(lay["layer2_summary"])
        + estimate_tokens(lay["layer3_summary"])
    )
    print(f"策略3 分层摘要      : {lay_tokens} tokens  省 {1 - lay_tokens / full_tokens:.0%}")
    print("\n分层结构：")
    print(f"  recent(完整)     : {len(lay['recent'])} 条")
    print(f"  layer1(6-20轮)   : {estimate_tokens(lay['layer1_summary'])} tokens")
    print(f"  layer2(21-50轮)  : {estimate_tokens(lay['layer2_summary'])} tokens")
    print(f"  layer3(更早)     : {estimate_tokens(lay['layer3_summary'])} tokens")


if __name__ == "__main__":
    _demo()
