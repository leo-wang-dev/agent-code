"""System Prompt 优化对照实验 —— 5 个技巧的 before/after token 实测。

对应文章第 43 篇 三、System Prompt 的工程化优化。

离线可运行：`python3 system_prompt_optimization.py`
逐条打印每个技巧优化前/后的 token 数与节省比例，最后汇总。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _tokens import estimate_tokens  # noqa: E402


@dataclass
class Experiment:
    name: str
    before: str
    after: str

    @property
    def before_tokens(self) -> int:
        return estimate_tokens(self.before)

    @property
    def after_tokens(self) -> int:
        return estimate_tokens(self.after)

    @property
    def saved_ratio(self) -> float:
        if not self.before_tokens:
            return 0.0
        return 1 - self.after_tokens / self.before_tokens


EXPERIMENTS = [
    Experiment(
        "技巧1: 删除客套话",
        before=(
            "You are a friendly, helpful, knowledgeable, and patient AI assistant. "
            "Your role is to assist users by answering their questions to the best of "
            "your ability, providing accurate and thoughtful responses at all times."
        ),
        after="你是客服助手。规则：礼貌 / 简洁 / 基于公司政策。",
    ),
    Experiment(
        "技巧2: 结构化代替散文",
        before=(
            "当用户问退货问题的时候，你应该先询问订单号，然后查询订单状态。"
            "如果订单超过 30 天，需要告诉用户超过退货期限。如果订单在 30 天内"
            "且产品没有人为损坏，可以批准退货。如果有损坏，则需要转人工处理。"
        ),
        after=(
            "退货流程：\n1. 询问订单号\n2. 查询订单\n3. 判断：\n"
            "   - 超 30 天 → 告知超期\n   - ≤ 30 天 + 无损坏 → 批准\n   - 有损坏 → 转人工"
        ),
    ),
    Experiment(
        "技巧3: XML/Markdown 标签分清指令与数据",
        before="参考以下公司政策，回答用户的退货问题，注意一定要基于政策不要编造内容。",
        after="<context>{policies}</context>\n<question>{query}</question>\n回答 question，仅基于 context。",
    ),
    Experiment(
        "技巧4: 移除稳定后的 Few-shot 示例",
        before=(
            "示例1: 用户「我要退货」→ 助手「请提供订单号」\n"
            "示例2: 用户「订单号 12345」→ 助手「已查询，符合退货条件」\n"
            "示例3: 用户「产品坏了」→ 助手「为您转接人工」\n"
            "现在开始，按上面示例的格式回答用户问题。"
        ),
        after="按「先要订单号 → 查询 → 判定」的流程回答退货问题。",
    ),
    Experiment(
        "技巧5: 英文写 System Prompt（让模型中文输出）",
        before="你是一个有帮助的助手。请仔细分析用户的问题，然后给出准确的回答。",
        after="You are a helpful assistant. Analyze the user query carefully. Reply in Chinese.",
    ),
]


def run() -> dict:
    total_before = sum(e.before_tokens for e in EXPERIMENTS)
    total_after = sum(e.after_tokens for e in EXPERIMENTS)
    return {
        "experiments": EXPERIMENTS,
        "total_before": total_before,
        "total_after": total_after,
        "saved_ratio": 1 - total_after / total_before if total_before else 0.0,
    }


def _demo() -> None:
    result = run()
    print("=" * 60)
    print("System Prompt 优化对照实验（token 用 tiktoken 或 CJK 启发式估算）")
    print("=" * 60)
    for e in result["experiments"]:
        print(f"\n{e.name}")
        print(f"  before: {e.before_tokens:>4} tokens")
        print(f"  after : {e.after_tokens:>4} tokens   省 {e.saved_ratio:.0%}")
    print("\n" + "-" * 60)
    print(
        f"合计: {result['total_before']} → {result['total_after']} tokens  "
        f"总节省 {result['saved_ratio']:.0%}"
    )
    print("固定开销压下来 = 每一次调用都省，ROI 最高（文章结论）。")


if __name__ == "__main__":
    _demo()
